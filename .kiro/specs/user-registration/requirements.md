# Requirements Document

## Introduction

This document defines the requirements for implementing a user registration system for events in the Events Management API. The system will enable users to register for events, manage event capacity constraints, handle waitlists, and track user event registrations. This feature extends the existing serverless architecture built with FastAPI, AWS Lambda, API Gateway, and DynamoDB.



## Glossary

- **User**: An individual who can register for events in the system
- **Event**: A scheduled occurrence with capacity constraints that users can register for
- **Registration System**: The collection of components that handle user creation and event registration
- **Event Registration**: The association between a user and an event indicating the user is attending
- **Event Capacity**: The maximum number of users that can register for an event
- **Waitlist**: A queue of users waiting for spots to become available in a full event
- **User Table**: The DynamoDB table storing user information
- **Registration Table**: The DynamoDB table storing event registration records
- **Waitlist Table**: The DynamoDB table storing waitlist entries for full events

## Requirements

### Requirement 1

**User Story:** As a system user, I want to create a user account with basic information, so that I can register for events.

#### Acceptance Criteria

1. WHEN a user creation request is submitted with a valid name THEN the Registration System SHALL create a new user with a unique user identifier
2. WHEN a user creation request is submitted with a custom userId THEN the Registration System SHALL use the provided userId if it does not already exist
3. WHEN a user creation request is submitted without a userId THEN the Registration System SHALL generate a unique UUID as the userId
4. WHEN a user is created THEN the Registration System SHALL store the userId, name, and creation timestamp in the User Table
5. WHEN a user creation succeeds THEN the Registration System SHALL return the created user with userId and name
6. WHEN a user creation request includes a name THEN the Registration System SHALL validate that the name contains between 1 and 200 characters
7. WHEN a user creation request includes an invalid name THEN the Registration System SHALL reject the request and return a validation error
8. WHEN a user creation request attempts to use a userId that already exists THEN the Registration System SHALL reject the request and return an error indicating the userId is already in use

### Requirement 2

**User Story:** As a user, I want to register for an event, so that I can attend the event.

#### Acceptance Criteria

1. WHEN a user registers for an event with available capacity THEN the Registration System SHALL create an event registration record
2. WHEN a user registers for an event THEN the Registration System SHALL store the userId, eventId, registration status, and registration timestamp in the Registration Table
3. WHEN a user successfully registers for an event THEN the Registration System SHALL return the registration details including userId, eventId, and status
4. WHEN a user attempts to register for an event that does not exist THEN the Registration System SHALL reject the registration and return an error
5. WHEN a user attempts to register for an event they are already registered for THEN the Registration System SHALL reject the registration and return an error indicating duplicate registration

### Requirement 3

**User Story:** As an event organizer, I want events to enforce capacity constraints, so that events do not become overcrowded.

#### Acceptance Criteria

1. WHEN a user attempts to register for an event at full capacity without a waitlist THEN the Registration System SHALL reject the registration and return an error indicating the event is full
2. WHEN the Registration System checks event capacity THEN the system SHALL count the number of confirmed registrations for the event
3. WHEN the number of confirmed registrations equals the event capacity THEN the Registration System SHALL consider the event full
4. WHEN an event has no capacity constraint defined THEN the Registration System SHALL allow unlimited registrations

### Requirement 4

**User Story:** As a user, I want to be added to a waitlist when an event is full, so that I can attend if spots become available.

#### Acceptance Criteria

1. WHEN a user attempts to register for a full event with a waitlist enabled THEN the Registration System SHALL add the user to the waitlist
2. WHEN a user is added to a waitlist THEN the Registration System SHALL store the userId, eventId, waitlist position, and timestamp in the Waitlist Table
3. WHEN a user is added to a waitlist THEN the Registration System SHALL assign a sequential position number based on the order of waitlist entries
4. WHEN a user is successfully added to a waitlist THEN the Registration System SHALL return the waitlist entry with userId, eventId, and position
5. WHEN a user attempts to join a waitlist they are already on THEN the Registration System SHALL reject the request and return an error

### Requirement 5

**User Story:** As a user, I want to unregister from an event, so that I can free up my spot for other attendees.

#### Acceptance Criteria

1. WHEN a user unregisters from an event THEN the Registration System SHALL remove the event registration record
2. WHEN a user unregisters from a full event with a waitlist THEN the Registration System SHALL promote the first user from the waitlist to confirmed registration
3. WHEN a waitlist user is promoted THEN the Registration System SHALL create a registration record for the promoted user and remove their waitlist entry
4. WHEN a user attempts to unregister from an event they are not registered for THEN the Registration System SHALL return an error
5. WHEN a user unregisters successfully THEN the Registration System SHALL return a confirmation message

### Requirement 6

**User Story:** As a user, I want to view all events I am registered for, so that I can track my event attendance.

#### Acceptance Criteria

1. WHEN a user requests their registered events THEN the Registration System SHALL return all events the user has confirmed registrations for
2. WHEN the Registration System retrieves registered events THEN the system SHALL include full event details for each registration
3. WHEN a user has no registered events THEN the Registration System SHALL return an empty list
4. WHEN the Registration System returns registered events THEN the system SHALL include the registration timestamp for each event

### Requirement 7

**User Story:** As a user, I want to view my waitlist status, so that I know which events I am waiting to attend.

#### Acceptance Criteria

1. WHEN a user requests their waitlist entries THEN the Registration System SHALL return all events the user is waitlisted for
2. WHEN the Registration System retrieves waitlist entries THEN the system SHALL include the waitlist position for each entry
3. WHEN the Registration System retrieves waitlist entries THEN the system SHALL include full event details for each waitlisted event
4. WHEN a user has no waitlist entries THEN the Registration System SHALL return an empty list
