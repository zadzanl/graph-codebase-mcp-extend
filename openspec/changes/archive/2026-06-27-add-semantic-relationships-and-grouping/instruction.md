# Implementation Guide: Semantic Relationships & Result Grouping

## Overview
Enhance MCP search with code relationships (calls, imports, inheritance) and semantic grouping. Backward compatible.

## Files to Modify
- `src/neo4j_storage/graph_db.py` - Add relationship queries
- `src/mcp/server.py` - Add grouping logic and enhance search_code
- `.env.example` - Document new environment variables

## Implementation Checklist

### Step 1: Add Relationship Query Method
**File**: `src/neo4j_storage/graph_db.py`  
**Location**: After `search_code_by_vector` method (~line 700)

Add `get_node_relationships(node_id, relationship_types, limit)` method that:
- Queries CALLS, CALLED_BY, EXTENDS, EXTENDED_BY, IMPORTS_FROM, IMPORTED_BY
- Returns Dict[str, List[Dict]] mapping relationship types to nodes
- Handles errors gracefully (returns empty dict)
- Uses Neo4j session with proper database parameter

See `implementation-detail.md` for complete code.

### Step 2: Add Grouping Helper Methods
**File**: `src/mcp/server.py`  
**Location**: Add as private methods in `CodebaseKnowledgeGraphMCP` class (after `__init__`)

Add two methods:
1. `_calculate_cosine_similarity(vec1, vec2)` - returns float 0.0-1.0
2. `_group_results_by_similarity(results, threshold, max_groups)` - returns grouped dict

See `implementation-detail.md` for complete code.

### Step 3: Enhance search_code Tool
**File**: `src/mcp/server.py`  
**Location**: Replace existing `search_code` tool in `_register_tools` (~line 79)

Changes:
- Add parameter: `include_relationships: bool = True`
- Add parameter: `group_threshold: float = None`
- After vector search: enrich results with relationships if enabled
- Before return: apply grouping if threshold > 0.0
- Response format: `{"results": [...]}` or `{"groups": [...], "ungrouped": [...]}`

See `implementation-detail.md` for complete code.

### Step 4: Update Environment Configuration
**File**: `.env.example`

Add:
```bash
GROUP_THRESHOLD=0.7
GROUP_MAX_GROUPS=10
```

## Testing Commands

Use venv Python for all tests:

```powershell
# Test relationships
.venv\Scripts\python.exe -m pytest tests/test_mcp_tools.py::test_search_with_relationships -v

# Test grouping
.venv\Scripts\python.exe -m pytest tests/test_mcp_tools.py::test_search_with_grouping -v

# Test backward compatibility
.venv\Scripts\python.exe -m pytest tests/test_mcp_tools.py::test_search_backward_compat -v
```

## Success Criteria
- ✅ `search_code` returns relationships by default
- ✅ Grouping works when `group_threshold` > 0.0
- ✅ Environment variables are respected
- ✅ Backward compatible (existing tests pass)
- ✅ Error handling covers edge cases

## Key Patterns from Codebase
- Neo4j queries use `self.driver.session(database=self.database)`
- Logger is `logging.getLogger(__name__)`
- Environment variables use `os.getenv()` with defaults
- Tool definitions use `@self.mcp.tool()` decorator
- JSON responses use `json.dumps(..., ensure_ascii=False)`