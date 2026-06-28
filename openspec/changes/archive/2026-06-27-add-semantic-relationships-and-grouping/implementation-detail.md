# Implementation Reference: Semantic Relationships & Grouping

Quick implementation guide for AI agents. See `instruction.md` for detailed context.

## Environment Variables

Add to `.env.example` and your `.env` file:
```bash
# Semantic grouping configuration
GROUP_THRESHOLD=0.7          # Similarity threshold (0.0-1.0, default 0.7)
GROUP_MAX_GROUPS=10          # Max groups to create (default 10)
```

## Step 1: Add Relationship Query to Neo4jDatabase

**File**: `src/neo4j_storage/graph_db.py`
**Location**: Add after `search_code_by_vector` method (~line 700)

```python
def get_node_relationships(self, node_id: str, relationship_types: List[str] = None, limit: int = 5) -> Dict[str, List[Dict]]:
    """Get relationships for a specific node
    
    Args:
        node_id: Node ID to query
        relationship_types: Types to include (default: all)
        limit: Max relationships per type
        
    Returns:
        Dict mapping relationship types to lists of related nodes
    """
    self._ensure_driver()
    if relationship_types is None:
        relationship_types = ['CALLS', 'CALLED_BY', 'EXTENDS', 'EXTENDED_BY', 'IMPORTS_FROM', 'IMPORTED_BY']
    
    relationships = {}
    
    try:
        with self.driver.session(database=self.database) as session:
            for rel_type in relationship_types:
                if rel_type == 'CALLS':
                    query = """
                    MATCH (n)-[:CALLS]->(target)
                    WHERE elementId(n) = $node_id
                    RETURN target LIMIT $limit
                    """
                elif rel_type == 'CALLED_BY':
                    query = """
                    MATCH (source)-[:CALLS]->(n)
                    WHERE elementId(n) = $node_id
                    RETURN source as target LIMIT $limit
                    """
                elif rel_type == 'EXTENDS':
                    query = """
                    MATCH (n)-[:EXTENDS]->(target)
                    WHERE elementId(n) = $node_id
                    RETURN target LIMIT $limit
                    """
                elif rel_type == 'EXTENDED_BY':
                    query = """
                    MATCH (source)-[:EXTENDS]->(n)
                    WHERE elementId(n) = $node_id
                    RETURN source as target LIMIT $limit
                    """
                elif rel_type == 'IMPORTS_FROM':
                    query = """
                    MATCH (n)-[:IMPORTS_FROM]->(target)
                    WHERE elementId(n) = $node_id
                    RETURN target LIMIT $limit
                    """
                elif rel_type == 'IMPORTED_BY':
                    query = """
                    MATCH (source)-[:IMPORTS_FROM]->(n)
                    WHERE elementId(n) = $node_id
                    RETURN source as target LIMIT $limit
                    """
                else:
                    continue
                
                result = session.run(query, {"node_id": node_id, "limit": limit})
                relationships[rel_type] = [dict(record["target"]) for record in result]
                
    except Exception as e:
        logger.error(f"Error getting relationships for node {node_id}: {e}")
        for rel_type in relationship_types:
            relationships[rel_type] = []
    
    return relationships
```

## Step 2: Add Grouping Methods to MCP Server

**File**: `src/mcp/server.py`
**Location**: Add as private methods in `CodebaseKnowledgeGraphMCP` class (after `__init__`)

```python
def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = sum(a * a for a in vec1) ** 0.5
    mag2 = sum(b * b for b in vec2) ** 0.5
    
    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0
    
    similarity = dot_product / (mag1 * mag2)
    return max(0.0, min(1.0, similarity))

def _group_results_by_similarity(self, results: List[Dict], threshold: float, max_groups: int = 10) -> Dict:
    """Group search results by semantic similarity"""
    if threshold <= 0.0 or not results:
        return {"groups": [], "ungrouped": results}
    
    groups = []
    used_indices = set()
    sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    
    for i, result in enumerate(sorted_results):
        if i in used_indices or len(groups) >= max_groups:
            continue
            
        current_embedding = result.get("node", {}).get("embedding")
        if not current_embedding:
            continue
            
        group = {
            "id": f"group_{len(groups)}",
            "representative": result,
            "items": [result],
            "similarity_score": 1.0
        }
        used_indices.add(i)
        
        # Find similar results
        for j, other_result in enumerate(sorted_results[i+1:], start=i+1):
            if j in used_indices:
                continue
                
            other_embedding = other_result.get("node", {}).get("embedding")
            if not other_embedding:
                continue
                
            similarity = self._calculate_cosine_similarity(current_embedding, other_embedding)
            if similarity >= threshold:
                group["items"].append(other_result)
                used_indices.add(j)
        
        groups.append(group)
    
    ungrouped = [r for i, r in enumerate(sorted_results) if i not in used_indices]
    
    return {
        "groups": groups,
        "ungrouped": ungrouped,
        "total_groups": len(groups),
        "total_ungrouped": len(ungrouped)
    }
```

## Step 3: Enhance search_code Tool

**File**: `src/mcp/server.py`
**Location**: Replace the existing `search_code` tool in `_register_tools` method (~line 79)

**Key Changes**:
1. Add `include_relationships: bool = True` parameter
2. Add `group_threshold: float = None` parameter
3. Add relationship enrichment after search
4. Add optional grouping before return

```python
@self.mcp.tool()
async def search_code(query: str, limit: int = 10, search_type: str = "vector", 
                     include_relationships: bool = True, group_threshold: float = None) -> str:
    """Search code with semantic relationships and optional grouping
    
    Args:
        query: Search query
        limit: Max results
        search_type: "vector" or "text"
        include_relationships: Add relationship data (default True)
        group_threshold: Similarity threshold for grouping (default from GROUP_THRESHOLD env var)
    """
    try:
        # Verify connection
        if not self.db.verify_connection():
            logger.warning("Database connection unavailable, reconnecting...")
            if not self.db.reconnect():
                return json.dumps({"error": "Database connection failed"})
        
        # Get grouping config
        if group_threshold is None:
            group_threshold = float(os.environ.get("GROUP_THRESHOLD", "0.0"))
        group_threshold = max(0.0, min(1.0, group_threshold))
        max_groups = int(os.environ.get("GROUP_MAX_GROUPS", "10"))
        
        # Perform search
        results = []
        if search_type == "vector":
            vector = self.code_embedder.provider.embed_text(query)
            if not vector or all(v == 0.0 for v in vector):
                return json.dumps({"error": "Failed to generate embedding"})
            
            for node_label in ["Function", "Method", "Class", "File"]:
                try:
                    node_results = self.db.search_code_by_vector(vector, node_label, limit)
                    results.extend(node_results)
                except Exception as e:
                    logger.warning(f"Error searching {node_label}: {e}")
            
            results = sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
        else:
            results = self.db.search_code_by_text(query, limit)
        
        # Add relationships
        if include_relationships:
            for result in results:
                node = result.get("node", {})
                node_id = node.get("id") or node.get("element_id")
                if node_id:
                    result["relationships"] = self.db.get_node_relationships(node_id)
        
        # Apply grouping if enabled
        if group_threshold > 0.0:
            grouped = self._group_results_by_similarity(results, group_threshold, max_groups)
            return json.dumps(grouped, ensure_ascii=False)
        
        return json.dumps({"results": results}, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return json.dumps({"error": str(e)})
```

## Step 4: Update Environment Configuration

**File**: `.env.example`
**Action**: Add these lines after existing configuration

```bash
# Semantic grouping configuration
GROUP_THRESHOLD=0.7          # Similarity threshold (0.0-1.0, default 0.7)
GROUP_MAX_GROUPS=10          # Max groups to create (default 10)
```

## Step 5: Test Implementation

Use the venv Python to run tests:

```powershell
# Test basic search with relationships
.venv\Scripts\python.exe -c "
import asyncio
import json
from src.mcp.server import CodebaseKnowledgeGraphMCP

async def test():
    server = CodebaseKnowledgeGraphMCP()
    # Access the tool directly from the registered tools
    tools = {t.name: t.fn for t in server.mcp._tool_manager._tools.values()}
    result = await tools['search_code']('database connection', limit=5)
    data = json.loads(result)
    print('Results:', len(data.get('results', [])))
    if data.get('results'):
        print('Has relationships:', 'relationships' in data['results'][0])

asyncio.run(test())
"

# Test grouping
.venv\Scripts\python.exe -c "
import asyncio
import json
import os
from src.mcp.server import CodebaseKnowledgeGraphMCP

os.environ['GROUP_THRESHOLD'] = '0.8'

async def test():
    server = CodebaseKnowledgeGraphMCP()
    tools = {t.name: t.fn for t in server.mcp._tool_manager._tools.values()}
    result = await tools['search_code']('error handling', limit=10)
    data = json.loads(result)
    print('Groups:', data.get('total_groups', 0))
    print('Ungrouped:', data.get('total_ungrouped', 0))

asyncio.run(test())
"
```

## Error Handling

- Invalid `group_threshold` → clamped to 0.0-1.0
- Missing node ID → skip relationships
- Relationship query failure → return empty dict
- Missing embedding → skip from grouping
- All errors logged with context
