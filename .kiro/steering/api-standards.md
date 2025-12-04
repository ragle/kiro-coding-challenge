---
inclusion: fileMatch
fileMatchPattern: '(main|api|routes|endpoints|handler)\.py$'
---

# API Standards and Conventions

This steering file defines REST API standards and conventions for this project. It is automatically included when working with API-related files.

## REST API Conventions

### HTTP Methods

Use HTTP methods according to their semantic meaning:

- **GET**: Retrieve resources (read-only, idempotent, cacheable)
  - List resources: `GET /events`
  - Get single resource: `GET /events/{id}`
  - Query/filter: `GET /events?status=active`

- **POST**: Create new resources (non-idempotent)
  - Create resource: `POST /events`
  - Returns `201 Created` with resource in response body
  - Include `Location` header with resource URI (optional)

- **PUT**: Update entire resource (idempotent)
  - Update resource: `PUT /events/{id}`
  - Returns `200 OK` with updated resource
  - All fields should be provided (full replacement)

- **PATCH**: Partial update (idempotent)
  - Update specific fields: `PATCH /events/{id}`
  - Returns `200 OK` with updated resource
  - Only modified fields need to be provided

- **DELETE**: Remove resources (idempotent)
  - Delete resource: `DELETE /events/{id}`
  - Returns `200 OK`, `202 Accepted`, or `204 No Content`
  - May return deleted resource or confirmation message

### HTTP Status Codes

Use appropriate status codes to indicate the result of operations:

#### Success Codes (2xx)
- **200 OK**: Successful GET, PUT, PATCH, or DELETE
- **201 Created**: Successful POST that creates a resource
- **202 Accepted**: Request accepted but processing not complete
- **204 No Content**: Successful request with no response body

#### Client Error Codes (4xx)
- **400 Bad Request**: Invalid request syntax or validation failure
- **401 Unauthorized**: Authentication required or failed
- **403 Forbidden**: Authenticated but not authorized
- **404 Not Found**: Resource does not exist
- **409 Conflict**: Request conflicts with current state
- **422 Unprocessable Entity**: Validation errors (alternative to 400)
- **429 Too Many Requests**: Rate limit exceeded

#### Server Error Codes (5xx)
- **500 Internal Server Error**: Unexpected server error
- **502 Bad Gateway**: Invalid response from upstream server
- **503 Service Unavailable**: Server temporarily unavailable
- **504 Gateway Timeout**: Upstream server timeout

## Error Response Format

All error responses must follow a consistent JSON structure:

### Standard Error Response

```json
{
  "detail": "Human-readable error message"
}
```

### Enhanced Error Response (Optional)

For more detailed error information:

```json
{
  "detail": "Human-readable error message",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2024-12-15T10:30:00Z",
  "path": "/events/123",
  "errors": [
    {
      "field": "capacity",
      "message": "Must be between 1 and 100000"
    }
  ]
}
```

### Validation Error Response

For input validation failures (400 or 422):

```json
{
  "detail": "Validation failed",
  "errors": [
    {
      "field": "email",
      "message": "Invalid email format",
      "type": "value_error"
    },
    {
      "field": "capacity",
      "message": "Must be greater than 0",
      "type": "value_error"
    }
  ]
}
```

## JSON Response Format Standards

### Success Response Structure

#### Single Resource
```json
{
  "eventId": "123",
  "title": "Event Title",
  "description": "Event description",
  "date": "2024-12-15",
  "location": "Event Location",
  "capacity": 100,
  "organizer": "Organizer Name",
  "status": "active",
  "createdAt": "2024-12-01T10:00:00Z",
  "updatedAt": "2024-12-10T15:30:00Z"
}
```

#### Resource Collection
```json
[
  {
    "eventId": "123",
    "title": "Event 1",
    ...
  },
  {
    "eventId": "456",
    "title": "Event 2",
    ...
  }
]
```

#### Paginated Collection (Optional Enhancement)
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "pageSize": 20,
  "hasNext": true,
  "hasPrevious": false
}
```

### Field Naming Conventions

- Use **camelCase** for JSON field names (e.g., `eventId`, `createdAt`)
- Use **snake_case** for Python variables (e.g., `event_id`, `created_at`)
- Be consistent across all endpoints
- Use descriptive, self-documenting names

### Data Type Standards

- **Dates/Times**: ISO 8601 format (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SSZ`)
- **Booleans**: `true` or `false` (lowercase)
- **Null values**: Use `null` (not empty strings)
- **Numbers**: No quotes around numeric values
- **IDs**: Strings (UUIDs or custom identifiers)

## Request Validation

### Input Validation Rules

Always validate:
1. **Required fields**: Ensure all mandatory fields are present
2. **Data types**: Verify correct types (string, number, boolean)
3. **Format**: Validate formats (email, URL, date, UUID)
4. **Range**: Check min/max values for numbers
5. **Length**: Enforce min/max length for strings
6. **Enum values**: Validate against allowed values
7. **Business rules**: Apply domain-specific validation

### Validation Error Handling

- Return `400 Bad Request` for validation errors
- Provide clear, actionable error messages
- Include field names in error responses
- Validate early (fail fast)
- Never expose internal error details to clients

## CORS Configuration

For web API access:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production CORS Settings:**
- Specify exact allowed origins (no wildcards)
- Limit allowed methods to those actually used
- Restrict allowed headers
- Set appropriate `max_age` for preflight caching

## API Documentation

### Endpoint Documentation

Each endpoint should include:
- Clear description of purpose
- Request parameters (path, query, body)
- Request body schema with examples
- Response schema with examples
- Possible status codes and error responses
- Authentication requirements (if applicable)

### Example Endpoint Documentation

```python
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
    Create a new event.
    
    - **title**: Event title (1-200 characters)
    - **description**: Event description (1-2000 characters)
    - **date**: Event date in ISO format
    - **location**: Event location (1-300 characters)
    - **capacity**: Event capacity (1-100000)
    - **organizer**: Organizer name (1-200 characters)
    - **status**: Event status (scheduled, ongoing, completed, cancelled, active)
    """
    ...
```

## Security Best Practices

### Input Sanitization
- Validate and sanitize all user input
- Use Pydantic models for automatic validation
- Escape special characters when necessary
- Prevent SQL injection (use parameterized queries)
- Prevent XSS attacks (sanitize HTML content)

### Error Messages
- Don't expose sensitive information in errors
- Don't reveal internal implementation details
- Use generic messages for authentication failures
- Log detailed errors server-side only

### Rate Limiting
- Implement rate limiting for public APIs
- Return `429 Too Many Requests` when exceeded
- Include `Retry-After` header

## Query Parameters

### Filtering
- Use query parameters for filtering: `?status=active`
- Support multiple filters: `?status=active&location=SF`
- Use clear, descriptive parameter names

### Sorting
- Use `sort` or `orderBy` parameter: `?sort=date`
- Support ascending/descending: `?sort=-date` (descending)

### Pagination
- Use `page` and `pageSize` or `limit` and `offset`
- Example: `?page=1&pageSize=20`
- Include pagination metadata in response

### Search
- Use `q` or `search` parameter: `?q=conference`
- Support partial matching when appropriate

## Idempotency

- **GET, PUT, DELETE**: Must be idempotent
- **POST**: Generally not idempotent
- Consider idempotency keys for critical POST operations
- Document idempotency behavior for each endpoint

## Versioning (Future Consideration)

When API versioning is needed:
- URL versioning: `/v1/events`, `/v2/events`
- Header versioning: `Accept: application/vnd.api.v1+json`
- Query parameter: `?version=1`

Choose one strategy and apply consistently.

## Testing Standards

### API Testing Requirements
- Test all endpoints (CRUD operations)
- Test validation rules
- Test error conditions
- Test edge cases
- Test authentication/authorization
- Test rate limiting
- Test CORS configuration

### Example Test Cases
- Valid requests return correct status codes
- Invalid requests return 400 with error details
- Missing resources return 404
- Unauthorized requests return 401/403
- Server errors return 500

## Performance Considerations

- Use appropriate database indexes
- Implement caching where appropriate
- Paginate large result sets
- Use async/await for I/O operations
- Monitor and log slow queries
- Set appropriate timeout values

## Logging

Log important events:
- Request/response for debugging
- Errors and exceptions
- Authentication attempts
- Rate limit violations
- Slow queries or operations

**Don't log:**
- Sensitive data (passwords, tokens, PII)
- Full request bodies in production
- Excessive debug information in production
