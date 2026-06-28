## Why
Current search results lack code relationship context and intelligent grouping. Engineers need to see how code elements connect (calls, imports, inheritance) and receive organized results to navigate codebases efficiently.

## What Changes
- **Semantic Relationships**: Show immediate code neighbors in search results (callers, callees, imports, inheritance)
- **Result Grouping**: Cluster results by semantic similarity using configurable cosine threshold
- **Environment Config**: `GROUP_THRESHOLD` (default 0.7) and `GROUP_MAX_GROUPS` (default 10)
- **Backward Compatible**: All enhancements optional via parameters, existing behavior preserved

## Impact
- **Affected specs**: `mcp` capability (enhanced search_code tool)
- **Affected code**: 
  - `src/neo4j_storage/graph_db.py` - new `get_node_relationships()` method
  - `src/mcp/server.py` - grouping logic and enhanced `search_code` tool
- **New env vars**: `GROUP_THRESHOLD`, `GROUP_MAX_GROUPS`
- **Performance**: Minimal (<100ms) - uses indexed Neo4j relationships with limits