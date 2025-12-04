# Design Document

## Overview

The user registration system extends the existing Events Management API to enable users to register for events with capacity management and waitlist functionality. The system maintains three primary data entities: Users, Event Registrations, and Waitlist Entries. It integrates seamlessly with the existing event management infrastructure using the same serverless architecture (FastAPI, AWS Lambda, API Gateway, DynamoDB).

### Key Features
- User creation and management
- Event registration with capacity enforcement
- Automatic waitlist management for full events
- Waitlist promotion when spots become available
- User event listing and waitlist status tracking

## Architecture

### System Components

The system follows a layered architecture consistent with the existing Events API:

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
│              (REST API Endpoints)                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  Lambda Function                        │
│                   (FastAPI App)                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │           API Route Handlers                      │ │
│  │  - User Management                                │ │
│  │  - Registration Management                        │ │
│  │  - Waitlist Management                            │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │           Business Logic Layer                    │ │
│  │  - Capacity Validation                            │ │
│  │  - Waitlist Promotion                             │ │
│  │  - Registration State Management                  │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │           Data Access Layer                       │ │
│  │  - User Repository                                │ │
│  │  - Registration Repository                        │ │
│  │  - Waitlist Repository                            │ │
│  │  - Event Repository (existing)                    │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    DynamoDB                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Users Table  │  │ Registrations│  │  Waitlist    │ │
│  │              │  │    Table     │  │   Table      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐                                      │
│  │ Events Table │  (existing)                          │
│  └──────────────┘                                      │
└─────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Consistency with Existing API**: Follow the same patterns, validation approach, and error handling as the Events API
2. **Serverless Architecture**: Leverage AWS Lambda for compute, DynamoDB for storage, maintaining stateless operations
3. **Atomic Operations**: Use DynamoDB conditional writes to prevent race conditions in capacity management
4. **Idempotency**: Design operations to be safely retryable
5. **Separation of Concerns**: Clear boundaries between API, business logic, and data access layers

## Components and Interfaces

### API Endpoints

#### User Management

**POST /users**
- Create a new user
- Request body: `{ "userId": "optional-custom-id", "name": "User Name" }`
- Response: `201 Created` with user object
- Errors: `400 Bad Request` (validation), `409 Conflict` (duplicate userId)

**GET /users/{userId}**
- Retrieve user details
- Response: `200 OK` with user object
- Errors: `404 Not Found`

#### Event Registration

**POST /events/{eventId}/registrations**
- Register a user for an event
- Request body: `{ "userId": "user-123" }`
- Response: `201 Created` with registration object OR waitlist entry if event is full
- Errors: `400 Bad Request`, `404 Not Found` (event/user), `409 Conflict` (already registered)

**DELETE /events/{eventId}/registrations/{userId}**
- Unregister a user from an event
- Response: `200 OK` with confirmation message
- Errors: `404 Not Found` (registration not found)

**GET /users/{userId}/registrations**
- List all events a user is registered for
- Response: `200 OK` with array of event objects with registration details
- Errors: `404 Not Found` (user)

**GET /users/{userId}/waitlist**
- List all events a user is waitlisted for
- Response: `200 OK` with array of waitlist entries including position and event details
- Errors: `404 Not Found` (user)

**GET /events/{eventId}/registrations**
- List all users registered for an event
- Response: `200 OK` with array of registration objects
- Errors: `404 Not Found` (event)

**GET /events/{eventId}/waitlist**
- List all users on the waitlist for an event
- Response: `200 OK` with array of waitlist entries ordered by position
- Errors: `404 Not Found` (event)

### Business Logic Components

#### CapacityManager
Responsible for checking and enforcing event capacity constraints.

```python
class CapacityManager:
    def check_capacity(self, event_id: str) -> CapacityStatus
    def is_event_full(self, event_id: str) -> bool
    def get_available_spots(self, event_id: str) -> int
```

#### WaitlistManager
Handles waitlist operations and promotions.

```python
class WaitlistManager:
    def add_to_waitlist(self, user_id: str, event_id: str) -> WaitlistEntry
    def promote_from_waitlist(self, event_id: str) -> Optional[str]
    def get_next_position(self, event_id: str) -> int
    def remove_from_waitlist(self, user_id: str, event_id: str) -> None
```

#### RegistrationManager
Orchestrates the registration process including capacity checks and waitlist handling.

```python
class RegistrationManager:
    def register_user(self, user_id: str, event_id: str) -> RegistrationResult
    def unregister_user(self, user_id: str, event_id: str) -> None
    def get_user_registrations(self, user_id: str) -> List[Registration]
```

## Data Models

### User

```python
class User(BaseModel):
    userId: str = Field(..., description="Unique user identifier")
    name: str = Field(..., min_length=1, max_length=200, description="User name")
    createdAt: str = Field(..., description="ISO timestamp of user creation")
```

**DynamoDB Schema (Users Table)**
- Partition Key: `userId` (String)
- Attributes: `name`, `createdAt`

### Registration

```python
class Registration(BaseModel):
    userId: str = Field(..., description="User identifier")
    eventId: str = Field(..., description="Event identifier")
    status: str = Field(default="confirmed", description="Registration status")
    registeredAt: str = Field(..., description="ISO timestamp of registration")
```

**DynamoDB Schema (Registrations Table)**
- Partition Key: `eventId` (String)
- Sort Key: `userId` (String)
- Attributes: `status`, `registeredAt`
- GSI: `UserRegistrationsIndex` - Partition Key: `userId`, Sort Key: `registeredAt`

### WaitlistEntry

```python
class WaitlistEntry(BaseModel):
    userId: str = Field(..., description="User identifier")
    eventId: str = Field(..., description="Event identifier")
    position: int = Field(..., description="Position in waitlist queue")
    addedAt: str = Field(..., description="ISO timestamp when added to waitlist")
```

**DynamoDB Schema (Waitlist Table)**
- Partition Key: `eventId` (String)
- Sort Key: `position` (Number)
- Attributes: `userId`, `addedAt`
- GSI: `UserWaitlistIndex` - Partition Key: `userId`, Sort Key: `addedAt`

### Event (Extended)

The existing Event model is extended with optional capacity fields:

```python
class Event(BaseModel):
    # ... existing fields ...
    capacity: Optional[int] = Field(None, description="Maximum number of registrations")
    waitlistEnabled: bool = Field(default=False, description="Whether waitlist is enabled")
```

## 