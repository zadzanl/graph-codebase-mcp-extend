import os
import argparse
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.models import InitializationOptions
import sys
import json
from dotenv import load_dotenv

# Load environment variables from .env file
# This is critical for MCP server to access Neo4j credentials
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.neo4j_storage.graph_db import Neo4jDatabase
from src.embeddings.factory import get_embedding_provider
from src.embeddings.embedder import CodeEmbedder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CodebaseKnowledgeGraphMCP:
    """MCP server implementation for Codebase Knowledge Graph"""
    
    def __init__(self, neo4j_uri=None, neo4j_user=None, neo4j_password=None, server_host=None, server_port=None):
        """Initialize MCP server
        
        Args:
            neo4j_uri: Neo4j database URI, if None will get from environment variables
            neo4j_user: Neo4j username, if None will get from environment variables
            neo4j_password: Neo4j password, if None will get from environment variables
            server_host: MCP server host address, used for HTTP/SSE transport
            server_port: MCP server port, used for HTTP/SSE transport
        """
        self.neo4j_uri = neo4j_uri or os.environ.get("NEO4J_URI")
        self.neo4j_user = neo4j_user or os.environ.get("NEO4J_USER")
        self.neo4j_password = neo4j_password or os.environ.get("NEO4J_PASSWORD")
        
        # Get server configuration from parameters, environment, or use defaults
        self.server_host = server_host or os.environ.get("MCP_SERVER_HOST", "127.0.0.1")
        self.server_port = server_port or int(os.environ.get("MCP_SERVER_PORT", "8080"))
        
        # Initialize FastMCP (configure host and port)
        self.mcp = FastMCP(
            name="Codebase KG Server",
            host=self.server_host,
            port=self.server_port
        )
        
        # Initialize Neo4j database
        self.db = Neo4jDatabase(
            uri=self.neo4j_uri,
            user=self.neo4j_user,
            password=self.neo4j_password
        )

        # Initialize embedding handler (using factory pattern to support multiple providers)
        embedding_provider = get_embedding_provider()
        self.code_embedder = CodeEmbedder(embedding_provider)

        # Register MCP tools
        self._register_tools()

        # Register MCP prompts
        self._register_prompts()

        # Register MCP resources
        self._register_resources()
    
    def _register_tools(self):
        """Register MCP tools"""
        
        @self.mcp.tool()
        async def search_code(
            query: str,
            limit: int = 10,
            search_type: str = "vector",
            include_relationships: bool = True,
            group_threshold: Optional[float] = 0.0
        ) -> str:
            """Search code

            Args:
                query: Search query
                limit: Maximum number of results to return
                search_type: Search type, can be "vector" or "text"
                include_relationships: Whether to include semantic relationships
                group_threshold: Threshold for semantic grouping (0.0 to disable)

            Returns:
                JSON string of search results
            """
            results = await self._search_code_impl(
                query=query,
                limit=limit,
                search_type=search_type,
                include_relationships=include_relationships,
                group_threshold=group_threshold
            )
            return json.dumps(results, ensure_ascii=False)
        
        @self.mcp.tool()
        async def execute_cypher_query(query: str, parameters: Dict = None) -> str:
            """Execute Cypher query
            
            Args:
                query: Cypher query statement
                parameters: Query parameters
                
            Returns:
                JSON string of query results
            """
            try:
                results = self.db.execute_cypher(query, parameters)
                return json.dumps(results, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Error occurred while executing Cypher query: {e}")
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def get_code_by_name(name: str, node_type: str = None) -> str:
            """Get code by name
            
            Args:
                name: Code name (class name, function name, etc.)
                node_type: Node type, can be "Function", "Method", "Class", "File"
                
            Returns:
                JSON string of code
            """
            try:
                query = """
                MATCH (n)
                WHERE n.name = $name
                """
                
                if node_type:
                    query += f" AND n:{node_type}"
                
                query += " RETURN n LIMIT 10"
                
                results = self.db.execute_cypher(query, {"name": name})
                return json.dumps(results, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Error occurred while getting code: {e}")
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def find_function_callers(function_name: str, limit: int = 10) -> str:
            """Find all locations that call a specific function
            
            Args:
                function_name: Function name
                limit: Maximum number of results to return
                
            Returns:
                JSON string of callers
            """
            try:
                query = """
                MATCH (caller)-[:CALLS]->(callee)
                WHERE callee.name = $function_name
                RETURN caller
                LIMIT $limit
                """
                
                results = self.db.execute_cypher(query, {
                    "function_name": function_name,
                    "limit": limit
                })
                
                return json.dumps(results, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Error occurred while finding function callers: {e}")
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def find_function_callees(function_name: str, limit: int = 10) -> str:
            """Find all functions called by a specific function
            
            Args:
                function_name: Function name
                limit: Maximum number of results to return
                
            Returns:
                JSON string of called functions
            """
            try:
                query = """
                MATCH (caller)-[:CALLS]->(callee)
                WHERE caller.name = $function_name
                RETURN callee
                LIMIT $limit
                """
                
                results = self.db.execute_cypher(query, {
                    "function_name": function_name,
                    "limit": limit
                })
                
                return json.dumps(results, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Error occurred while finding function callees: {e}")
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def find_class_inheritance(class_name: str) -> str:
            """Find class inheritance relationships
            
            Args:
                class_name: Class name
                
            Returns:
                JSON string of inheritance relationships
            """
            try:
                # Find superclasses
                superclasses_query = """
                MATCH (sub:Class {name: $class_name})-[:EXTENDS]->(super:Class)
                RETURN super
                """
                
                superclasses = self.db.execute_cypher(superclasses_query, {
                    "class_name": class_name
                })
                
                # Find subclasses
                subclasses_query = """
                MATCH (sub:Class)-[:EXTENDS]->(super:Class {name: $class_name})
                RETURN sub
                """
                
                subclasses = self.db.execute_cypher(subclasses_query, {
                    "class_name": class_name
                })
                
                return json.dumps({
                    "superclasses": superclasses,
                    "subclasses": subclasses
                }, ensure_ascii=False)
                
            except Exception as e:
                logger.error(f"Error occurred while finding class inheritance: {e}")
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def find_file_dependencies(file_path: str) -> str:
            """Find file dependencies
            
            Args:
                file_path: File path
                
            Returns:
                JSON string of dependencies
            """
            try:
                # Find modules imported by this file (using IMPORTS_FROM)
                imports_query = """
                MATCH (f:File {path: $file_path})-[:IMPORTS_FROM]->(target:File)
                RETURN target
                """
                
                imports = self.db.execute_cypher(imports_query, {
                    "file_path": file_path
                })
                
                # Find files that import from this file
                imported_by_query = """
                MATCH (f:File)-[:IMPORTS_FROM]->(target:File {path: $file_path})
                RETURN f
                """
                
                imported_by = self.db.execute_cypher(imported_by_query, {
                    "file_path": file_path
                })
                
                return json.dumps({
                    "imports": imports,
                    "imported_by": imported_by
                }, ensure_ascii=False)
                
            except Exception as e:
                logger.error(f"Error occurred while finding file dependencies: {e}")
                return json.dumps({"error": str(e)})
    
    def _register_prompts(self):
        """Register MCP prompts"""
        
        @self.mcp.prompt()
        def code_search_prompt(query: str) -> str:
            """Create code search prompt
            
            Args:
                query: Search query
                
            Returns:
                Generated prompt
            """
            return f"""
            You are a codebase expert, please help me search for code related to the following query:
            
            Query: {query}
            
            Please prioritize the following aspects:
            1. Search for related functions, methods, classes, or files
            2. Analyze relationships between code (such as call relationships, inheritance relationships, etc.)
            3. Explain the functionality and purpose of the found code
            
            You can use the provided tools to perform the search and analyze the results.
            """
        
        @self.mcp.prompt()
        def code_understanding_prompt(code_element: str, element_type: str) -> str:
            """Create code understanding prompt
            
            Args:
                code_element: Code element name (function name, class name, etc.)
                element_type: Element type ("Function", "Class", "File", etc.)
                
            Returns:
                Generated prompt
            """
            return f"""
            You are a code analysis expert, please help me understand the following code element:
            
            Element name: {code_element}
            Element type: {element_type}
            
            Please provide the following analysis:
            1. The main functionality and purpose of this element
            2. Its relationship with other code elements (such as call relationships, inheritance relationships, etc.)
            3. Usage methods and examples of this element
            
            You can use the provided tools to get detailed information about this element and analyze its structure.
            """
    
    def _register_resources(self):
        """Register MCP resources"""
        
        @self.mcp.resource("schema://kg")
        def get_kg_schema() -> str:
            """Get knowledge graph schema description
            
            Returns:
                Description of knowledge graph structure
            """
            return """
            Knowledge Graph Structure:
            
            Node Types:
            - File: Represents a code file
              - Properties: id, path, name
            - Class: Represents a class definition
              - Properties: id, name, file_path, line_no, end_line_no, code_snippet
            - Function: Represents a global function definition
              - Properties: id, name, file_path, line_no, end_line_no, code_snippet
            - Method: Represents a class method
              - Properties: id, name, file_path, line_no, end_line_no, code_snippet
            - Variable: Represents a variable definition
              - Properties: id, name, file_path, line_no
            - Module: Represents an imported module
              - Properties: id, name
            
            Relationship Types:
            - CONTAINS: Indicates a file contains a code element
              - Example: (File)-[:CONTAINS]->(Function)
            - DEFINES: Indicates a class defines a method or property
              - Example: (Class)-[:DEFINES]->(Method)
            - CALLS: Indicates function call relationships
              - Example: (Function)-[:CALLS]->(Function)
            - EXTENDS: Indicates class inheritance relationships
              - Example: (Class)-[:EXTENDS]->(Class)
            - IMPORTS: Indicates a file imports a module
              - Example: (File)-[:IMPORTS]->(Module)
            """
        
        @self.mcp.resource("cypher://examples")
        def get_cypher_examples() -> str:
            """Get Cypher query examples
            
            Returns:
                Cypher query examples
            """
            return """
            Cypher Query Examples:
            
            1. Find a function with a specific name:
            ```
            MATCH (f:Function)
            WHERE f.name = "process_data"
            RETURN f
            ```
            
            2. Find all functions that call a certain function:
            ```
            MATCH (caller)-[:CALLS]->(callee:Function)
            WHERE callee.name = "process_data"
            RETURN caller
            ```
            
            3. Find all classes that inherit from a certain class:
            ```
            MATCH (sub:Class)-[:EXTENDS]->(super:Class)
            WHERE super.name = "BaseProcessor"
            RETURN sub
            ```
            
            4. Find a file and the functions it contains:
            ```
            MATCH (file:File)-[:CONTAINS]->(func:Function)
            WHERE file.path = "src/main.py"
            RETURN func
            ```
            
            5. Find all files that import a certain module:
            ```
            MATCH (file:File)-[:IMPORTS]->(module:Module)
            WHERE module.name = "pandas"
            RETURN file
            ```
            """
    
    def _calculate_cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0

        try:
            import math

            values1 = [float(value) for value in v1]
            values2 = [float(value) for value in v2]
            if not all(math.isfinite(value) for value in values1 + values2):
                return 0.0

            dot_product = sum(a * b for a, b in zip(values1, values2))
            magnitude1 = math.sqrt(sum(a * a for a in values1))
            magnitude2 = math.sqrt(sum(b * b for b in values2))

            if magnitude1 == 0.0 or magnitude2 == 0.0:
                return 0.0

            similarity = dot_product / (magnitude1 * magnitude2)
            return max(0.0, min(1.0, similarity))
        except (TypeError, ValueError):
            return 0.0

    def _empty_relationships(self) -> Dict[str, List]:
        """Return empty relationship buckets"""
        return {
            "calls": [], "called_by": [],
            "extends": [], "extended_by": [],
            "imports": [], "imported_by": []
        }

    def _resolve_group_threshold(self, group_threshold: Optional[float]) -> float:
        """Resolve grouping threshold from parameter or environment."""
        import math

        if group_threshold is None:
            raw_value = os.environ.get("GROUP_THRESHOLD", "0.7")
            fallback = 0.7
            source = "GROUP_THRESHOLD"
        else:
            raw_value = group_threshold
            fallback = 0.0
            source = "group_threshold"

        try:
            threshold = float(raw_value)
        except (TypeError, ValueError):
            logger.warning("Invalid %s value %r; using %.1f", source, raw_value, fallback)
            return fallback

        if not math.isfinite(threshold):
            logger.warning("Invalid %s value %r; using %.1f", source, raw_value, fallback)
            return fallback

        clamped = max(0.0, min(1.0, threshold))
        if clamped != threshold:
            logger.warning("Clamped %s value %r to %.1f", source, raw_value, clamped)
        return clamped

    def _get_group_max_groups(self) -> int:
        """Get maximum number of groups from environment"""
        env_val = os.environ.get("GROUP_MAX_GROUPS")
        if env_val is not None:
            try:
                max_groups = int(env_val)
                if max_groups >= 1:
                    return max_groups
                logger.warning("Invalid GROUP_MAX_GROUPS value %r; using 10", env_val)
            except (TypeError, ValueError):
                logger.warning("Invalid GROUP_MAX_GROUPS value %r; using 10", env_val)
        return 10  # Default

    def _group_results_by_similarity(
        self,
        results: List[Dict[str, Any]],
        threshold: float,
        max_groups: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Group search results by semantic similarity"""
        max_groups = max_groups or self._get_group_max_groups()
        if not results:
            return {"groups": [], "ungrouped": [], "total_groups": 0, "total_ungrouped": 0}

        if threshold <= 0.0:
            return {
                "groups": [],
                "ungrouped": results,
                "total_groups": 0,
                "total_ungrouped": len(results),
            }

        groups = []
        ungrouped = []
        sorted_results = sorted(results, key=lambda item: item.get("score", 0), reverse=True)

        for item in sorted_results:
            node = item.get("node", {})
            embedding = node.get("embedding")

            if not embedding or not isinstance(embedding, list):
                ungrouped.append(item)
                continue

            # Try to find a matching group
            found_group = False
            for group in groups:
                # Compare with the representative (first item) of the group
                rep_embedding = group["representative"].get("node", {}).get("embedding")
                similarity = self._calculate_cosine_similarity(embedding, rep_embedding)
                if similarity >= threshold:
                    group["items"].append(item)
                    group.setdefault("_similarities", []).append(similarity)
                    group["similarity_score"] = sum(group["_similarities"]) / len(group["_similarities"])
                    found_group = True
                    break

            if not found_group:
                if len(groups) < max_groups:
                    groups.append({
                        "id": f"group_{len(groups) + 1}",
                        "representative": item,
                        "items": [item],
                        "similarity_score": 1.0,
                        "_similarities": [1.0],
                    })
                else:
                    ungrouped.append(item)

        for group in groups:
            group.pop("_similarities", None)

        return {
            "groups": groups,
            "ungrouped": ungrouped,
            "total_groups": len(groups),
            "total_ungrouped": len(ungrouped),
        }

    async def _search_code_impl(
        self,
        query: str,
        limit: int = 10,
        search_type: str = "vector",
        include_relationships: bool = True,
        group_threshold: Optional[float] = 0.0
    ) -> Dict[str, Any]:
        """Implementation logic for code search"""
        try:
            # Verify connection before performing search
            if not self.db.verify_connection():
                logger.warning("Database connection is not available, attempting to reconnect...")
                if not self.db.reconnect():
                    return {"error": "Database connection is not available."}

            results = []
            if search_type == "vector":
                vector = self.code_embedder.provider.embed_text(query)
                if not vector or all(v == 0.0 for v in vector):
                    return {"error": "Failed to generate embedding for query."}

                for node_label in ["Function", "Method", "Class", "File"]:
                    try:
                        node_results = self.db.search_code_by_vector(vector, node_label, limit)
                        results.extend(node_results)
                    except Exception as node_error:
                        logger.warning(f"Error searching {node_label} nodes: {node_error}")
                        continue

                results = sorted(results, key=lambda x: x["score"], reverse=True)[:limit]

            elif search_type == "text":
                results = self.db.search_code_by_text(query, limit)

            # Add relationships if requested
            if include_relationships:
                for item in results:
                    node = item.get("node", {})
                    node_id = node.get("id")
                    if not node_id:
                        item["relationships"] = self._empty_relationships()
                        continue

                    try:
                        item["relationships"] = self.db.get_node_relationships(node_id)
                    except Exception as relationship_error:
                        logger.warning(
                            "Error getting relationships for node %s: %s",
                            node_id,
                            relationship_error,
                        )
                        item["relationships"] = self._empty_relationships()

            # Handle grouping
            resolved_threshold = self._resolve_group_threshold(group_threshold)
            if resolved_threshold > 0.0:
                response = self._group_results_by_similarity(
                    results,
                    resolved_threshold,
                    self._get_group_max_groups(),
                )
                return response
            else:
                return {"results": results}

        except Exception as e:
            logger.error(f"Error in _search_code_impl: {e}", exc_info=True)
            return {"error": str(e)}

    def start(self, port=None, transport="stdio"):
        """Start MCP server
        
        Args:
            port: HTTP server port number (ignored, port is set during initialization)
            transport: Transport protocol, can be "stdio", "http" (streamable-http), or "sse"
        """
        if transport == "http":
            logger.info(f"MCP server starting in HTTP mode, listening on http://{self.server_host}:{self.server_port}/mcp")
            self.mcp.run(transport="streamable-http")
        elif transport == "sse":
            logger.info(f"MCP server starting in SSE mode, listening on http://{self.server_host}:{self.server_port}/sse")
            self.mcp.run(transport="sse")
        else:
            logger.info("MCP server starting in stdio mode")
            self.mcp.run(transport="stdio")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Codebase Knowledge Graph MCP Server")
    parser.add_argument("--codebase-path", help="Codebase path", default=".")
    parser.add_argument("--transport", choices=["stdio", "http", "sse"], default="stdio", help="MCP transport protocol")
    parser.add_argument("--port", type=int, help="HTTP server port number (only for HTTP/SSE transport)", default=8080)
    parser.add_argument("--neo4j-uri", help="Neo4j database URI")
    parser.add_argument("--neo4j-user", help="Neo4j username")
    parser.add_argument("--neo4j-password", help="Neo4j password")
    
    args = parser.parse_args()
    
    # Create MCP server
    server = CodebaseKnowledgeGraphMCP(
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password,
        server_port=args.port
    )
    
    # Start server
    server.start(transport=args.transport)


if __name__ == "__main__":
    main()