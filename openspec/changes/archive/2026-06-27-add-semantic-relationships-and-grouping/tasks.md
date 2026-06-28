## 1. Neo4j Database Enhancement
- [x] 1.1 Add `get_node_relationships()` method to `Neo4jDatabase` class in `src/neo4j_storage/graph_db.py` (after line 700)
- [x] 1.2 Implement Cypher queries for each relationship type (CALLS, CALLED_BY, EXTENDS, EXTENDED_BY, IMPORTS_FROM, IMPORTED_BY)
- [x] 1.3 Add error handling for missing nodes and connection failures
- [x] 1.4 Add limit parameter to prevent unbounded queries (default 5)

## 2. MCP Server Grouping Logic
- [x] 2.1 Add `_calculate_cosine_similarity()` helper method to `CodebaseKnowledgeGraphMCP` class in `src/mcp/server.py` (after `__init__`)
- [x] 2.2 Add `_group_results_by_similarity()` method with threshold-based clustering logic
- [x] 2.3 Read `GROUP_THRESHOLD` and `GROUP_MAX_GROUPS` from environment variables with defaults (0.7, 10)
- [x] 2.4 Handle edge cases: missing embeddings, invalid thresholds, empty results

## 3. Enhanced search_code Tool
- [x] 3.1 Modify `search_code` tool in `src/mcp/server.py` (~line 79) to add `include_relationships` parameter (bool, default True)
- [x] 3.2 Add `group_threshold` parameter (float, optional, uses env var if None)
- [x] 3.3 After vector search: call `get_node_relationships()` for each result if `include_relationships=True`
- [x] 3.4 Add relationships to each result node under `relationships` key
- [x] 3.5 If `group_threshold > 0.0`: apply `_group_results_by_similarity()` before return
- [x] 3.6 Update response format: keep `{"results": [...]}` for ungrouped, add `{"groups": [...], "ungrouped": [...]}` for grouped

## 4. Environment Configuration
- [x] 4.1 Add `GROUP_THRESHOLD=0.7` to `.env.example`
- [x] 4.2 Add `GROUP_MAX_GROUPS=10` to `.env.example`
- [x] 4.3 Update README.md with new environment variable documentation

## 5. Testing
- [x] 5.1 Create `tests/test_semantic_relationships.py` with relationship query tests
- [x] 5.2 Add test for `_calculate_cosine_similarity()` with known vectors
- [x] 5.3 Add test for `_group_results_by_similarity()` with mock data
- [x] 5.4 Test `search_code` with `include_relationships=True` and verify relationship data
- [x] 5.5 Test `search_code` with various `group_threshold` values (0.0, 0.5, 0.9, 1.0)
- [x] 5.6 Test backward compatibility: existing tests in `tests/test_mcp_tools.py` must still pass
- [x] 5.7 Test error handling: invalid thresholds, missing node IDs, connection failures

## 6. Validation & Approval
- [x] 6.1 Run `openspec validate add-semantic-relationships-and-grouping --strict`
- [x] 6.2 Fix any validation errors
- [x] 6.3 Run full test suite: `python -m pytest tests -v`
- [x] 6.4 Prepare change for final user approval before merging