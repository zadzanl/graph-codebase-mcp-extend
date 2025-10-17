## MODIFIED Requirements

### Requirement: High-Concurrency Indexing
The system SHALL process files in parallel to reduce indexing time using an adaptive strategy that selects the optimal execution mode based on the Python runtime and codebase characteristics.

#### Scenario: Free-threaded Python with GIL disabled
- **GIVEN** the application is running on a free-threaded Python 3.14+ interpreter
- **AND** `sys._is_gil_enabled()` returns `False`
- **AND** the codebase contains ≥50 files
- **WHEN** indexing a codebase
- **THEN** the system SHALL use a `ThreadPoolExecutor` to process files concurrently
- **AND** log "Using ThreadPoolExecutor (free-threaded mode) with N workers"

#### Scenario: Free-threaded Python with GIL re-enabled
- **GIVEN** the application is running on a free-threaded Python 3.14+ interpreter
- **AND** an incompatible extension module has re-enabled the GIL at runtime
- **AND** `sys._is_gil_enabled()` returns `True`
- **WHEN** indexing a codebase
- **THEN** the system SHALL log a warning about GIL re-enablement
- **AND** continue using `ThreadPoolExecutor` (still benefits from concurrency despite GIL)

#### Scenario: GIL-bound Python
- **GIVEN** the application is running on a standard (GIL-bound) Python interpreter
- **AND** the codebase contains ≥50 files
- **WHEN** indexing a codebase
- **THEN** the system SHALL use a `ProcessPoolExecutor` to process files in parallel
- **AND** log "Using ProcessPoolExecutor (GIL-enabled mode) with N workers"

#### Scenario: Small codebase optimization
- **GIVEN** the codebase contains <50 files (or user-configured threshold)
- **WHEN** indexing the codebase
- **THEN** the system SHALL use sequential processing (no parallelism)
- **AND** log "Using sequential processing (N files < MIN_FILES_FOR_PARALLEL)"
- **AND** avoid the parallel processing overhead

#### Scenario: Fallback on executor failure
- **GIVEN** the parallel executor initialization or execution fails
- **WHEN** an exception is raised during parallel processing
- **THEN** the system SHALL log the error with full traceback
- **AND** automatically fall back to sequential processing
- **AND** continue indexing without failing

## ADDED Requirements

### Requirement: Runtime Detection
The system SHALL detect the Python runtime capabilities and GIL status to select the optimal execution strategy.

#### Scenario: Detecting free-threaded Python build
- **GIVEN** Python 3.13+ with free-threading support
- **WHEN** the system initializes
- **THEN** it SHALL check `sysconfig.get_config_var("Py_GIL_DISABLED") == 1`
- **AND** log the detected Python build type (free-threaded or GIL-enabled)

#### Scenario: Detecting runtime GIL status
- **GIVEN** a free-threaded Python build
- **WHEN** checking GIL status during initialization
- **THEN** it SHALL call `sys._is_gil_enabled()` if available
- **AND** log whether the GIL is currently enabled or disabled
- **AND** fall back to assuming GIL is enabled if `sys._is_gil_enabled()` is not available

#### Scenario: Monitoring GIL re-enablement
- **GIVEN** the system started with GIL disabled
- **WHEN** processing completes
- **THEN** it SHALL check if GIL status has changed
- **AND** log a warning if the GIL was re-enabled during processing
- **AND** report which extension may have caused the re-enablement (if detectable)

### Requirement: Thread-Safe Database Operations
The system SHALL ensure all database operations are performed in a thread-safe manner by using proper Neo4j driver patterns.

#### Scenario: Concurrent database writes
- **GIVEN** multiple worker threads are processing files
- **WHEN** a worker needs to write to the database
- **THEN** it SHALL acquire its own `Session` from the shared `neo4j.Driver` instance
- **AND** use a context manager to ensure proper session cleanup
- **AND** the `Session` SHALL NOT be shared with any other thread

#### Scenario: Connection pool sized for concurrency
- **GIVEN** the system is configured with N workers
- **WHEN** the Neo4j driver is initialized
- **THEN** the connection pool size SHALL be ≥ N (recommended: N × 2)
- **AND** the system SHALL validate this configuration at startup
- **AND** log a warning if pool size < worker count

#### Scenario: Connection pool exhaustion handling
- **GIVEN** all connections in the pool are in use
- **WHEN** a worker attempts to acquire a connection
- **THEN** it SHALL wait up to 30 seconds for a connection to become available
- **AND** if timeout occurs, it SHALL retry up to 3 times with exponential backoff
- **AND** if all retries fail, it SHALL log an error and skip the file
- **AND** not crash other workers

#### Scenario: Graceful session cleanup on error
- **GIVEN** a worker encounters an error while processing a file
- **WHEN** the exception is raised
- **THEN** the context manager SHALL ensure the session is properly closed
- **AND** the connection SHALL be returned to the pool
- **AND** the error SHALL be logged without crashing the worker

### Requirement: Configurable Concurrency
The system SHALL allow the user to configure the level of parallelism through environment variables with sensible defaults.

#### Scenario: Custom worker count
- **GIVEN** the `MAX_WORKERS` environment variable is set to `16`
- **WHEN** the indexing process starts
- **THEN** the executor SHALL be configured with a maximum of 16 workers
- **AND** log "Configured MAX_WORKERS=16"

#### Scenario: Default worker count
- **GIVEN** the `MAX_WORKERS` environment variable is NOT set
- **WHEN** the indexing process starts
- **THEN** the system SHALL use `min(os.cpu_count(), 8)` as the worker count
- **AND** log "Using default worker count: N (based on CPU cores)"

#### Scenario: Custom minimum files threshold
- **GIVEN** the `MIN_FILES_FOR_PARALLEL` environment variable is set to `100`
- **WHEN** indexing a codebase with 75 files
- **THEN** the system SHALL use sequential processing
- **AND** log "75 files < MIN_FILES_FOR_PARALLEL (100), using sequential processing"

#### Scenario: Disabling parallel processing
- **GIVEN** the `PARALLEL_INDEXING_ENABLED` environment variable is set to `false`
- **WHEN** indexing any codebase
- **THEN** the system SHALL always use sequential processing
- **AND** log "Parallel indexing disabled via configuration"

#### Scenario: Configuration validation
- **GIVEN** invalid configuration values (e.g., `MAX_WORKERS=0` or `MAX_WORKERS=abc`)
- **WHEN** the system initializes
- **THEN** it SHALL raise a `ValueError` with a clear error message
- **AND** suggest the correct configuration format

### Requirement: Comprehensive Logging and Monitoring
The system SHALL provide detailed logging for parallel processing operations to facilitate debugging and performance analysis.

#### Scenario: Execution mode logging
- **GIVEN** parallel processing is initialized
- **WHEN** the executor type is selected
- **THEN** the system SHALL log:
  - Python version and build type (GIL-enabled or free-threaded)
  - GIL status (enabled or disabled)
  - Executor type (ThreadPoolExecutor, ProcessPoolExecutor, or sequential)
  - Worker count
  - Connection pool size
  - File count and processing threshold

#### Scenario: Per-file progress tracking
- **GIVEN** parallel processing is active
- **WHEN** each file is processed
- **THEN** the system SHALL log:
  - File path
  - Worker ID (thread/process ID)
  - Processing time
  - Success or failure status
  - Error message (if failed)

#### Scenario: Performance metrics reporting
- **GIVEN** indexing completes
- **WHEN** all files have been processed
- **THEN** the system SHALL log summary metrics:
  - Total files processed
  - Successful file count
  - Failed file count
  - Total processing time
  - Average time per file
  - Throughput (files per second)
  - Execution mode used

### Requirement: Error Handling and Resilience
The system SHALL handle errors gracefully without causing cascading failures or data loss.

#### Scenario: Individual file processing failure
- **GIVEN** a worker encounters an error processing a specific file
- **WHEN** the exception occurs
- **THEN** the worker SHALL log the error with full traceback
- **AND** continue processing other files
- **AND** the other workers SHALL NOT be affected
- **AND** the failed file SHALL be included in the failure count

#### Scenario: Worker crash resilience
- **GIVEN** a worker thread/process crashes unexpectedly
- **WHEN** the crash occurs
- **THEN** the executor SHALL detect the failure
- **AND** the remaining workers SHALL continue processing
- **AND** the system SHALL log the worker crash
- **AND** optionally spawn a replacement worker (depending on executor)

#### Scenario: Database connection failure
- **GIVEN** the Neo4j database becomes unavailable during processing
- **WHEN** a worker attempts to write to the database
- **THEN** it SHALL retry the operation up to 3 times with exponential backoff
- **AND** if all retries fail, log a critical error
- **AND** optionally pause processing and alert the user

#### Scenario: Keyboard interrupt (Ctrl+C)
- **GIVEN** the user presses Ctrl+C during indexing
- **WHEN** the interrupt signal is received
- **THEN** the system SHALL log "Indexing interrupted by user"
- **AND** gracefully shut down all workers
- **AND** close all database connections
- **AND** report partially completed progress
- **AND** exit with a non-zero status code

### Requirement: Dependency Compatibility
The system SHALL verify that all dependencies support the selected execution mode and handle incompatibilities gracefully.

#### Scenario: NumPy version check for free-threading
- **GIVEN** the system is running on free-threaded Python
- **WHEN** importing NumPy
- **THEN** the system SHALL check if NumPy version ≥ 2.1.0
- **AND** if version < 2.1.0, log a warning about potential compatibility issues
- **AND** recommend upgrading to NumPy ≥ 2.1.0 for optimal performance

#### Scenario: GIL re-enablement by dependency
- **GIVEN** the system starts with GIL disabled
- **AND** an imported module re-enables the GIL
- **WHEN** the GIL status is checked after imports
- **THEN** the system SHALL detect the change
- **AND** log a warning: "GIL was re-enabled by an imported extension module"
- **AND** continue execution (ThreadPoolExecutor still provides concurrency)
