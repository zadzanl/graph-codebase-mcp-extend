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

- **Code Parsing**: Utilize Abstract Syntax Tree (AST) to analyze Python code structures, extracting variables, functions, classes, and their relationships
- **Semantic Embedding**: Generate vector representations for code elements using OpenAI Embeddings to capture semantic characteristics
- **Knowledge Graph Construction**: Store parsed code elements and relationships in Neo4j graph database to form a complete knowledge graph
- **Knowledge Graph Visualization**: Intuitively display code structures and relationships through Neo4j's visualization capabilities
- **MCP Query Interface**: Provide an AI-agent-friendly query interface following the Model Context Protocol standard
- **Relationship Queries**: Support complex code relationship queries, such as function call chains and dependency relationships
- **Cross-File Analysis**: Accurately track dependencies between files, including module imports and symbol references

## Supported Programming Languages

- [x] Python
- [ ] Java
- [ ] C++
- [ ] JavaScript

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
git clone https://github.com/eric050828/graph-codebase-mcp.git
cd graph-codebase-mcp
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

Create a `.env` file or use `mcp.json` to specify environment parameters:

#### `.env` file example:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
OPENAI_API_KEY=your_openai_api_key
# Parallel indexing configuration (optional; sensible defaults are used if omitted)
PARALLEL_INDEXING_ENABLED=true
MAX_WORKERS=8
MIN_FILES_FOR_PARALLEL=50
NEO4J_MAX_CONNECTION_POOL_SIZE=16
```

#### `mcp.json` file example:
```json
{
  "mcpServers": {
    "graph-codebase-mcp": {
      "command": "python",
      "args": [
          "src/mcp_server.py",
          "--codebase-path",
          "path/to/your/codebase"
        ],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password",
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
│   ├── ast_parser/           # Code AST parsing module
│   │   └── parser.py         # AST parser implementation with cross-file dependency analysis
│   ├── embeddings/           # OpenAI Embeddings processing module
│   ├── neo4j_storage/        # Neo4j database operations module
│   ├── mcp/                  # MCP Server implementation
│   ├── main.py               # Main program entry point
│   └── mcp_server.py         # MCP Server startup entry point
├── examples/                 # Usage examples
├── tests/                    # Test cases
├── docs/                     # Documentation and diagrams
│   └── images/               # Image resources
├── .env.example              # Environment variable example
├── requirements.txt          # Dependency package list
└── README.md                 # Documentation
```

## Technology Stack

- **Programming Language**: Python 3.10+ (Python 3.14 free-threaded recommended)
- **Code Analysis**: Python AST module
- **Vector Embedding**: OpenAI Embeddings
- **Graph Database**: Neo4j
- **Interface Protocol**: Model Context Protocol (MCP)
- **SDK Support**: MCP Python SDK, Neo4j Python SDK

## License

MIT License

## References

- [Neo4j GraphRAG Python Package](https://neo4j.com/blog/news/graphrag-python-package/)
- [Model Context Protocol](https://github.com/modelcontextprotocol/specification)
- [Neo4j Python Driver Documentation](https://neo4j.com/docs/api/python-driver/)
- [Python AST Module Documentation](https://docs.python.org/3/library/ast.html)

## Embedding Provider Configuration

You can configure the embedding provider by setting the following environment variables:

- `EMBEDDING_PROVIDER`: The provider to use. Supported values are `openai` (default), `google`, `deepinfra`, or `generic`.
- `EMBEDDING_MODEL`: The name of the embedding model to use (e.g., `text-embedding-3-small`).
- `OPENAI_API_KEY`: Your OpenAI API key.
- `GEMINI_API_KEY`: Your Google Gemini API key.
- `DEEPINFRA_API_KEY`: Your DeepInfra API key.
- `EMBEDDING_API_KEY`: Your API key for a generic provider.
- `EMBEDDING_API_BASE_URL`: The base URL for a generic provider.

---

