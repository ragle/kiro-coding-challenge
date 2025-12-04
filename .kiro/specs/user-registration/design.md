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
Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: User creation with valid name produces unique identifier
*For any* valid user name (1-200 characters), creating a user should result in a unique userId being assigned.
**Validates: Requirements 1.1**

### Property 2: Custom userId is preserved when provided
*For any* user creation request with a custom userId that doesn't already exist, the returned user should have the exact userId that was provided.
**Validates: Requirements 1.2**

### Property 3: Auto-generated userIds are valid UUIDs
*For any* user creation request without a userId, the generated userId should be a valid UUID format.
**Validates: Requirements 1.3**

### Property 4: User data persistence round-trip
*For any* created user, retrieving the user by userId should return the same name and include a createdAt timestamp.
**Validates: Requirements 1.4**

### Property 5: User creation response contains required fields
*For any* successful user creation, the response should contain both userId and name fields.
**Validates: Requirements 1.5**

### Property 6: Name length validation
*For any* user creation request, names outside the range of 1-200 characters should be rejected with a validation error.
**Validates: Requirements 2.1, 2.2**

### Property 7: Registration creation with available capacity
*For any* event with available capacity and any valid user, registering the user should create a registration record with status "confirmed".
**Validates: Requirements 3.1**

### Property 8: Registration data persistence
*For any* created registration, querying the Registration Table should return a record with userId, eventId, status, and registeredAt fields.
**Validates: Requirements 3.2**

### Property 9: Registration response structure
*For any* successful registration, the response should include userId, eventId, and status fields.
**Validates: Requirements 3.3**

### Property 10: Capacity enforcement
*For any* event at full capacity (registrations == capacity) without waitlist enabled, attempting to register another user should be rejected with an error indicating the event is full.
**Validates: Requirements 4.1**

### Property 11: Registration count equals confirmed registrations
*For any* event, the count of confirmed registrations should equal the number of registration records with status "confirmed" for that event.
**Validates: Requirements 4.2, 4.3**

### Property 12: Unlimited registration without capacity constraint
*For any* event without a capacity constraint, registering any number of users should succeed.
**Validates: Requirements 4.4**

### Property 13: Waitlist addition for full events
*For any* full event with waitlist enabled, attempting to register a user should add them to the waitlist instead of creating a registration.
**Validates: Requirements 5.1**

### Property 14: Waitlist data persistence
*For any* user added to a waitlist, querying the Waitlist Table should return an entry with userId, eventId, position, and addedAt fields.
**Validates: Requirements 5.2**

### Property 15: Sequential waitlist positions
*For any* event, adding multiple users to the waitlist should assign sequential position numbers (1, 2, 3, ...) in the order they were added.
**Validates: Requirements 5.3**

### Property 16: Waitlist response structure
*For any* successful waitlist addition, the response should include userId, eventId, and position fields.
**Validates: Requirements 5.4**

### Property 17: Unregistration removes record
*For any* confirmed registration, unregistering should remove the registration record from the Registration Table.
**Validates: Requirements 6.1**

### Property 18: Waitlist promotion on unregistration
*For any* full event with a non-empty waitlist, when a user unregisters, the user at waitlist position 1 should be promoted to a confirmed registration and removed from the waitlist.
**Validates: Requirements 6.2, 6.3**

### Property 19: Unregistration confirmation
*For any* successful unregistration, the response should include a confirmation message.
**Validates: Requirements 6.5**

### Property 20: User registrations list completeness
*For any* user with confirmed registrations, requesting their registered events should return all events they are registered for with full event details.
**Validates: Requirements 7.1, 7.2**

### Property 21: Registration timestamps included
*For any* user's registered events list, each event should include the registeredAt timestamp.
**Validates: Requirements 7.4**

### Property 22: User waitlist entries completeness
*For any* user with waitlist entries, requesting their waitlist should return all events they are waitlisted for with position and full event details.
**Validates: Requirements 8.1, 8.2, 8.3**

### Property 23: HTTP 201 for successful creation
*For any* successful user or registration creation, the HTTP response status code should be 201 Created.
**Validates: Requirements 9.1**

### Property 24: HTTP 400 for validation errors
*For any* request with validation errors, the HTTP response status code should be 400 Bad Request with error details.
**Validates: Requirements 9.2**

### Property 25: HTTP 404 for missing resources
*For any* request for a non-existent resource, the HTTP response status code should be 404 Not Found.
**Validates: Requirements 9.3**

### Property 26: HTTP 409 for conflicts
*For any* request that creates a conflict (duplicate userId, duplicate registration), the HTTP response status code should be 409 Conflict.
**Validates: Requirements 9.4**

### Property 27: Standard error response format
*For any* error response, the response body should include a "detail" field with an error message.
**Validates: Requirements 9.5**

### Property 28: HTTP 500 for unexpected errors
*For any* unexpected system error, the HTTP response status code should be 500 Internal Server Error.
**Validates: Requirements 10.5**

## Error Handling

### Error Categories

1. **Validation Errors (400 Bad Request)**
   - Invalid name length
   - Missing required fields
   - Invalid data types

2. **Not Found Errors (404 Not Found)**
   - User does not exist
   - Event does not exist
   - Registration does not exist

3. **Conflict Errors (409 Conflict)**
   - Duplicate userId
   - User already registered for event
   - User already on waitlist
   - Event at full capacity (without waitlist)

4. **Server Errors (500 Internal Server Error)**
   - DynamoDB connection failures
   - Unexpected exceptions
   - Data consistency issues

### Error Response Format

All errors follow the standard format:

```json
{
  "detail": "Human-readable error message"
}
```

### Atomic Operations

To prevent race conditions in capacity management:

1. **Registration with Capacity Check**: Use DynamoDB conditional writes to ensure capacity is not exceeded
2. **Waitlist Promotion**: Use transactions to atomically remove from waitlist and create registration
3. **Duplicate Prevention**: Use conditional writes to prevent duplicate registrations

### Retry Logic

- All operations should be idempotent where possible
- Use conditional writes to prevent duplicate operations
- Client should retry on 500 errors with exponential backoff

## Testing Strategy

### Unit Testing

Unit tests will verify specific behaviors and edge cases:

1. **User Creation**
   - Valid user creation with auto-generated ID
   - Valid user creation with custom ID
   - Rejection of invalid names (empty, too long)
   - Rejection of duplicate userIds

2. **Event Registration**
   - Successful registration with available capacity
   - Rejection when event is full (no waitlist)
   - Rejection of duplicate registrations
   - Rejection when event doesn't exist

3. **Waitlist Management**
   - Addition to waitlist when event is full
   - Sequential position assignment
   - Promotion on unregistration
   - Rejection of duplicate waitlist entries

4. **Data Retrieval**
   - User registrations list
   - User waitlist entries
   - Empty lists for users with no registrations/waitlist entries

### Property-Based Testing

Property-based tests will verify universal properties across many randomly generated inputs using the **Hypothesis** library for Python. Each property test should run a minimum of 100 iterations.

Each property-based test must be tagged with a comment explicitly referencing the correctness property from this design document using the format: `# Feature: user-registration, Property {number}: {property_text}`

The following properties will be implemented as property-based tests:

1. **Property 1**: User creation with valid names
2. **Property 2**: Custom userId preservation
3. **Property 3**: UUID format validation
4. **Property 4**: User data round-trip
5. **Property 6**: Name length validation
6. **Property 7**: Registration with available capacity
7. **Property 10**: Capacity enforcement
8. **Property 11**: Registration counting
9. **Property 12**: Unlimited registration
10. **Property 13**: Waitlist addition
11. **Property 15**: Sequential waitlist positions
12. **Property 18**: Waitlist promotion
13. **Property 20**: User registrations completeness
14. **Property 22**: User waitlist completeness
15. **Property 23-28**: HTTP status code validation

### Integration Testing

Integration tests will verify end-to-end workflows:

1. **Complete Registration Flow**: Create user → Create event → Register user → Verify registration
2. **Capacity and Waitlist Flow**: Fill event → Add to waitlist → Unregister user → Verify promotion
3. **Multiple Users Flow**: Create multiple users → Register for same event → Verify capacity enforcement

### Test Data Generation

For property-based testing, generators will create:
- Random valid user names (1-200 characters)
- Random userIds (UUIDs and custom strings)
- Random event configurations (with/without capacity, with/without waitlist)
- Random registration scenarios (various capacity levels)

## Implementation Notes

### DynamoDB Considerations

1. **Conditional Writes**: Use `ConditionExpression` to prevent race conditions
   ```python
   # Example: Prevent duplicate userId
   table.put_item(
       Item=user_item,
       ConditionExpression='attribute_not_exists(userId)'
   )
   ```

2. **Transactions**: Use DynamoDB transactions for waitlist promotion to ensure atomicity
   ```python
   # Atomic promotion: remove from waitlist + create registration
   dynamodb.transact_write_items(
       TransactItems=[
           {'Delete': {'TableName': 'Waitlist', 'Key': {...}}},
           {'Put': {'TableName': 'Registrations', 'Item': {...}}}
       ]
   )
   ```

3. **GSI Queries**: Use Global Secondary Indexes for efficient user-centric queries
   - UserRegistrationsIndex: Query all registrations for a user
   - UserWaitlistIndex: Query all waitlist entries for a user

### Performance Considerations

1. **Batch Operations**: When retrieving event details for multiple registrations, use batch_get_item
2. **Caching**: Consider caching event capacity information for frequently accessed events
3. **Pagination**: Implement pagination for large result sets (user registrations, event registrations)

### Security Considerations

1. **Input Validation**: Validate all inputs using Pydantic models
2. **SQL Injection Prevention**: Not applicable (using DynamoDB)
3. **Rate Limiting**: Implement rate limiting at API Gateway level
4. **Logging**: Log all operations but exclude sensitive data

### Monitoring and Observability

1. **Metrics to Track**:
   - User creation rate
   - Registration success/failure rate
   - Waitlist addition rate
   - Promotion rate
   - API latency (p50, p95, p99)

2. **Alarms**:
   - High error rate (> 5%)
   - High latency (> 1000ms p95)
   - DynamoDB throttling

3. **Logs**:
   - All user creations
   - All registrations and unregistrations
   - All waitlist operations
   - All errors with context
