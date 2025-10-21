# Getting Started with Graph Codebase MCP

This comprehensive guide will help you set up, configure, and use the Graph Codebase MCP tool to create and query knowledge graphs from your codebase.

## Table of Contents

1. [Quick Start (5 Minutes)](#quick-start-5-minutes)
2. [Prerequisites](#prerequisites)
3. [Detailed Setup Guide](#detailed-setup-guide)
4. [MCP Configuration](#mcp-configuration)
5. [Example Queries](#example-queries)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Topics](#advanced-topics)

---

## Quick Start (5 Minutes)

Get running quickly with these four steps:

### 1. Start Neo4j
```powershell
docker run -d --name neo4j-codebase -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/bV5PazG8LUGAmre0B95VZSBs6RR3mCoNb0Txig1JNTU neo4j:latest
```

### 2. Activate Python Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Process Your Codebase
```powershell
python src/main.py --codebase-path C:\Path\To\Your\Codebase
```

### 4. View Results
Open http://localhost:7474 in your browser
- Username: `neo4j`
- Password: `bV5PazG8LUGAmre0B95VZSBs6RR3mCoNb0Txig1JNTU`

---

## Prerequisites

1. **Docker** - For running Neo4j database
2. **Python 3.14+** - For running the codebase parser
3. **Python Virtual Environment** - Recommended for dependency isolation

---

## Detailed Setup Guide

## Step 1: Set Up Neo4j Database

### Start Neo4j with Docker

```powershell
# Start Neo4j container with proper authentication
docker run -d --name neo4j-codebase \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/bV5PazG8LUGAmre0B95VZSBs6RR3mCoNb0Txig1JNTU \
  neo4j:latest
```

**Important Notes:**
- Username MUST be `neo4j` (Neo4j requirement)
- Password can be customized (default in this project: `bV5PazG8LUGAmre0B95VZSBs6RR3mCoNb0Txig1JNTU`)
- Port 7474: Neo4j Browser (Web UI)
- Port 7687: Bolt protocol (Application connection)

### Verify Neo4j is Running

```powershell
# Check container status
docker ps

# View logs
docker logs neo4j-codebase --tail 20

# You should see: "INFO  Started."
```

### Access Neo4j Browser

Open your browser and navigate to: http://localhost:7474

- Username: `neo4j`
- Password: `bV5PazG8LUGAmre0B95VZSBs6RR3mCoNb0Txig1JNTU`

---

## Step 2: Configure Environment Variables

The `.env` file should be configured as follows:

```properties
# Neo4j Database Connection Settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j                                    # MUST be 'neo4j'
NEO4J_PASSWORD=bV5PazG8LUGAmre0B95VZSBs6RR3mCoNb0Txig1JNTU

# OpenAI API Settings (optional if using Google Gemini)
OPENAI_API_KEY=your_openai_api_key

# Google Gemini API Settings
EMBEDDING_PROVIDER=google
EMBEDDING_MODEL=text-embedding-004
GEMINI_API_KEY=AIzaSyCnPygreyoGL1mX6XjX9jwL-xUt3V9piYU

# Other Configuration
LOG_LEVEL=INFO

# Parallel Indexing Configuration (Optional)
PARALLEL_INDEXING_ENABLED=true
MAX_WORKERS=4
MIN_FILES_FOR_PARALLEL=50
NEO4J_MAX_CONNECTION_POOL_SIZE=16

# Multi-language Support
ENABLE_JS_TS_PARSING=true

# AST-grep Integration (Advanced)
USE_AST_GREP=false
AST_GREP_LANGUAGES=python,javascript,typescript
AST_GREP_FALLBACK_TO_LEGACY=true
```

---

## Step 3: Install Python Dependencies

### Activate Virtual Environment

```powershell
# If using venv (recommended)
.\venv\Scripts\Activate.ps1

# Or if using .venv
.\.venv\Scripts\Activate.ps1
```

### Install Requirements

```powershell
pip install -r requirements.txt
```

---

## Step 4: Process Your Codebase

### Basic Usage

```powershell
python src/main.py --codebase-path <path-to-your-codebase>
```

### Example: Process the Example Codebase

```powershell
python src/main.py --codebase-path C:\Projects\graph-codebase-mcp-extend\example_codebase
```

### Clear Database Before Processing

```powershell
python src/main.py --codebase-path <path> --clear-db
```

### Start MCP Server After Processing

```powershell
python src/main.py --codebase-path <path> --start-mcp-server
```

---

## Step 5: Query Your Knowledge Graph

### Using Neo4j Browser

Open http://localhost:7474 and run Cypher queries:

#### View All Nodes
```cypher
MATCH (n) RETURN n LIMIT 25
```

#### Find All Functions
```cypher
MATCH (f:Function) RETURN f.name, f.file_path, f.line_no
```

#### Find All Classes
```cypher
MATCH (c:Class) RETURN c.name, c.file_path
```

#### Find Function Calls
```cypher
MATCH (f1:Function)-[r:CALLS]->(f2:Function)
RETURN f1.name, f2.name, r
```

#### Find Import Dependencies
```cypher
MATCH (f1:File)-[r:IMPORTS]->(f2)
RETURN f1.name, f2.name
```

#### Search by Similarity (Vector Search)
```cypher
// Find functions similar to a query
CALL db.index.vector.queryNodes(
  'function_vector_index',
  5,
  [/* embedding vector */]
) YIELD node, score
RETURN node.name, node.code_snippet, score
```

---

## Step 6: Run Tests (Optional)

```powershell
# Run all tests
pytest

# Run specific test
pytest tests/test_main_processing.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src
```

---

## Supported Languages

The tool currently supports:

1. **Python** (.py)
2. **JavaScript** (.js, .jsx)
3. **TypeScript** (.ts, .tsx)
4. **C++** (.cpp, .cc, .cxx, .h, .hpp) - with AST-grep
5. **Java** (.java) - with AST-grep
6. **Rust** (.rs) - with AST-grep
7. **Go** (.go) - with AST-grep

---

## Troubleshooting

### Neo4j Connection Issues

**Error:** `Couldn't connect to localhost:7687`

**Solution:**
1. Ensure Docker is running: `docker ps`
2. Restart Neo4j: `docker restart neo4j-codebase`
3. Check logs: `docker logs neo4j-codebase`

---

**Error:** `The client is unauthorized due to authentication failure`

**Solution:**
1. Verify `.env` has `NEO4J_USER=neo4j` (not custom username)
2. Ensure password matches Docker startup: `NEO4J_AUTH=neo4j/<password>`
3. Restart with fresh container if credentials changed:
   ```powershell
   docker stop neo4j-codebase
   docker rm neo4j-codebase
   # Then start fresh container with correct credentials
   ```

---

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'src'`

**Solution:** This has been fixed. The script now automatically adds the project root to `sys.path`.

If you still encounter this:
1. Run from project root: `python src/main.py ...`
2. Or use module syntax: `python -m src.main ...`

---

### Embedding API Issues

**Error:** API key not working or rate limits

**Solution:**
1. Verify your API key in `.env`
2. Switch providers:
   - For Google Gemini: Set `EMBEDDING_PROVIDER=google`
   - For OpenAI: Set `EMBEDDING_PROVIDER=openai`
3. Check rate limits and quotas for your provider

---

## Docker Management

### Useful Docker Commands

```powershell
# View running containers
docker ps

# View all containers (including stopped)
docker ps -a

# Stop Neo4j
docker stop neo4j-codebase

# Start Neo4j
docker start neo4j-codebase

# Restart Neo4j
docker restart neo4j-codebase

# Remove container (will delete all data)
docker rm neo4j-codebase

# View logs
docker logs neo4j-codebase

# Follow logs in real-time
docker logs -f neo4j-codebase

# Execute commands in container
docker exec -it neo4j-codebase bash
```

### Persistent Data Storage

To persist Neo4j data across container restarts, use volumes:

```powershell
docker run -d --name neo4j-codebase \
  -p 7474:7474 -p 7687:7687 \
  -v neo4j-data:/data \
  -v neo4j-logs:/logs \
  -e NEO4J_AUTH=neo4j/bV5PazG8LUGAmre0B95VZSBs6RR3mCoNb0Txig1JNTU \
  neo4j:latest
```

---

## MCP Configuration

### Overview

The MCP (Model Context Protocol) server allows AI assistants to query your codebase knowledge graph directly from your IDE.

### Step 1: Update Your mcp.json

Add this to your `mcp.json` file (typically located at `%APPDATA%\Code\User\mcp.json`):

```json
{
  "servers": {
    "graph-codebase-mcp": {
      "command": "python",
      "args": [
        "C:\\Projects\\graph-codebase-mcp-extend\\run_mcp_server.py",
        "--transport",
        "stdio"
      ],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "bV5PazG8LUGAmre0B95VZSBs6RR3mCoNb0Txig1JNTU",
        "EMBEDDING_PROVIDER": "google",
        "EMBEDDING_MODEL": "text-embedding-004",
        "GEMINI_API_KEY": "AIzaSyCnPygreyoGL1mX6XjX9jwL-xUt3V9piYU"
      },
      "type": "stdio"
    }
  }
}
```

**Important Notes:**
- Use **absolute paths** for the Python script path
- Update the path to match your actual project location
- Alternatively, omit the `env` section to use your `.env` file

### Step 2: Restart VS Code / Your MCP Client

The MCP server configuration is loaded on startup.

### Step 3: Verify the Setup

Ask your AI assistant: "What classes are in the codebase?"

### Available MCP Tools

Once configured, the following tools will be available:

1. **search_code** - Search using vector similarity or full-text
   - Parameters: `query`, `limit`, `search_type` (vector/text)

2. **execute_cypher_query** - Run custom Cypher queries
   - Parameters: `query`, `parameters`

3. **get_code_by_name** - Get code elements by name
   - Parameters: `name`, `node_type`

4. **find_function_callers** - Find what calls a function
   - Parameters: `function_name`, `limit`

5. **find_function_callees** - Find what a function calls
   - Parameters: `function_name`, `limit`

6. **find_class_inheritance** - Find inheritance relationships
   - Parameters: `class_name`

7. **find_file_dependencies** - Find import relationships
   - Parameters: `file_path`

### Start the MCP Server Manually

```powershell
# Process codebase and start MCP server
python src/main.py --codebase-path <path> --start-mcp-server

# Use SSE transport (HTTP)
python src/main.py --codebase-path <path> --start-mcp-server --mcp-transport sse --mcp-port 8080
```

### MCP Server Endpoints

When using SSE transport on port 8080:
- Health check: `http://localhost:8080/health`
- MCP endpoint: `http://localhost:8080/mcp`

---

## Example Queries

### Current Knowledge Graph Contents

Based on the example codebase, you have:

**Nodes:**
- 6 Classes (Person, Employee, User, AdminUser, EventBus, MathOps)
- 5 Functions (calculateTotal, formatDate, log_execution, make_multiplier, on_task_assigned)
- 14 Methods (various class methods)
- 5 Files (main.py, models.py, events.py, utils.py, sample.js)
- 3 Variables

**Relationships:**
- 5 IMPORTS_DEFINITION relationships
- 4 IMPORTS_FROM relationships

### Natural Language Examples

Ask your AI assistant natural questions:

- "What classes are in this codebase?"
- "Show me all functions in utils.py"
- "Find code related to user authentication"
- "What imports does main.py have?"
- "Show me the Employee class and its methods"
- "Find all functions that deal with calculations"
- "What's the structure of the EventBus class?"
- "Search for decorator functions"

### Example 1: Search for Code by Semantic Similarity

**Query:** "Find code related to user management"

**MCP Tool Call:**
```json
{
  "tool": "search_code",
  "parameters": {
    "query": "user management",
    "limit": 5,
    "search_type": "vector"
  }
}
```

**Expected Results:** User class, AdminUser class, Person class, Employee class

### Example 2: Find a Specific Function

**Query:** "Show me the calculateTotal function"

**MCP Tool Call:**
```json
{
  "tool": "get_code_by_name",
  "parameters": {
    "name": "calculateTotal",
    "node_type": "Function"
  }
}
```

### Example 3: Find All Classes

**MCP Tool Call:**
```json
{
  "tool": "execute_cypher_query",
  "parameters": {
    "query": "MATCH (c:Class) RETURN c.name as name, c.file_path as file, c.line_no as line ORDER BY c.name"
  }
}
```

**Expected Results:**
1. AdminUser (sample.js:21)
2. Employee (models.py:12)
3. EventBus (events.py:3)
4. MathOps (utils.py:14)
5. Person (models.py:3)
6. User (sample.js:10)

### Example 4: Find File Dependencies

**Query:** "What does main.py import?"

**MCP Tool Call:**
```json
{
  "tool": "find_file_dependencies",
  "parameters": {
    "file_path": "C:\\Projects\\graph-codebase-mcp-extend\\example_codebase\\main.py"
  }
}
```

### Example 5: Find Class Inheritance

**Query:** "Show inheritance for the Employee class"

**MCP Tool Call:**
```json
{
  "tool": "find_class_inheritance",
  "parameters": {
    "class_name": "Employee"
  }
}
```

**Expected Results:**
```json
{
  "superclasses": [
    {"name": "Person", "file_path": "models.py"}
  ],
  "subclasses": []
}
```

### Advanced Cypher Patterns

#### Find Code Co-location
```cypher
MATCH (f:File)<-[:BELONGS_TO]-(func:Function)
RETURN f.name, count(func) as function_count
ORDER BY function_count DESC
LIMIT 5
```

#### Find All Definitions in a File
```cypher
MATCH (n)
WHERE n.file_path CONTAINS 'models.py'
RETURN labels(n)[0] as type, n.name as name, n.line_no as line
ORDER BY n.line_no
```

#### Cross-File Analysis
```cypher
MATCH (importer:File)-[:IMPORTS_FROM]->(utils:File {name: 'utils.py'})
RETURN importer.name as file
```

### Testing Methods

#### Method 1: Through VS Code with MCP
1. Configure MCP server in `mcp.json`
2. Restart VS Code
3. Ask natural questions to your AI assistant

#### Method 2: Direct Testing with Python
```python
from src.neo4j_storage.graph_db import Neo4jDatabase
from dotenv import load_dotenv

load_dotenv()
db = Neo4jDatabase()

# Run any query
result = db.execute_cypher("MATCH (c:Class) RETURN c.name ORDER BY c.name")
print(result)

db.close()
```

#### Method 3: Using Neo4j Browser
1. Open http://localhost:7474
2. Login with your credentials
3. Paste Cypher queries directly

---

## Troubleshooting

### Common Docker Commands

```powershell
docker ps                          # Check status
docker logs neo4j-codebase        # View logs
docker stop neo4j-codebase        # Stop
docker start neo4j-codebase       # Start
docker restart neo4j-codebase     # Restart
docker rm neo4j-codebase          # Remove (deletes data)
```

### Processing Options

```powershell
# Clear database before processing
python src/main.py --codebase-path <path> --clear-db

# Start MCP server after processing
python src/main.py --codebase-path <path> --start-mcp-server
```

---

## Performance Optimization

### Parallel Processing

For large codebases (50+ files), parallel processing is automatically enabled:

```properties
PARALLEL_INDEXING_ENABLED=true
MAX_WORKERS=4                      # Adjust based on CPU cores
MIN_FILES_FOR_PARALLEL=50          # Minimum files to trigger parallel mode
NEO4J_MAX_CONNECTION_POOL_SIZE=16  # Should be >= MAX_WORKERS * 2
```

### Recommendations:
- **Small codebases (<50 files):** Set `PARALLEL_INDEXING_ENABLED=false`
- **Medium codebases (50-500 files):** `MAX_WORKERS=4`
- **Large codebases (500+ files):** `MAX_WORKERS=8`
- Always set `NEO4J_MAX_CONNECTION_POOL_SIZE` to at least `MAX_WORKERS * 2`

---

## Advanced Topics

### Testing the Setup

#### Test via Demo Script
```powershell
python demo_queries.py
```
This runs 7 example queries and shows you what's in the graph.

#### Test via Python
```python
from src.neo4j_storage.graph_db import Neo4jDatabase
from dotenv import load_dotenv

load_dotenv()
db = Neo4jDatabase()

# Query all classes
classes = db.execute_cypher("""
    MATCH (c:Class) 
    RETURN c.name as name, c.file_path as file
    ORDER BY c.name
""")

for cls in classes:
    print(f"{cls['name']} - {cls['file']}")

db.close()
```

### What You Can Do with MCP

- ✅ **Search code semantically** - Find code by meaning, not just keywords
- ✅ **Analyze dependencies** - Understand import relationships
- ✅ **Explore class hierarchies** - See inheritance trees
- ✅ **Find function calls** - Trace code execution paths
- ✅ **Run custom queries** - Use Cypher for complex analysis
- ✅ **Visualize code structure** - See relationships in Neo4j Browser

### Process Your Own Codebase

```powershell
# Step 1: Process your codebase
python src/main.py --codebase-path C:\Path\To\Your\Project

# Step 2: Restart your MCP client (VS Code)

# Step 3: Start querying!
```

---

## Next Steps

1. **Explore the Knowledge Graph**
   - Use Neo4j Browser to visualize relationships
   - Run Cypher queries to extract insights

2. **Integrate with Your IDE**
   - Configure MCP server in your `mcp.json`
   - Query code structure and dependencies from your editor

3. **Try Example Queries**
   - Use natural language questions
   - Experiment with custom Cypher queries

4. **Extend the Tool**
   - Add support for more languages
   - Customize node/relationship extraction
   - Build custom analysis tools on top of the graph

---

## Common Issues and Solutions

### MCP Server Won't Start

**Check:**
1. Neo4j is running: `docker ps | Select-String "neo4j-codebase"`
2. Database has data: `python demo_queries.py`
3. Path in mcp.json is absolute and correct
4. Environment variables are set correctly

### No Results from Queries

**Reason:** Database might be empty

**Solution:**
```powershell
# Process the example codebase (or your own)
python src/main.py --codebase-path C:\Projects\graph-codebase-mcp-extend\example_codebase

# Verify data exists
python demo_queries.py
```

### Import Errors

**Reason:** Python can't find modules

**Solution:**
- Use `run_mcp_server.py` (handles paths automatically)
- Ensure absolute paths in mcp.json
- Check virtual environment is activated

### Can't Connect to Neo4j

**Quick Fix:**
```powershell
docker restart neo4j-codebase
Start-Sleep -Seconds 15  # Wait for startup
```

**Authentication Failed:**
- Ensure `.env` has `NEO4J_USER=neo4j` (NOT custom username)
- Password must match Docker command

---

## Root Cause Notes

**Historical Issue:** Authentication failure when connecting to Neo4j.

**Root Cause:** Neo4j requires the admin username to be exactly `neo4j`. Custom usernames like `neo4j_local` are not allowed for the admin user.

**Solution:** Updated `.env` to use `NEO4J_USER=neo4j` and restarted the Docker container with matching credentials.

---

## Resources

- **Neo4j Documentation:** https://neo4j.com/docs/
- **Cypher Query Language:** https://neo4j.com/docs/cypher-manual/current/
- **MCP Protocol:** https://modelcontextprotocol.io/
- **Project Repository:** https://github.com/zadzanl/graph-codebase-mcp-extend

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review logs: `docker logs neo4j-codebase` and Python output
3. Open an issue on GitHub with error details and logs

---

**Happy Code Graphing! 🚀**

Your Graph-Codebase-MCP server is ready to help you understand and navigate your codebase like never before!
