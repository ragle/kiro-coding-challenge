# Events Management API

A serverless REST API for managing events, built with FastAPI, AWS Lambda, API Gateway, and DynamoDB.

## Architecture

- **Backend**: FastAPI (Python 3.11)
- **Infrastructure**: AWS CDK (Python)
- **Compute**: AWS Lambda
- **API**: Amazon API Gateway
- **Database**: Amazon DynamoDB
- **Deployment**: Serverless architecture

## Features

- ✅ Full CRUD operations for events
- ✅ Input validation with Pydantic
- ✅ CORS enabled for web access
- ✅ Comprehensive error handling
- ✅ Query filtering by status
- ✅ Custom event IDs support
- ✅ Automatic timestamps (createdAt, updatedAt)

## Event Schema

```json
{
  "eventId": "string (UUID or custom)",
  "title": "string (1-200 chars)",
  "description": "string (1-2000 chars)",
  "date": "string (ISO format)",
  "location": "string (1-300 chars)",
  "capacity": "integer (1-100000)",
  "organizer": "string (1-200 chars)",
  "status": "string (scheduled|ongoing|completed|cancelled|active)"
}
```

## API Endpoints

### Base URL
```
https://bc37aqhsv1.execute-api.us-west-2.amazonaws.com/prod/
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/events` | List all events |
| GET | `/events?status=active` | Filter events by status |
| GET | `/events/{eventId}` | Get specific event |
| POST | `/events` | Create new event |
| PUT | `/events/{eventId}` | Update event |
| DELETE | `/events/{eventId}` | Delete event |

## Usage Examples

### Create Event
```bash
curl -X POST "https://bc37aqhsv1.execute-api.us-west-2.amazonaws.com/prod/events" \
  -H "Content-Type: application/json" \
  -d '{
    "eventId": "my-event-123",
    "title": "Tech Conference 2024",
    "description": "Annual technology conference",
    "date": "2024-12-15",
    "location": "San Francisco Convention Center",
    "capacity": 500,
    "organizer": "Tech Events Inc",
    "status": "active"
  }'
```

### List All Events
```bash
curl -X GET "https://bc37aqhsv1.execute-api.us-west-2.amazonaws.com/prod/events"
```

### Filter Events by Status
```bash
curl -X GET "https://bc37aqhsv1.execute-api.us-west-2.amazonaws.com/prod/events?status=active"
```

### Get Specific Event
```bash
curl -X GET "https://bc37aqhsv1.execute-api.us-west-2.amazonaws.com/prod/events/my-event-123"
```

### Update Event
```bash
curl -X PUT "https://bc37aqhsv1.execute-api.us-west-2.amazonaws.com/prod/events/my-event-123" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Tech Conference 2024",
    "capacity": 600
  }'
```

### Delete Event
```bash
curl -X DELETE "https://bc37aqhsv1.execute-api.us-west-2.amazonaws.com/prod/events/my-event-123"
```

## Local Development

### Prerequisites

- Python 3.11+
- Node.js (for AWS CDK)
- AWS CLI configured
- AWS CDK CLI (`npm install -g aws-cdk`)

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd <repository-name>
```

2. **Install backend dependencies**
```bash
cd backend
pip install -r requirements.txt
```

3. **Install infrastructure dependencies**
```bash
cd infrastructure
pip install -r requirements.txt
```

### Running Locally

Run the FastAPI application locally:

```bash
cd backend
uvicorn main:app --reload
```

Access the API at `http://localhost:8000`

Interactive API docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### API Documentation

View the generated API documentation:

```bash
# Generate documentation
cd backend
python3.11 -m pdoc main -o docs --no-search

# View documentation
open docs/index.html
```

The documentation is also available in the `backend/docs/` directory.

## Deployment

### Prerequisites

- AWS account with appropriate permissions
- AWS credentials configured

### Deploy to AWS

1. **Bootstrap CDK (first time only)**
```bash
cd infrastructure
cdk bootstrap aws://<account-id>/<region>
```

2. **Build Lambda package**
```bash
cd backend
rm -rf package && mkdir package
python3.11 -m pip install --platform manylinux2014_x86_64 \
  --only-binary=:all: -r requirements.txt -t package/
cp main.py lambda_handler.py package/
```

3. **Deploy the stack**
```bash
cd infrastructure
cdk deploy
```

The deployment will output the API Gateway URL.

### Update Deployment

After making changes:

```bash
# Rebuild Lambda package
cd backend
rm -rf package && mkdir package
python3.11 -m pip install --platform manylinux2014_x86_64 \
  --only-binary=:all: -r requirements.txt -t package/
cp main.py lambda_handler.py package/

# Redeploy
cd ../infrastructure
cdk deploy
```

### Destroy Infrastructure

```bash
cd infrastructure
cdk destroy
```

## Project Structure

```
.
├── backend/
│   ├── main.py              # FastAPI application
│   ├── lambda_handler.py    # Lambda handler wrapper
│   ├── requirements.txt     # Python dependencies
│   └── package/            # Lambda deployment package
├── infrastructure/
│   ├── app.py              # CDK app entry point
│   ├── cdk.json            # CDK configuration
│   ├── requirements.txt    # CDK dependencies
│   └── stacks/
│       └── backend_stack.py # Infrastructure definition
└── README.md
```

## Infrastructure Components

### DynamoDB Table
- **Name**: EventsTable
- **Partition Key**: eventId (String)
- **Billing**: Pay-per-request
- **Removal Policy**: Destroy (for dev/testing)

### Lambda Function
- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 30 seconds
- **Handler**: lambda_handler.handler

### API Gateway
- **Type**: REST API
- **CORS**: Enabled for all origins
- **Integration**: Lambda Proxy

## Error Handling

The API returns appropriate HTTP status codes:

- `200` - Success
- `201` - Created
- `204` - No Content (alternative for DELETE)
- `400` - Bad Request (validation errors)
- `404` - Not Found
- `500` - Internal Server Error

Error response format:
```json
{
  "detail": "Error message"
}
```

## Validation Rules

- **title**: 1-200 characters
- **description**: 1-2000 characters
- **date**: ISO format (YYYY-MM-DD or ISO 8601)
- **location**: 1-300 characters
- **capacity**: 1-100,000
- **organizer**: 1-200 characters
- **status**: Must be one of: scheduled, ongoing, completed, cancelled, active

## Security

- CORS configured for web access
- Input validation on all endpoints
- DynamoDB access restricted to Lambda execution role
- API Gateway throttling enabled

## Monitoring

View Lambda logs:
```bash
aws logs tail /aws/lambda/<function-name> --follow
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
