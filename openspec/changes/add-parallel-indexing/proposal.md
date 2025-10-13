## Why
The current single-threaded indexing process is a major bottleneck, especially for large codebases. This leads to long wait times and a poor user experience. A parallel processing model is required to significantly reduce indexing time and improve performance.

## What Changes
- Re-architect the file processing pipeline to use a `concurrent.futures` executor.
- Use a `ThreadPoolExecutor` on free-threaded Python 3.14+ and fall back to a `ProcessPoolExecutor` on older versions.
- Implement a thread-safe pattern for database operations by ensuring each worker thread uses its own Neo4j `Session`.
- Make the number of workers and the Neo4j connection pool size configurable.

## Impact
- **Affected specs**: `main`
- **Affected code**: `src/main.py`, `src/neo4j_storage/graph_db.py`
