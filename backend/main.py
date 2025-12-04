from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import os
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Events API",
    version="1.0.0",
    description="REST API for managing events with DynamoDB"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        # Add your production domains here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# DynamoDB setup
dynamodb = boto3.resource('dynamodb')
table_name = os.getenv('EVENTS_TABLE_NAME', 'EventsTable')
table = dynamodb.Table(table_name)


# Custom exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"}
    )


# Pydantic models with validation
class EventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Event title")
    description: str = Field(..., min_length=1, max_length=2000, description="Event description")
    date: str = Field(..., description="Event date in ISO format (YYYY-MM-DD or ISO 8601)")
    location: str = Field(..., min_length=1, max_length=300, description="Event location")
    capacity: int = Field(..., gt=0, le=100000, description="Event capacity (1-100000)")
    organizer: str = Field(..., min_length=1, max_length=200, description="Event organizer name")
    status: str = Field(default="scheduled", description="Event status")
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['scheduled', 'ongoing', 'completed', 'cancelled', 'active']
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v
    
    @validator('date')
    def validate_date(cls, v):
        try:
            # Try parsing as ISO date
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError("Date must be in ISO format (YYYY-MM-DD or ISO 8601)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Tech Conference 2024",
                "description": "Annual technology conference featuring industry leaders",
                "date": "2024-12-15T09:00:00Z",
                "location": "San Francisco Convention Center",
                "capacity": 500,
                "organizer": "Tech Events Inc",
                "status": "scheduled"
            }
        }


class EventCreate(EventBase):
    eventId: Optional[str] = Field(None, description="Optional custom event ID")


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    date: Optional[str] = None
    location: Optional[str] = Field(None, min_length=1, max_length=300)
    capacity: Optional[int] = Field(None, gt=0, le=100000)
    organizer: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[str] = None
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ['scheduled', 'ongoing', 'completed', 'cancelled', 'active']
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v
    
    @validator('date')
    def validate_date(cls, v):
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
                return v
            except ValueError:
                raise ValueError("Date must be in ISO format (YYYY-MM-DD or ISO 8601)")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Tech Conference 2024",
                "capacity": 600,
                "status": "ongoing"
            }
        }


class Event(EventBase):
    eventId: str = Field(..., description="Unique event identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "eventId": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Tech Conference 2024",
                "description": "Annual technology conference featuring industry leaders",
                "date": "2024-12-15T09:00:00Z",
                "location": "San Francisco Convention Center",
                "capacity": 500,
                "organizer": "Tech Events Inc",
                "status": "scheduled"
            }
        }


class ErrorResponse(BaseModel):
    detail: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Event not found"
            }
        }


@app.get("/")
async def root():
    return {"message": "Events API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post(
    "/events",
    response_model=Event,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Event created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def create_event(event: EventCreate):
    """
    Create a new event with the following properties:
    - **title**: Event title (1-200 characters)
    - **description**: Event description (1-2000 characters)
    - **date**: Event date in ISO format
    - **location**: Event location (1-300 characters)
    - **capacity**: Event capacity (1-100000)
    - **organizer**: Organizer name (1-200 characters)
    - **status**: Event status (scheduled, ongoing, completed, cancelled, active)
    - **eventId**: Optional custom event ID
    """
    # Use provided eventId or generate new one
    event_id = event.eventId if event.eventId else str(uuid.uuid4())
    
    item = {
        'eventId': event_id,
        'title': event.title,
        'description': event.description,
        'date': event.date,
        'location': event.location,
        'capacity': event.capacity,
        'organizer': event.organizer,
        'status': event.status,
        'createdAt': datetime.utcnow().isoformat()
    }
    
    try:
        table.put_item(Item=item)
        logger.info(f"Created event: {event_id}")
        event_dict = event.dict(exclude={'eventId'})
        return Event(eventId=event_id, **event_dict)
    except ClientError as e:
        logger.error(f"DynamoDB error creating event: {e.response['Error']['Message']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create event in database"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@app.get(
    "/events",
    response_model=List[Event],
    responses={
        200: {"description": "List of all events"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def list_events(status: Optional[str] = None):
    """
    Retrieve all events from the database.
    Optionally filter by status using ?status=active query parameter.
    Returns an empty list if no events exist.
    """
    try:
        if status:
            # Filter by status
            response = table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': status}
            )
        else:
            response = table.scan()
        
        events = response.get('Items', [])
        logger.info(f"Retrieved {len(events)} events" + (f" with status={status}" if status else ""))
        return [Event(**event) for event in events]
    except ClientError as e:
        logger.error(f"DynamoDB error listing events: {e.response['Error']['Message']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve events from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@app.get(
    "/events/{event_id}",
    response_model=Event,
    responses={
        200: {"description": "Event details"},
        404: {"model": ErrorResponse, "description": "Event not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_event(event_id: str):
    """
    Retrieve a specific event by its ID.
    Returns 404 if the event doesn't exist.
    """
    if not event_id or not event_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event ID cannot be empty"
        )
    
    try:
        response = table.get_item(Key={'eventId': event_id})
        
        if 'Item' not in response:
            logger.warning(f"Event not found: {event_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        logger.info(f"Retrieved event: {event_id}")
        return Event(**response['Item'])
    except HTTPException:
        raise
    except ClientError as e:
        logger.error(f"DynamoDB error getting event: {e.response['Error']['Message']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@app.put(
    "/events/{event_id}",
    response_model=Event,
    responses={
        200: {"description": "Event updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input or no fields to update"},
        404: {"model": ErrorResponse, "description": "Event not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def update_event(event_id: str, event_update: EventUpdate):
    """
    Update an existing event. Only provided fields will be updated.
    All validation rules apply to updated fields.
    """
    if not event_id or not event_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event ID cannot be empty"
        )
    
    try:
        # Check if event exists
        response = table.get_item(Key={'eventId': event_id})
        if 'Item' not in response:
            logger.warning(f"Event not found for update: {event_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        # Build update expression
        update_data = event_update.dict(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        update_expr = "SET "
        expr_attr_values = {}
        expr_attr_names = {}
        
        for idx, (key, value) in enumerate(update_data.items()):
            if idx > 0:
                update_expr += ", "
            expr_attr_names[f"#{key}"] = key
            expr_attr_values[f":{key}"] = value
            update_expr += f"#{key} = :{key}"
        
        # Add updatedAt timestamp
        expr_attr_names["#updatedAt"] = "updatedAt"
        expr_attr_values[":updatedAt"] = datetime.utcnow().isoformat()
        update_expr += ", #updatedAt = :updatedAt"
        
        response = table.update_item(
            Key={'eventId': event_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values,
            ReturnValues="ALL_NEW"
        )
        
        logger.info(f"Updated event: {event_id}")
        return Event(**response['Attributes'])
    except HTTPException:
        raise
    except ClientError as e:
        logger.error(f"DynamoDB error updating event: {e.response['Error']['Message']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update event in database"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@app.delete(
    "/events/{event_id}",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Event deleted successfully"},
        204: {"description": "Event deleted successfully"},
        404: {"model": ErrorResponse, "description": "Event not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def delete_event(event_id: str):
    """
    Delete an event by its ID.
    Returns 200 if the event doesn't exist.
    """
    if not event_id or not event_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event ID cannot be empty"
        )
    
    try:
        # Check if event exists
        response = table.get_item(Key={'eventId': event_id})
        if 'Item' not in response:
            logger.warning(f"Event not found for deletion: {event_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        
        table.delete_item(Key={'eventId': event_id})
        logger.info(f"Deleted event: {event_id}")
        return {"message": "Event deleted successfully"}
    except HTTPException:
        raise
    except ClientError as e:
        logger.error(f"DynamoDB error deleting event: {e.response['Error']['Message']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete event from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
