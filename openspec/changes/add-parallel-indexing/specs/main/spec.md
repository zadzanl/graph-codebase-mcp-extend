## MODIFIED Requirements

### Requirement: High-Concurrency Indexing
The system SHALL process files in parallel to reduce indexing time.

#### Scenario: Free-threaded Python
- **GIVEN** the application is running on a free-threaded Python 3.14+ interpreter
- **WHEN** indexing a codebase
- **THEN** the system SHALL use a `ThreadPoolExecutor` to process files concurrently.

#### Scenario: GIL-bound Python
- **GIVEN** the application is running on a standard (GIL-bound) Python interpreter
- **WHEN** indexing a codebase
- **THEN** the system SHALL use a `ProcessPoolExecutor` to process files in parallel.

## ADDED Requirements

### Requirement: Thread-Safe Database Operations
The system SHALL ensure all database operations are performed in a thread-safe manner.

#### Scenario: Concurrent database writes
- **GIVEN** multiple worker threads are processing files
- **WHEN** a worker needs to write to the database
- **THEN** it SHALL acquire its own `Session` from the shared `neo4j.Driver` instance for the transaction.

### Requirement: Configurable Concurrency
The system SHALL allow the user to configure the level of parallelism.

#### Scenario: Custom worker count
- **GIVEN** the `MAX_WORKERS` environment variable is set to `16`
- **WHEN** the indexing process starts
- **THEN** the executor SHALL be configured with a maximum of 16 workers.
