# Graph-Codebase-MCP

[ [English](README.md) | [繁體中文](docs/README-zh-TW.md) ]

Intelligent code search and analysis through Neo4j knowledge graphs

## Project Overview

Graph-Codebase-MCP is a specialized tool for creating knowledge graphs of codebases, combining Neo4j graph database with Model Context Protocol (MCP) to provide intelligent code search and analysis capabilities. The project utilizes Abstract Syntax Tree (AST) to analyze Python code structures and employs OpenAI Embeddings for semantic encoding, storing code entities and relationships in Neo4j to form a comprehensive knowledge graph.

Through the MCP server interface, AI agents can understand and search code more intelligently, surpassing the limitations of traditional text search and achieving a deeper understanding of code structure and semantics.

### Knowledge Graph Visualization Example

The following diagram shows a knowledge graph of [example codebase](./example_codebase):

![Knowledge Graph Example](docs/images/example_graph.svg)

The graph illustrates the network of relationships between files (pink), classes (blue), functions and methods (yellow), and variables (green), including:
- Import relationships between files (IMPORTS_FROM)
- Specific symbol imports from files (IMPORTS_DEFINITION)
- Class inheritance relationships (EXTENDS)
- Function call relationships (CALLS)
- Definition relationships between classes and their methods/attributes (DEFINES)

This structured representation enables AI to more effectively understand the structure and semantic relationships within code.

## Core Features

- **Multi-Language Code Parsing**: Support for 6+ programming languages using both legacy AST parsers and modern ast-grep adapters
- **Semantic Embeddings**: Generate vector representations for code elements using configurable embedding providers (OpenAI, Google Gemini, DeepInfra)
- **Knowledge Graph Construction**: Store parsed code entities and relationships in Neo4j to form a comprehensive, queryable knowledge graph
- **Cross-File Dependency Analysis**: Track imports, symbols, and dependencies across file boundaries for complete codebase understanding
- **Parallel Indexing**: Dramatically speed up large codebase processing with automatic parallelization and intelligent fallback strategies
- **MCP Query Interface**: Provide an AI-agent-friendly interface following the Model Context Protocol standard
- **Relationship Queries**: Support complex queries including function call chains, inheritance hierarchies, and dependency networks

## Supported Programming Languages

- [x] Python
- [x] JavaScript / TypeScript
- [x] Java
- [x] C++
- [x] Rust
- [x] Go

## System Requirements

- Python 3.10 or higher (3.14 free-threaded recommended for best performance)
- Neo4j graph database (version 5.x recommended)
- Docker (optional, for containerized deployment)

## Parallel Indexing

Graph-Codebase-MCP supports parallel indexing to dramatically speed up processing of large codebases. When available, the system automatically selects the optimal execution strategy based on your Python version and codebase size. The system will automatically fallback to sequential processing for small codebases (< 50 files) or when free-threading isnt available. It also scales based on CPU cores

### How It Works

The system uses a two-pass architecture:
1. **First Pass (Parallel)**: Each worker independently parses files and builds module definitions
2. **Second Pass (Sequential)**: Resolves cross-file imports using the complete module index

### Configuration

Parallel indexing is enabled by default. You can customize behavior via environment variables:

```bash
# Enable/disable parallel indexing (default: true)
PARALLEL_INDEXING_ENABLED=true

# Maximum worker threads/processes (default: min(cpu_count, 8))
MAX_WORKERS=8

# Minimum files required to use parallel mode (default: 50)
MIN_FILES_FOR_PARALLEL=50

# Neo4j connection pool size (default: MAX_WORKERS * 2)
NEO4J_MAX_CONNECTION_POOL_SIZE=16
```

### Troubleshooting

**Connection pool exhausted**
- Increase `NEO4J_MAX_CONNECTION_POOL_SIZE` (recommended: `MAX_WORKERS * 2`)
- Reduce `MAX_WORKERS` if system resources are limited

**Performance not improving**
- Ensure you have Python 3.14 free-threaded for best results
- Check CPU utilization - you may already be I/O bound

## Installation Guide

### 1. Clone the Project

```bash
git clone https://github.com/zadzanl/graph-codebase-mcp-extend.git
cd graph-codebase-mcp-extend
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Install Python 3.14 Free-Threaded (GIL disabled)

To unlock true parallel speedups on multi-core CPUs, you can install Python 3.14 free-threaded (GIL disabled). Standard Python works fine and the app will fall back to safe modes automatically, but free-threaded can deliver 2x+ speedups on large codebases.

- Windows/macOS installers from python.org include an option to install a free-threaded build.
- Verify with either method:
  - `python -VV` shows "free-threading build" in the version string
  - In Python: `import sys; hasattr(sys, "_is_gil_enabled") and sys._is_gil_enabled()` returns `False`

References:
- Python HOWTO: Python support for free threading (3.14)
- What’s New in Python 3.14 – Free-threaded mode improvements

### 3. Configure Environment Variables

Create a `.env` file in the project root (see [Embedding Provider Configuration](#embedding-provider-configuration) for more details):

#### `.env` file example (with OpenAI):
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
OPENAI_API_KEY=your_openai_api_key
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
PARALLEL_INDEXING_ENABLED=true
MAX_WORKERS=4
```

#### `.env` file example (with Google Gemini):
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
EMBEDDING_PROVIDER=google
EMBEDDING_MODEL=text-embedding-004
GEMINI_API_KEY=your_gemini_api_key
PARALLEL_INDEXING_ENABLED=true
MAX_WORKERS=4
```

#### `mcp.json` configuration example:
```json
{
  "mcpServers": {
    "graph-codebase-mcp": {
      "command": "python",
      "args": [
          "src/main.py",
          "--codebase-path",
          "path/to/your/codebase"
        ],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password",
        "EMBEDDING_PROVIDER": "openai",
        "EMBEDDING_MODEL": "text-embedding-3-small",
        "OPENAI_API_KEY": "your_openai_api_key"
      }
    }
  }
}
```

### 4. Launch Neo4j

If using Docker:
```bash
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest
```

Access the Neo4j browser at: http://localhost:7474

## Usage Instructions

### 1. Build the Code Knowledge Graph

Execute the main program to analyze the codebase and build the knowledge graph:

```bash
python src/main.py --codebase-path /path/to/your/codebase
```

### 2. Start the MCP Server

```bash
python src/mcp_server.py
```

## MCP Query Examples

This project supports various code-related queries, such as:

- Find all callers of a specific function: `"find all callers of function:process_data"`
- Find the inheritance structure of a specific class: `"show inheritance hierarchy of class:DataProcessor"`
- Query the dependencies of a file: `"list dependencies of file:main.py"`
- Find code related to a specific module: `"search code related to module:data_processing"`
- Cross-file tracking of symbol imports and usage: `"trace imports and usages of class:Employee"`
- Analyze the dependency network between files: `"analyze dependency network starting from file:main.py"`

## Architecture Overview

```
graph-codebase-mcp/
├── src/
│   ├── ast_parser/           # Multi-language AST parsing module
│   │   ├── parser.py         # Legacy Python AST parser
│   │   ├── multi_parser.py   # Multi-language parser coordinator
│   │   ├── language_detector.py # Automatic language detection
│   │   └── adapters/         # Language-specific ast-grep adapters
│   │       ├── python_adapter.py
│   │       ├── javascript_adapter.py
│   │       ├── java_adapter.py
│   │       ├── cpp_adapter.py
│   │       ├── rust_adapter.py
│   │       └── go_adapter.py
│   ├── embeddings/           # Embedding provider module
│   │   ├── factory.py        # Provider factory (OpenAI, Google Gemini, DeepInfra)
│   │   ├── openai_compatible.py # OpenAI-compatible API client
│   │   ├── base.py           # Base embedding provider interface
│   │   └── embedder.py       # Code embedding processor
│   ├── neo4j_storage/        # Neo4j database operations
│   │   └── graph_db.py       # Neo4j graph database interface
│   ├── parallel/             # Parallel processing module
│   │   └── pool_manager.py   # Thread/process pool manager
│   ├── utils/                # Utility functions
│   │   └── runtime_detection.py # Python runtime detection (3.14 free-threading)
│   ├── mcp/                  # MCP Server implementation
│   │   └── server.py         # MCP server entry point
│   ├── main.py               # Main program entry point
│   └── mcp_server.py         # MCP server startup script
├── tests/                    # Comprehensive test suite
├── docs/                     # Documentation and diagrams
│   └── images/               # Visual resources
├── .env                      # Environment configuration
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## Technology Stack

- **Languages**: Python 3.10+ (Python 3.14 free-threaded recommended for best performance)
- **Code Analysis**: Python AST module, ast-grep, Tree-sitter
- **Multi-Language Support**: Dedicated adapters for Python, JavaScript/TypeScript, Java, C++, Rust, Go
- **Vector Embeddings**: OpenAI, Google Gemini, or DeepInfra APIs (OpenAI-compatible)
- **Graph Database**: Neo4j 5.x with connection pooling
- **Parallel Processing**: ThreadPoolExecutor (Python 3.14) or ProcessPoolExecutor with automatic selection
- **Interface Protocol**: Model Context Protocol (MCP) Python SDK
- **Web Framework**: Starlette/Uvicorn for MCP server hosting

## License

MIT License

## Useful References

- [Neo4j GraphRAG Python Package](https://neo4j.com/blog/news/graphrag-python-package/)
- [Model Context Protocol](https://github.com/modelcontextprotocol/specification)
- [Neo4j Python Driver Documentation](https://neo4j.com/docs/api/python-driver/)
- [Python AST Module Documentation](https://docs.python.org/3/library/ast.html)

## Embedding Provider Configuration

The system supports multiple embedding providers. Configure via environment variables:

### OpenAI (Default)
```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=your_openai_api_key
```

### Google Gemini
```env
EMBEDDING_PROVIDER=google
EMBEDDING_MODEL=text-embedding-004
GEMINI_API_KEY=your_gemini_api_key
```

### DeepInfra
```env
EMBEDDING_PROVIDER=deepinfra
EMBEDDING_MODEL=your_model_name
DEEPINFRA_API_KEY=your_deepinfra_api_key
```

### Generic OpenAI-Compatible Provider
```env
EMBEDDING_PROVIDER=generic
EMBEDDING_MODEL=your_model_name
EMBEDDING_API_KEY=your_api_key
EMBEDDING_API_BASE_URL=https://your-provider-endpoint/v1
```

### Supported Models and Dimensions
| Provider | Model | Dimensions | Notes |
|----------|-------|-----------|-------|
| OpenAI | text-embedding-3-small | 1536 | Recommended default |
| OpenAI | text-embedding-3-large | 3072 | Higher quality |
| Google | text-embedding-004 | 768 | Legacy, being deprecated |
| Google | gemini-embedding-001 | 3072 | Latest, recommended |

---
