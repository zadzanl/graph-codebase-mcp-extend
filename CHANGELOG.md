# Changelog

## [2025-10-14] - Parallel Indexing Support

### [FEAT]
- **Parallel Indexing**: Implemented parallel codebase indexing with automatic executor selection
  - ThreadPoolExecutor support for Python 3.14 free-threaded (true parallelism without GIL)
  - ProcessPoolExecutor fallback for standard Python (parallelism via multiprocessing)
  - Adaptive strategy: Automatic sequential mode for small codebases (< 50 files)
  - 2x+ speedup on large codebases (1000+ files) with Python 3.14t
  - 1.5x+ speedup on standard Python with ProcessPoolExecutor

- **Runtime Detection**: Comprehensive Python runtime analysis
  - Automatic detection of Python 3.14 free-threading support
  - GIL status monitoring and re-enablement detection
  - Optimal worker count calculation based on CPU cores
  - Detailed logging of runtime environment and executor selection

- **Thread-Safe Database Operations**: Enhanced Neo4j driver management
  - Shared thread-safe Driver instance across workers
  - Per-worker Session instances for isolation
  - Configurable connection pool sizing (default: MAX_WORKERS * 2)
  - Connection pool monitoring and warnings

- **Configuration**: New environment variables for fine-tuning
  - `PARALLEL_INDEXING_ENABLED`: Enable/disable parallel mode (default: true)
  - `MAX_WORKERS`: Maximum worker threads/processes (default: min(cpu_count, 8))
  - `MIN_FILES_FOR_PARALLEL`: Threshold for parallel mode (default: 50)
  - `NEO4J_MAX_CONNECTION_POOL_SIZE`: Connection pool size (default: MAX_WORKERS * 2)

- **Two-Pass Architecture**: Intelligent parallel processing pipeline
  - First pass: Parallel file parsing and module definition building
  - Second pass: Sequential import resolution using complete module index
  - Per-file error handling without worker crashes
  - Progress tracking and comprehensive logging

### [BUILD]
- Updated NumPy to >= 2.1.0 for Python 3.14 free-threading compatibility
- Added CI/CD testing for Python 3.10-3.14 on ubuntu/windows/macos
- Created .env.example with parallel indexing configuration

### [TESTS]
- Added 42 comprehensive unit tests (runtime detection, pool manager, integration)
- Added 10 integration tests for parallel processing workflows
- All 52 tests passing with full coverage of parallel features
- Added performance benchmarking framework

### [DOCS]
- Documented Python 3.14 free-threaded installation guide
- Added parallel indexing configuration and troubleshooting section
- Updated README with performance expectations and best practices
- Created detailed implementation summary document

## [2025-05-01] - Documentation and Visualization Updates

### [DOCS]
- Added knowledge graph visualization example to README.md
- Updated documentation to reflect cross-file dependency analysis functionality
- Extended MCP query examples with cross-file analysis cases
- Improved project structure documentation

## [2025-05-01] - Fixed Relationship Duplication Issues

### [FIX]
- Resolved duplicate IMPORTS_FROM relationship creation issues
- Implemented relationship uniqueness verification mechanism
- Optimized module import processing logic with source file grouping
- Added intelligent symbol import grouping tracking

## [2025-05-01] - Fixed File Node Duplication Issues

### [FIX]
- Fixed duplicate creation of module and file nodes
- Implemented direct association between module names and file nodes
- Optimized import dependency tracking mechanism
- Improved cross-file symbol reference handling

## [2025-05-01] - Enhanced Cross-File Dependency Relationships

### [FEAT]
- Implemented inter-module import relationship tracking and creation
- Enhanced AST parser to support cross-file symbol dependency analysis
- Added support for tracking relationships between imported symbols across files
- Implemented cross-file function call and class inheritance relationship tracking

## [2025-04-30] - Initial Version

### [FEAT]
- Implemented AST parser with Python code structure analysis support
- Integrated OpenAI Embeddings for code semantic encoding
- Established Neo4j graph database model for code knowledge graph
- Developed MCP Server interface for code querying and analysis

### [DOCS]
- Created detailed README.md with project overview, installation guide, and usage instructions
- Established TODO.md to track development progress and future plans

### [BUILD]
- Created basic project structure and directory organization
- Set up virtual environment and dependency management
- Configured Neo4j and OpenAI API integration
