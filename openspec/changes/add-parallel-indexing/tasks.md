## 1. Parallel Processing Core
- [ ] 1.1. Implement a `ProcessingPoolManager` in `src/main.py` that selects between `ThreadPoolExecutor` and `ProcessPoolExecutor` based on the Python runtime.
- [ ] 1.2. Refactor the main indexing loop to submit file processing tasks to the executor pool.
- [ ] 1.3. Add environment variables to configure the number of workers and the Neo4j connection pool size.

## 2. Thread-Safe Database Operations
- [ ] 2.1. Ensure a single, shared `neo4j.Driver` instance is created at startup.
- [ ] 2.2. Update the worker function to acquire a new `Session` from the driver for each task.
- [ ] 2.3. Set the `max_connection_pool_size` for the Neo4j driver to be at least the number of workers.

## 3. Validation
- [ ] 3.1. Benchmark the new parallel indexing process on a large codebase to confirm performance improvements.
- [ ] 3.2. Add logging to monitor the concurrency strategy (thread vs. process) and worker activity.
