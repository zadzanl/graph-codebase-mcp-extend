import os
import sys
import argparse
import logging
import time
from typing import Dict, List, Any, Tuple, Optional
from dotenv import load_dotenv
import json
from concurrent.futures import as_completed

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ast_parser.parser import ASTParser
from src.ast_parser.multi_parser import MultiLanguageParser
from src.embeddings.factory import get_embedding_provider
from src.embeddings.embedder import CodeEmbedder, OpenAIEmbeddings
from src.neo4j_storage.graph_db import Neo4jDatabase
from src.parallel.pool_manager import get_processing_pool
from src.utils.runtime_detection import log_runtime_info

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CodebaseKnowledgeGraph:
    """Class for creating and managing the codebase knowledge graph"""
    
    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        """Initialize the Codebase Knowledge Graph
        
        Args:
            neo4j_uri: Neo4j database URI, if None, get from environment variables
            neo4j_user: Neo4j username, if None, get from environment variables
            neo4j_password: Neo4j password, if None, get from environment variables
        """
        self.neo4j_uri = neo4j_uri or os.environ.get("NEO4J_URI")
        self.neo4j_user = neo4j_user or os.environ.get("NEO4J_USER")
        self.neo4j_password = neo4j_password or os.environ.get("NEO4J_PASSWORD")
        
        # Validate configuration
        self._validate_configuration()
        
        # Initialize Neo4j database connection with connection pooling
        max_pool_size = self._get_neo4j_pool_size()
        self.db = Neo4jDatabase(
            uri=self.neo4j_uri or "",
            user=self.neo4j_user or "",
            password=self.neo4j_password or "",
            max_connection_pool_size=max_pool_size
        )
        
        # Initialize code parser
        self.parser = ASTParser()
        
        # Store ast-grep feature flags for use in parsing methods
        self.use_ast_grep = os.getenv("USE_AST_GREP", "false").lower() == "true"
        self.ast_grep_languages = os.getenv("AST_GREP_LANGUAGES", "python,javascript,typescript").split(',')
        self.ast_grep_fallback = os.getenv("AST_GREP_FALLBACK_TO_LEGACY", "true").lower() == "true"
        
        # Initialize embedding handler
        # If an explicit API key is provided prefer the wrapper, otherwise use the factory
        if openai_api_key:
            self.embedder = OpenAIEmbeddings(api_key=openai_api_key)
        else:
            self.embedder = get_embedding_provider()

        self.code_embedder = CodeEmbedder(self.embedder)
    
    def _validate_configuration(self) -> None:
        """Validate configuration parameters
        """
        # Validate MAX_WORKERS
        max_workers_str = os.getenv("MAX_WORKERS", "")
        if max_workers_str:
            try:
                max_workers = int(max_workers_str)
                if max_workers <= 0:
                    logger.warning(f"MAX_WORKERS must be greater than 0, current value: {max_workers}. Will use default")
                elif max_workers > 128:
                    logger.warning(f"MAX_WORKERS too large ({max_workers}). Recommend <= 128. May cause resource exhaustion")
            except ValueError:
                logger.warning(f"Invalid MAX_WORKERS value: '{max_workers_str}'. Will use default")
        
        # Validate NEO4J_MAX_CONNECTION_POOL_SIZE
        from src.utils.runtime_detection import get_optimal_worker_count
        optimal_workers = get_optimal_worker_count()
        
        pool_size_str = os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", "")
        if pool_size_str:
            try:
                pool_size = int(pool_size_str)
                if pool_size < optimal_workers:
                    logger.warning(
                        f"NEO4J_MAX_CONNECTION_POOL_SIZE ({pool_size}) is less than MAX_WORKERS ({optimal_workers}). "
                        f"Recommend setting to at least {optimal_workers * 2} to avoid connection pool exhaustion"
                    )
            except ValueError:
                logger.warning(f"Invalid NEO4J_MAX_CONNECTION_POOL_SIZE value: '{pool_size_str}'")
        
        # Validate MIN_FILES_FOR_PARALLEL
        min_files_str = os.getenv("MIN_FILES_FOR_PARALLEL", "")
        if min_files_str:
            try:
                min_files = int(min_files_str)
                if min_files < 1:
                    logger.warning(f"MIN_FILES_FOR_PARALLEL must be at least 1, current value: {min_files}")
                elif min_files < 10:
                    logger.info(f"MIN_FILES_FOR_PARALLEL ({min_files}) is small. Parallel processing may not bring performance gains")
            except ValueError:
                logger.warning(f"Invalid MIN_FILES_FOR_PARALLEL value: '{min_files_str}'")
    
    def _get_neo4j_pool_size(self) -> int:
        """Get Neo4j connection pool size
        
        Returns:
            Connection pool size
        """
        from src.utils.runtime_detection import get_optimal_worker_count
        
        pool_size_str = os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", "")
        if pool_size_str:
            try:
                return int(pool_size_str)
            except ValueError:
                pass
        
        # Default: MAX_WORKERS * 2, minimum 16
        optimal_workers = get_optimal_worker_count()
        default_size = max(optimal_workers * 2, 16)
        logger.info(f"Using default Neo4j connection pool size: {default_size}")
        return default_size
    
    def process_codebase(self, codebase_path: str, clear_db: bool = False) -> Tuple[int, int]:
        """Process the entire codebase, parse and import into the knowledge graph
        
        Args:
            codebase_path: Directory path of the codebase
            clear_db: Whether to clear the database
            
        Returns:
            Number of nodes and relationships processed
        """
        start_time = time.time()
        logger.info(f"Starting to process codebase: {codebase_path}")
        
        # Log runtime information (GIL status, Python version, etc.)
        log_runtime_info()
        
        # Verify database connection
        if not self.db.verify_connection():
            raise ConnectionError("Cannot connect to Neo4j database, please check connection settings")
        
        # Clear the database (if needed)
        if clear_db:
            logger.info("Clearing database...")
            self.db.clear_database()
        
        # Create database schema
        logger.info("Creating database schema...")
        self.db.create_schema_constraints()
        
        # Collect all source files (Python, JS, TS)
        source_files = self._collect_source_files(codebase_path)
        logger.info(f"Found {len(source_files)} source code files")
        
        # Get configuration for parallel processing
        parallel_enabled = os.getenv("PARALLEL_INDEXING_ENABLED", "true").lower() == "true"
        min_files_for_parallel = int(os.getenv("MIN_FILES_FOR_PARALLEL", "50"))
        
        # Determine if we should use parallel processing
        use_parallel = parallel_enabled and len(source_files) >= min_files_for_parallel
        
        if use_parallel:
            logger.info(f"Using parallel processing mode to process {len(source_files)} files")
            nodes, relations = self._process_files_parallel(source_files, codebase_path)
        else:
            logger.info(f"Using sequential processing mode to process {len(source_files)} files")
            # For sequential mode, we still need to use the router
            nodes, relations = self._process_directory_with_routing(codebase_path)
        
        logger.info(f"Total parsed {len(nodes)} nodes and {len(relations)} relationships")
        
        # Generate embedding vectors for nodes
        logger.info("Generating embedding vectors for nodes...")
        self._generate_embeddings(nodes)
        
        # Convert nodes to Neo4j format and import into the database
        logger.info("Importing nodes into database...")
        neo4j_nodes = self._convert_nodes_to_neo4j_format(nodes)
        self.db.batch_create_nodes(neo4j_nodes)
        
        # Convert relationships to Neo4j format and import into the database
        logger.info("Importing relationships into database...")
        neo4j_relations = self._convert_relations_to_neo4j_format(relations)
        self.db.batch_create_relationships(neo4j_relations)
        
        # Create vector index (for similarity search)
        logger.info("Creating vector indexes...")
        try:
            for node_label in ["Function", "Method", "Class", "File"]:
                try:
                    self.db.create_vector_index(
                        index_name=f"{node_label.lower()}_vector_index",
                        node_label=node_label,
                        property_name="embedding",
                        dimension=getattr(self.embedder, 'dimension', 1536)  # use configured provider dimension when available
                    )
                except Exception as e:
                    logger.warning(f"Warning when creating {node_label} vector index: {e}")
        except Exception as e:
            logger.error(f"Error creating vector indexes: {e}")
        
        # Create full-text search index
        logger.info("Creating full-text search indexes...")
        try:
            self.db.create_full_text_index(
                index_name="code_index",
                node_labels=["Function", "Method", "Class", "File"],
                properties=["name", "code_snippet"]
            )
        except Exception as e:
            logger.error(f"Error creating full-text search index: {e}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Codebase processing complete! Time taken: {elapsed_time:.2f} seconds (Parallel mode: {use_parallel})")
        return len(nodes), len(relations)
    
    def _collect_source_files(self, directory_path: str) -> List[str]:
        """Collect all source code files in the directory (supports 7 languages)
        
        Args:
            directory_path: Directory path
            
        Returns:
            List of source code file paths
        """
        source_files = []
        
        # When USE_AST_GREP is enabled, collect files based on AST_GREP_LANGUAGES
        if self.use_ast_grep:
            supported_extensions = []
            if 'python' in self.ast_grep_languages:
                supported_extensions.append('.py')
            if 'javascript' in self.ast_grep_languages or 'typescript' in self.ast_grep_languages:
                supported_extensions.extend(['.js', '.ts', '.jsx', '.tsx'])
            if 'java' in self.ast_grep_languages:
                supported_extensions.append('.java')
            if 'cpp' in self.ast_grep_languages:
                supported_extensions.extend(['.cpp', '.cc', '.cxx', '.h', '.hpp'])
            if 'rust' in self.ast_grep_languages:
                supported_extensions.append('.rs')
            if 'go' in self.ast_grep_languages:
                supported_extensions.append('.go')
            supported_extensions = tuple(supported_extensions)
            
            logger.info(f"ast-grep mode enabled languages: {', '.join(self.ast_grep_languages)}")
        else:
            # Legacy mode: only Python and optionally JS/TS
            enable_js_ts = os.getenv("ENABLE_JS_TS_PARSING", "true").lower() == "true"
            python_extensions = (".py",)
            js_ts_extensions = (".js", ".ts", ".jsx", ".tsx") if enable_js_ts else ()
            supported_extensions = python_extensions + js_ts_extensions
            
            if enable_js_ts:
                logger.info("Multi-language support enabled: Python, JavaScript, TypeScript")
            else:
                logger.info("Only Python support enabled")
        
        for root, _, files in os.walk(directory_path):
            for file_name in files:
                if file_name.endswith(supported_extensions):
                    file_path = os.path.join(root, file_name)
                    source_files.append(file_path)
        
        return source_files
    
    def _get_parser_for_file(self, file_path: str):
        """Select the appropriate parser based on file extension
        
        Args:
            file_path: File path
            
        Returns:
            Parser instance (ASTParser, TypeScriptParser, or MultiLanguageParser), None if unsupported
        """
        # When USE_AST_GREP is enabled, use MultiLanguageParser coordinator
        if self.use_ast_grep:
            return MultiLanguageParser(
                use_ast_grep=True,
                ast_grep_languages=self.ast_grep_languages,
                ast_grep_fallback=self.ast_grep_fallback
            )
        
        # Otherwise, use legacy routing
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.py':
            from src.ast_parser.parser import ASTParser
            return ASTParser()
        elif ext in ['.js', '.ts', '.jsx', '.tsx']:
            from src.ast_parser.typescript_parser import TypeScriptParser
            return TypeScriptParser()
        else:
            logger.warning(f"Unsupported file extension: {ext} ({file_path})")
            return None
    
    def _process_directory_with_routing(self, directory_path: str) -> Tuple[Dict[str, Any], List[Any]]:
        """Process directory with parser routing (sequential mode)
        
        Args:
            directory_path: Directory path
            
        Returns:
            Node dictionary and relationship list
        """
        # When USE_AST_GREP is enabled, use MultiLanguageParser for coordinated parsing
        if self.use_ast_grep:
            coordinator = MultiLanguageParser(
                use_ast_grep=True,
                ast_grep_languages=self.ast_grep_languages,
                ast_grep_fallback=self.ast_grep_fallback
            )
            return coordinator.parse_directory(directory_path, build_index=True)
        
        # Legacy routing (USE_AST_GREP=false)
        all_nodes = {}
        all_module_definitions = {}
        all_pending_imports = []
        all_module_to_file = {}
        
        # Collect all source files
        source_files = self._collect_source_files(directory_path)
        
        # First pass: Parse all files and build index
        for file_path in source_files:
            try:
                parser = self._get_parser_for_file(file_path)
                if parser:
                    nodes, _ = parser.parse_file(file_path, build_index=True)
                    
                    # Merge results
                    all_nodes.update(nodes)
                    all_module_definitions.update(parser.module_definitions)
                    all_pending_imports.extend(parser.pending_imports)
                    all_module_to_file.update(parser.module_to_file)
            except Exception as e:
                logger.error(f"Error parsing file {file_path}: {e}")
        
        # Second pass: Process pending imports
        # Create a temporary parser to process imports
        from src.ast_parser.parser import ASTParser
        temp_parser = ASTParser()
        temp_parser.nodes = all_nodes
        temp_parser.module_definitions = all_module_definitions
        temp_parser.pending_imports = all_pending_imports
        temp_parser.module_to_file = all_module_to_file
        temp_parser._process_pending_imports()
        
        return all_nodes, temp_parser.relations
    
    def _process_files_parallel(self, source_files: List[str], codebase_path: str) -> Tuple[Dict[str, Any], List[Any]]:
        """Process source files using parallel processing mode (multi-language support)
        
        Args:
            source_files: List of source file paths
            codebase_path: Codebase directory path
            
        Returns:
            Node dictionary and relationship list
        """
        from src.ast_parser.parser import ASTParser
        from src.ast_parser.typescript_parser import TypeScriptParser
        
        try:
            # First pass: Parse all files in parallel to build module definition index
            logger.info("First pass: Parsing all files in parallel...")
            
            # Create a shared parser for collecting results
            # Each worker will create its own parser instance
            all_nodes = {}
            all_module_definitions = {}
            all_pending_imports = []
            all_module_to_file = {}
            
            def parse_file_worker(file_path: str) -> Tuple[Dict, Dict, List, Dict]:
                """Worker function to parse a single file
                
                Args:
                    file_path: Path to the source file
                    
                Returns:
                    Tuple of (nodes, module_definitions, pending_imports, module_to_file)
                """
                try:
                    # When USE_AST_GREP is enabled, use MultiLanguageParser
                    if self.use_ast_grep:
                        parser = MultiLanguageParser(
                            use_ast_grep=True,
                            ast_grep_languages=self.ast_grep_languages,
                            ast_grep_fallback=self.ast_grep_fallback
                        )
                    else:
                        # Legacy routing: Select parser based on file extension
                        ext = os.path.splitext(file_path)[1].lower()
                        
                        if ext == '.py':
                            parser = ASTParser()
                        elif ext in ['.js', '.ts', '.jsx', '.tsx']:
                            parser = TypeScriptParser()
                        else:
                            logger.warning(f"Unsupported file extension: {ext} ({file_path})")
                            return ({}, {}, [], {})
                    
                    parser.parse_file(file_path, build_index=True)
                    
                    return (
                        dict(parser.nodes),
                        dict(parser.module_definitions),
                        list(parser.pending_imports),
                        dict(parser.module_to_file)
                    )
                except Exception as e:
                    logger.error(f"Error parsing file {file_path}: {e}")
                    return ({}, {}, [], {})
            
            # Use the processing pool manager to process files in parallel
            with get_processing_pool() as pool:
                # Submit all file parsing tasks
                futures = [pool.submit(parse_file_worker, file_path) for file_path in source_files]
                
                # Filter out None values (though submit() should always return a Future)
                futures = [f for f in futures if f is not None]
                
                # Collect results as they complete
                completed = 0
                for future in as_completed(futures):
                    try:
                        nodes, module_defs, pending, module_files = future.result()
                        
                        # Merge results
                        all_nodes.update(nodes)
                        all_module_definitions.update(module_defs)
                        all_pending_imports.extend(pending)
                        all_module_to_file.update(module_files)
                        
                        completed += 1
                        if completed % 10 == 0:
                            logger.info(f"Completed {completed}/{len(source_files)} files")
                    except Exception as e:
                        logger.error(f"Error processing file result: {e}")
            
            logger.info(f"First pass complete: Parsed {len(all_nodes)} nodes")
            
            # Second pass: Process pending imports sequentially
            # This must be sequential because it requires the complete module definition index
            logger.info("Second pass: Processing pending imports...")
            
            # Create a parser with the aggregated data to process imports
            final_parser = ASTParser()
            final_parser.nodes = all_nodes
            final_parser.module_definitions = all_module_definitions
            final_parser.pending_imports = all_pending_imports
            final_parser.module_to_file = all_module_to_file
            
            # Process all pending imports
            final_parser._process_pending_imports()
            
            logger.info(f"Second pass complete: Processed {len(final_parser.relations)} relationships")
            
            return final_parser.nodes, final_parser.relations
            
        except Exception as e:
            # Graceful degradation: Fall back to sequential processing
            logger.error(f"Parallel processing failed: {e}")
            logger.warning("Falling back to sequential processing mode...")
            
            # Log detailed error for debugging
            import traceback
            logger.debug(f"Parallel processing error details:\n{traceback.format_exc()}")
            
            # Use sequential processing with routing
            return self._process_directory_with_routing(codebase_path)
    
    def _generate_embeddings(self, nodes: Dict[str, Any]) -> None:
        """Generate embedding vectors for nodes
        
        Args:
            nodes: Node dictionary
        """
        batch_size = 20  # Batch size to avoid API limits
        
        # Only generate embeddings for specific node types
        target_types = ["Function", "Method", "Class", "File"]
        
        nodes_to_embed = [
            (node_id, node) for node_id, node in nodes.items()
            if node.node_type in target_types
        ]
        
        for i in range(0, len(nodes_to_embed), batch_size):
            batch = nodes_to_embed[i:i+batch_size]
            
            # Reset batch data
            code_texts = []
            node_types = []
            names = []
            node_ids = []
            
            # Collect batch data
            for node_id, node in batch:
                # For file types, use the file name as the code text
                if node.node_type == "File":
                    code_text = f"File: {node.name}"
                else:
                    code_text = node.code_snippet or f"{node.node_type}: {node.name}"
                
                code_texts.append(code_text)
                node_types.append(node.node_type)
                names.append(node.name)
                node_ids.append(node_id)
            
            # Only generate embeddings if there is data to process
            if code_texts:
                # Batch generate embedding vectors
                embeddings = self.code_embedder.embed_code_nodes_batch(
                    code_texts=code_texts,
                    node_types=node_types,
                    names=names
                )
                
                # Ensure embedding vector matches node list length
                if len(embeddings) >= len(node_ids):
                    # Add embedding vector to node
                    for i, node_id in enumerate(node_ids):
                        nodes[node_id].properties["embedding"] = embeddings[i]
                    
                    logger.debug(f"Generated embeddings for {len(batch)} nodes")
                else:
                    # Handle cases where the number of embedding vectors is insufficient
                    logger.warning(f"Number of embeddings ({len(embeddings)}) is less than number of nodes ({len(node_ids)}), using zero vectors as substitute")
                    for i, node_id in enumerate(node_ids):
                        if i < len(embeddings):
                            nodes[node_id].properties["embedding"] = embeddings[i]
                        else:
                            # Use zero vectors as a substitute
                            nodes[node_id].properties["embedding"] = [0.0] * getattr(self.embedder, 'dimension', 1536)
    
    def _convert_nodes_to_neo4j_format(self, nodes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert nodes to Neo4j bulk import format
        
        Args:
            nodes: Node dictionary
            
        Returns:
            List of nodes in Neo4j format
        """
        neo4j_nodes = []
        
        for node_id, node in nodes.items():
            # Create basic properties
            properties = {
                "id": node_id,
                "name": node.name,
                "file_path": node.file_path,
                "line_no": node.line_no
            }
            
            # Add node type specific properties
            if node.end_line_no:
                properties["end_line_no"] = node.end_line_no
            
            if node.code_snippet:
                properties["code_snippet"] = node.code_snippet
            
            # Add embedding vector (if any)
            if "embedding" in node.properties:
                properties["embedding"] = node.properties["embedding"]
            
            # Merge other properties, ensuring all properties are Neo4j compatible primitive types
            for key, value in node.properties.items():
                if key != "embedding":  # Skip already processed embedding vectors
                    # Check property value type, ensure it's a Neo4j-supported primitive type or array thereof
                    if isinstance(value, (str, int, float, bool)) or (
                        isinstance(value, list) and all(isinstance(item, (int, float)) for item in value)
                    ):
                        properties[key] = value
                    else:
                        # If not a primitive type, try to use JSON serialization
                        try:
                            properties[key] = json.dumps(value)
                        except (TypeError, ValueError) as e:
                            logger.warning(f"Could not serialize property {key}, skipping: {e}")
            
            # Add node labels
            labels = ["Base", node.node_type]
            
            neo4j_nodes.append({
                "labels": labels,
                "properties": properties
            })
        
        return neo4j_nodes
    
    def _convert_relations_to_neo4j_format(self, relations: List[Any]) -> List[Dict[str, Any]]:
        """Convert relationships to Neo4j bulk import format
        
        Args:
            relations: Relationship list
            
        Returns:
            List of relationships in Neo4j format
        """
        neo4j_relations = []
        
        for relation in relations:
            # Ensure properties are Neo4j compatible
            processed_properties = {}
            
            for key, value in relation.properties.items():
                # Check property value type, ensure it's a Neo4j-supported primitive type or array thereof
                if isinstance(value, (str, int, float, bool)) or (
                    isinstance(value, list) and all(isinstance(item, (int, float)) for item in value)
                ):
                    processed_properties[key] = value
                else:
                    # If not a primitive type, try to use JSON serialization
                    try:
                        processed_properties[key] = json.dumps(value)
                    except (TypeError, ValueError) as e:
                        logger.warning(f"Could not serialize relationship property {key}, skipping: {e}")
            
            neo4j_relation = {
                "start_node_id": relation.source_id,
                "end_node_id": relation.target_id,
                "type": relation.relation_type,
                "properties": processed_properties
            }
            
            neo4j_relations.append(neo4j_relation)
        
        return neo4j_relations
    
    def close(self) -> None:
        """Close resources (database connections, etc.)"""
        self.db.close()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Codebase Knowledge Graph Creation Tool")
    parser.add_argument("--codebase-path", required=True, help="Codebase path")
    parser.add_argument("--clear-db", action="store_true", help="Clear database")
    parser.add_argument("--neo4j-uri", help="Neo4j database URI")
    parser.add_argument("--neo4j-user", help="Neo4j username")
    parser.add_argument("--neo4j-password", help="Neo4j password")
    parser.add_argument("--openai-api-key", help="OpenAI API key")
    parser.add_argument("--start-mcp-server", action="store_true", help="Start MCP server after building knowledge graph")
    parser.add_argument("--mcp-transport", choices=["stdio", "sse"], default="stdio", help="MCP transport protocol")
    parser.add_argument("--mcp-port", type=int, default=8080, help="MCP server port number (only for SSE transport)")
    
    args = parser.parse_args()
    # --- AST-grep integration feature flags ---
    use_ast_grep = os.getenv("USE_AST_GREP", "false").lower() == "true"
    ast_grep_languages = os.getenv("AST_GREP_LANGUAGES", "python,javascript,typescript").split(',')
    ast_grep_fallback = os.getenv("AST_GREP_FALLBACK_TO_LEGACY", "true").lower() == "true"
    logger.info(f"USE_AST_GREP={use_ast_grep}, AST_GREP_LANGUAGES={ast_grep_languages}, AST_GREP_FALLBACK_TO_LEGACY={ast_grep_fallback}")
    
    # Create knowledge graph
    kg = CodebaseKnowledgeGraph(
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password,
        openai_api_key=args.openai_api_key
    )
    
    try:
        # Process codebase
        num_nodes, num_relations = kg.process_codebase(
            codebase_path=args.codebase_path,
            clear_db=args.clear_db
        )
        
        logger.info(f"Successfully processed codebase, imported {num_nodes} nodes and {num_relations} relationships")
        
        # Start MCP server (if needed)
        if args.start_mcp_server:
            logger.info("Starting MCP server...")
            
            # Import MCP server module
            from src.mcp.server import CodebaseKnowledgeGraphMCP
            
            # Create and start MCP server
            server = CodebaseKnowledgeGraphMCP(
                neo4j_uri=args.neo4j_uri,
                neo4j_user=args.neo4j_user,
                neo4j_password=args.neo4j_password,
                openai_api_key=args.openai_api_key
            )
            
            server.start(port=args.mcp_port, transport=args.mcp_transport)
    finally:
        # Close resources
        kg.close()


if __name__ == "__main__":
    main()