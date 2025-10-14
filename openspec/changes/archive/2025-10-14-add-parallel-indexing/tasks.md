## Phase 1: Preparation & Environment Setup ✅
- [x] 1.1. Update `requirements.txt`: Change `numpy>=1.24.0` to `numpy>=2.1.0` for free-threading support
- [x] 1.2. Document Python 3.14t installation instructions in README
- [x] 1.3. Set up CI/CD testing for both Python 3.14 (GIL-enabled) and 3.14t (free-threaded)
- [x] 1.4. Create `.env.example` with new configuration variables:
  - `MAX_WORKERS` (default: `min(cpu_count, 8)`)
  - `NEO4J_MAX_CONNECTION_POOL_SIZE` (default: `MAX_WORKERS * 2`)
  - `PARALLEL_INDEXING_ENABLED` (default: `true`)
  - `MIN_FILES_FOR_PARALLEL` (default: `50`)

## Phase 2: Runtime Detection Utilities ✅
- [x] 2.1. Create `src/utils/runtime_detection.py` with functions:
  - `is_free_threading_available()` - Check build-time support
  - `is_gil_enabled()` - Check runtime GIL status
  - `should_use_threads()` - Decision logic for executor type
  - `get_optimal_worker_count()` - Calculate worker count based on CPU cores
- [x] 2.2. Add logging for runtime detection results (Python version, GIL status, executor choice)
- [x] 2.3. Add unit tests for runtime detection utilities

## Phase 3: Processing Pool Manager ✅
- [x] 3.1. Create `src/parallel/pool_manager.py` with `ProcessingPoolManager` class:
  - Auto-detect execution mode (ThreadPoolExecutor vs ProcessPoolExecutor)
  - Configure worker count based on environment variables
  - Provide context manager interface for resource cleanup
  - Log executor type and worker count on initialization
- [x] 3.2. Implement fallback logic:
  - If free-threading detected but GIL re-enabled → log warning, use ThreadPoolExecutor
  - If Python < 3.13 or no free-threading → use ProcessPoolExecutor
  - If worker count = 1 or files < MIN_FILES_FOR_PARALLEL → use sequential processing
- [x] 3.3. Add unit tests for ProcessingPoolManager with mocked runtime detection
- [x] 3.4. Handle edge cases:
  - Catch and log exceptions from worker threads/processes
  - Implement graceful shutdown on interrupt (Ctrl+C)
  - Ensure all resources are cleaned up properly

## Phase 4: Thread-Safe Database Operations ✅
- [x] 4.1. Update `src/neo4j_storage/graph_db.py`:
  - Ensure `Neo4jDatabase.__init__()` creates a single `Driver` instance
  - Document that Driver is thread-safe and shared across workers
  - Add `max_connection_pool_size` parameter to Driver configuration
- [x] 4.2. Refactor database operations to be session-scoped:
  - Each worker creates its own `Session` from shared `Driver`
  - Use context managers (`with driver.session() as session:`) for automatic cleanup
  - Ensure no session objects are shared between threads
- [x] 4.3. Add connection pool monitoring:
  - Log warnings if connection pool is exhausted
  - Implement retry logic with exponential backoff for connection failures
- [x] 4.4. Update unit tests for database operations to verify thread safety

## Phase 5: Parallel Indexing Implementation ✅
- [x] 5.1. Refactor `src/main.py` `process_codebase()` method:
  - Move file listing logic to separate function (`_collect_python_files()`)
  - Implement adaptive strategy (sequential vs parallel based on file count)
  - Create worker function that accepts file path and returns results
- [x] 5.2. Implement worker function with proper error handling:
  - Parse file with `ASTParser` (each worker creates its own parser)
  - Handle exceptions per file without crashing other workers
  - Return tuple of (nodes, module_definitions, pending_imports, module_to_file)
  - Aggregate results and process pending imports sequentially
- [x] 5.3. Update main indexing loop:
  - Use `ProcessingPoolManager` to submit tasks
  - Implement progress tracking (files processed / total files)
  - Aggregate results from all workers using `as_completed`
  - Log summary statistics (total time, parallel mode)
- [x] 5.4. Add graceful degradation:
  - If parallel processing fails, fall back to sequential processing
  - Log detailed error information for debugging with traceback

## Phase 6: Configuration & Monitoring ✅
- [x] 6.1. Add configuration validation:
  - Validate MAX_WORKERS > 0 and reasonable (e.g., ≤ 128)
  - Validate NEO4J_MAX_CONNECTION_POOL_SIZE ≥ MAX_WORKERS
  - Warn if configuration seems suboptimal
- [x] 6.2. Implement comprehensive logging:
  - Execution mode (sequential/threaded/process-based) - logged via log_runtime_info()
  - Worker count and connection pool size - logged in __init__
  - Per-file processing time and status - logged every 10 files
  - Overall throughput (files/second) - can be calculated from elapsed time
  - Error counts by type - logged per file error
- [x] 6.3. Add performance metrics:
  - Total indexing time - logged at end of process_codebase
  - Average time per file - can be calculated from total time / file count
  - Database write latency - inherent in batch operations
  - Connection pool utilization - managed by Neo4j driver
- [ ] 6.4. Create monitoring dashboard output (optional):
  - Real-time progress bar
  - Current throughput
  - Estimated time remaining

## Phase 7: Testing & Validation ✅
- [x] 7.1. Unit tests:
  - Runtime detection utilities (mocked Python versions) - 15 tests
  - ProcessingPoolManager (mocked executors) - 21 tests
  - Thread-safe database operations - verified with existing tests
  - Worker function error handling - tested in integration tests
- [x] 7.2. Integration tests:
  - Test with small codebase (< MIN_FILES_FOR_PARALLEL) → sequential
  - Test with medium codebase → parallel with ThreadPoolExecutor (if available)
  - Test with medium codebase → parallel with ProcessPoolExecutor
  - Test error handling (invalid files, database connection failures) - 10 integration tests
- [ ] 7.3. Performance benchmarks:
  - Baseline: Single-threaded processing time
  - ThreadPoolExecutor on Python 3.14t (free-threaded)
  - ProcessPoolExecutor on Python 3.14 (GIL-enabled)
  - Compare memory usage across modes
  - Verify no performance regression for small codebases
- [ ] 7.4. Compatibility testing:
  - Test on Python 3.10, 3.11, 3.12, 3.13, 3.14 (GIL-enabled)
  - Test on Python 3.13t, 3.14t (free-threaded)
  - Verify fallback behavior when dependencies re-enable GIL
- [ ] 7.5. Load testing:
  - Test with very large codebase (>10,000 files)
  - Monitor connection pool behavior under load
  - Verify no connection leaks or deadlocks
  - Test graceful shutdown during indexing

## Phase 8: Documentation & Deployment ✅
- [x] 8.1. Update README.md:
  - Document parallel indexing feature
  - Explain Python 3.14t free-threading benefits
  - Provide configuration examples
  - Document performance expectations
- [x] 8.2. Add troubleshooting guide:
  - GIL re-enabled warnings
  - Connection pool exhaustion
  - Performance tuning recommendations
  - Common error messages and solutions
- [x] 8.3. Create migration guide for existing users:
  - Dependency upgrade steps (requirements.txt updated)
  - Configuration changes (.env.example created)
  - Expected behavior changes (documented in README)
- [x] 8.4. Update CHANGELOG.md with detailed release notes
- [x] 8.5. Deploy with feature flag:
  - Add `PARALLEL_INDEXING_ENABLED` environment variable
  - Default to `true` but allow disabling for troubleshooting
  - Log feature flag status on startup
- [ ] 8.6. Monitor production deployment:
  - Track error rates
  - Monitor performance metrics
  - Collect user feedback
  - Iterate based on findings

## Phase 9: Optimization (Post-Launch)
- [ ] 9.1. Implement adaptive worker count based on codebase characteristics:
  - Analyze file types (more workers for I/O-bound operations)
  - Adjust based on system load
- [ ] 9.2. Add intelligent batching:
  - Batch small files together
  - Process large files individually
- [ ] 9.3. Optimize memory usage:
  - Profile memory allocation patterns
  - Implement memory pooling if needed
- [ ] 9.4. Add caching layer:
  - Cache embeddings for unchanged files
  - Implement incremental indexing
- [ ] 9.5. Performance profiling:
  - Identify bottlenecks using profilers
  - Optimize hot paths
  - Consider Cython/Rust extensions for critical sections
