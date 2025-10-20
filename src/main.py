import os
import argparse
import logging
import time
from typing import Dict, List, Any, Tuple, Optional
from dotenv import load_dotenv
import json
from concurrent.futures import as_completed

from src.ast_parser.parser import ASTParser
from src.ast_parser.multi_parser import MultiLanguageParser
from src.embeddings.factory import get_embedding_provider
from src.embeddings.embedder import CodeEmbedder, OpenAIEmbeddings
from src.neo4j_storage.graph_db import Neo4jDatabase
from src.parallel.pool_manager import get_processing_pool
from src.utils.runtime_detection import log_runtime_info

load_dotenv()

# 設置日誌
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CodebaseKnowledgeGraph:
    """Codebase知識圖譜的創建與管理類"""
    # Class for creating and managing the codebase knowledge graph
    
    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        """初始化Codebase知識圖譜
        # Initialize the Codebase Knowledge Graph
        
        Args:
            neo4j_uri: Neo4j資料庫URI，若為None則從環境變數取得
            # neo4j_uri: Neo4j database URI, if None, get from environment variables
            neo4j_user: Neo4j使用者名稱，若為None則從環境變數取得
            # neo4j_user: Neo4j username, if None, get from environment variables
            neo4j_password: Neo4j密碼，若為None則從環境變數取得
            # neo4j_password: Neo4j password, if None, get from environment variables
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
        
        # 初始化程式碼解析器
        # Initialize code parser
        self.parser = ASTParser()
        
        # Store ast-grep feature flags for use in parsing methods
        # 儲存 ast-grep 功能標誌供解析方法使用
        self.use_ast_grep = os.getenv("USE_AST_GREP", "false").lower() == "true"
        self.ast_grep_languages = os.getenv("AST_GREP_LANGUAGES", "python,javascript,typescript").split(',')
        self.ast_grep_fallback = os.getenv("AST_GREP_FALLBACK_TO_LEGACY", "true").lower() == "true"
        
        # 初始化嵌入處理器
        # If an explicit API key is provided prefer the wrapper, otherwise use the factory
        if openai_api_key:
            self.embedder = OpenAIEmbeddings(api_key=openai_api_key)
        else:
            self.embedder = get_embedding_provider()

        self.code_embedder = CodeEmbedder(self.embedder)
    
    def _validate_configuration(self) -> None:
        """驗證配置參數
        # Validate configuration parameters
        """
        # Validate MAX_WORKERS
        max_workers_str = os.getenv("MAX_WORKERS", "")
        if max_workers_str:
            try:
                max_workers = int(max_workers_str)
                if max_workers <= 0:
                    logger.warning(f"MAX_WORKERS 必須大於 0，當前值: {max_workers}. 將使用默認值")
                    # MAX_WORKERS must be greater than 0, current value: {max_workers}. Will use default
                elif max_workers > 128:
                    logger.warning(f"MAX_WORKERS 過大 ({max_workers}). 建議使用 <= 128. 可能導致資源耗盡")
                    # MAX_WORKERS too large ({max_workers}). Recommend <= 128. May cause resource exhaustion
            except ValueError:
                logger.warning(f"MAX_WORKERS 值無效: '{max_workers_str}'. 將使用默認值")
                # Invalid MAX_WORKERS value: '{max_workers_str}'. Will use default
        
        # Validate NEO4J_MAX_CONNECTION_POOL_SIZE
        from src.utils.runtime_detection import get_optimal_worker_count
        optimal_workers = get_optimal_worker_count()
        
        pool_size_str = os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", "")
        if pool_size_str:
            try:
                pool_size = int(pool_size_str)
                if pool_size < optimal_workers:
                    logger.warning(
                        f"NEO4J_MAX_CONNECTION_POOL_SIZE ({pool_size}) 小於 MAX_WORKERS ({optimal_workers}). "
                        f"建議設置為至少 {optimal_workers * 2} 以避免連接池耗盡"
                    )
                    # NEO4J_MAX_CONNECTION_POOL_SIZE ({pool_size}) less than MAX_WORKERS ({optimal_workers}).
                    # Recommend setting to at least {optimal_workers * 2} to avoid connection pool exhaustion
            except ValueError:
                logger.warning(f"NEO4J_MAX_CONNECTION_POOL_SIZE 值無效: '{pool_size_str}'")
                # Invalid NEO4J_MAX_CONNECTION_POOL_SIZE value: '{pool_size_str}'
        
        # Validate MIN_FILES_FOR_PARALLEL
        min_files_str = os.getenv("MIN_FILES_FOR_PARALLEL", "")
        if min_files_str:
            try:
                min_files = int(min_files_str)
                if min_files < 1:
                    logger.warning(f"MIN_FILES_FOR_PARALLEL 必須至少為 1，當前值: {min_files}")
                    # MIN_FILES_FOR_PARALLEL must be at least 1, current value: {min_files}
                elif min_files < 10:
                    logger.info(f"MIN_FILES_FOR_PARALLEL ({min_files}) 較小. 並行處理可能不會帶來性能提升")
                    # MIN_FILES_FOR_PARALLEL ({min_files}) is small. Parallel processing may not bring performance gains
            except ValueError:
                logger.warning(f"MIN_FILES_FOR_PARALLEL 值無效: '{min_files_str}'")
                # Invalid MIN_FILES_FOR_PARALLEL value: '{min_files_str}'
    
    def _get_neo4j_pool_size(self) -> int:
        """獲取 Neo4j 連接池大小
        # Get Neo4j connection pool size
        
        Returns:
            連接池大小
            # Connection pool size
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
        logger.info(f"使用默認 Neo4j 連接池大小: {default_size}")
        # Using default Neo4j connection pool size: {default_size}
        return default_size
    
    def process_codebase(self, codebase_path: str, clear_db: bool = False) -> Tuple[int, int]:
        """處理整個程式碼庫，解析並匯入知識圖譜
        # Process the entire codebase, parse and import into the knowledge graph
        
        Args:
            codebase_path: 程式碼庫的目錄路徑
            # codebase_path: Directory path of the codebase
            clear_db: 是否清空資料庫
            # clear_db: Whether to clear the database
            
        Returns:
            處理的節點數量和關係數量
            # Number of nodes and relationships processed
        """
        start_time = time.time()
        logger.info(f"開始處理程式碼庫: {codebase_path}")
        # Start processing codebase
        
        # Log runtime information (GIL status, Python version, etc.)
        log_runtime_info()
        
        # 驗證資料庫連接
        # Verify database connection
        if not self.db.verify_connection():
            raise ConnectionError("無法連接到Neo4j資料庫，請檢查連接設定")
        
        # 清空資料庫（如果需要）
        # Clear the database (if needed)
        if clear_db:
            logger.info("清空資料庫...")
            self.db.clear_database()
        
        # 建立資料庫結構
        # Create database schema
        logger.info("創建資料庫結構...")
        self.db.create_schema_constraints()
        
        # Collect all source files (Python, JS, TS)
        source_files = self._collect_source_files(codebase_path)
        logger.info(f"找到 {len(source_files)} 個源代碼檔案")
        # Found {len(source_files)} source files
        
        # Get configuration for parallel processing
        parallel_enabled = os.getenv("PARALLEL_INDEXING_ENABLED", "true").lower() == "true"
        min_files_for_parallel = int(os.getenv("MIN_FILES_FOR_PARALLEL", "50"))
        
        # Determine if we should use parallel processing
        use_parallel = parallel_enabled and len(source_files) >= min_files_for_parallel
        
        if use_parallel:
            logger.info(f"使用並行處理模式處理 {len(source_files)} 個檔案")
            # Use parallel processing mode to process {len(source_files)} files
            nodes, relations = self._process_files_parallel(source_files, codebase_path)
        else:
            logger.info(f"使用順序處理模式處理 {len(source_files)} 個檔案")
            # Use sequential processing mode to process {len(source_files)} files
            # For sequential mode, we still need to use the router
            nodes, relations = self._process_directory_with_routing(codebase_path)
        
        logger.info(f"共解析出 {len(nodes)} 個節點和 {len(relations)} 個關係")
        # Total {len(nodes)} nodes and {len(relations)} relationships parsed
        
        # 為節點生成嵌入向量
        # Generate embedding vectors for nodes
        logger.info("為節點生成嵌入向量...")
        self._generate_embeddings(nodes)
        
        # 將節點轉換為Neo4j格式並匯入資料庫
        # Convert nodes to Neo4j format and import into the database
        logger.info("將節點匯入資料庫...")
        neo4j_nodes = self._convert_nodes_to_neo4j_format(nodes)
        self.db.batch_create_nodes(neo4j_nodes)
        
        # 將關係轉換為Neo4j格式並匯入資料庫
        # Convert relationships to Neo4j format and import into the database
        logger.info("將關係匯入資料庫...")
        neo4j_relations = self._convert_relations_to_neo4j_format(relations)
        self.db.batch_create_relationships(neo4j_relations)
        
        # 創建向量索引（用於相似度搜索）
        # Create vector index (for similarity search)
        logger.info("創建向量索引...")
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
                    logger.warning(f"創建 {node_label} 向量索引時出現警告: {e}")
                    # Warning when creating {node_label} vector index: {e}
        except Exception as e:
            logger.error(f"創建向量索引時發生錯誤: {e}")
            # Error creating vector index: {e}
        
        # 創建全文檢索索引
        # Create full-text search index
        logger.info("創建全文檢索索引...")
        try:
            self.db.create_full_text_index(
                index_name="code_index",
                node_labels=["Function", "Method", "Class", "File"],
                properties=["name", "code_snippet"]
            )
        except Exception as e:
            logger.error(f"創建全文檢索索引時發生錯誤: {e}")
            # Error creating full-text search index: {e}
        
        elapsed_time = time.time() - start_time
        logger.info(f"程式碼庫處理完成！耗時: {elapsed_time:.2f} 秒 (並行模式: {use_parallel})")
        # Codebase processing complete! Time taken: {elapsed_time:.2f} seconds (Parallel mode: {use_parallel})
        return len(nodes), len(relations)
    
    def _collect_source_files(self, directory_path: str) -> List[str]:
        """收集目錄中的所有源代碼檔案 (支持 7 種語言)
        # Collect all source code files in the directory (supports 7 languages)
        
        Args:
            directory_path: 目錄路徑
            # directory_path: Directory path
            
        Returns:
            源代碼檔案路徑列表
            # List of source code file paths
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
            
            logger.info(f"ast-grep 模式已啟用語言: {', '.join(self.ast_grep_languages)}")
            # ast-grep mode enabled languages: ...
        else:
            # Legacy mode: only Python and optionally JS/TS
            enable_js_ts = os.getenv("ENABLE_JS_TS_PARSING", "true").lower() == "true"
            python_extensions = (".py",)
            js_ts_extensions = (".js", ".ts", ".jsx", ".tsx") if enable_js_ts else ()
            supported_extensions = python_extensions + js_ts_extensions
            
            if enable_js_ts:
                logger.info("已啟用多語言支持: Python, JavaScript, TypeScript")
                # Multi-language support enabled: Python, JavaScript, TypeScript
            else:
                logger.info("僅啟用 Python 支持")
                # Only Python support enabled
        
        for root, _, files in os.walk(directory_path):
            for file_name in files:
                if file_name.endswith(supported_extensions):
                    file_path = os.path.join(root, file_name)
                    source_files.append(file_path)
        
        return source_files
    
    def _get_parser_for_file(self, file_path: str):
        """根據檔案副檔名選擇適當的解析器
        # Select the appropriate parser based on file extension
        
        Args:
            file_path: 檔案路徑
            # file_path: File path
            
        Returns:
            解析器實例 (ASTParser, TypeScriptParser, 或 MultiLanguageParser)，如果不支持則返回 None
            # Parser instance (ASTParser, TypeScriptParser, or MultiLanguageParser), None if unsupported
        """
        # When USE_AST_GREP is enabled, use MultiLanguageParser coordinator
        # 當啟用 USE_AST_GREP 時，使用 MultiLanguageParser 協調器
        if self.use_ast_grep:
            return MultiLanguageParser(
                use_ast_grep=True,
                ast_grep_languages=self.ast_grep_languages,
                ast_grep_fallback=self.ast_grep_fallback
            )
        
        # Otherwise, use legacy routing
        # 否則，使用傳統路由
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.py':
            from src.ast_parser.parser import ASTParser
            return ASTParser()
        elif ext in ['.js', '.ts', '.jsx', '.tsx']:
            from src.ast_parser.typescript_parser import TypeScriptParser
            return TypeScriptParser()
        else:
            logger.warning(f"不支持的檔案副檔名: {ext} ({file_path})")
            # Unsupported file extension: {ext} ({file_path})
            return None
    
    def _process_directory_with_routing(self, directory_path: str) -> Tuple[Dict[str, Any], List[Any]]:
        """使用解析器路由處理目錄（順序模式）
        # Process directory with parser routing (sequential mode)
        
        Args:
            directory_path: 目錄路徑
            # directory_path: Directory path
            
        Returns:
            節點字典和關係列表
            # Node dictionary and relationship list
        """
        # When USE_AST_GREP is enabled, use MultiLanguageParser for coordinated parsing
        # 當啟用 USE_AST_GREP 時，使用 MultiLanguageParser 進行協調解析
        if self.use_ast_grep:
            coordinator = MultiLanguageParser(
                use_ast_grep=True,
                ast_grep_languages=self.ast_grep_languages,
                ast_grep_fallback=self.ast_grep_fallback
            )
            return coordinator.parse_directory(directory_path, build_index=True)
        
        # Legacy routing (USE_AST_GREP=false)
        # 傳統路由 (USE_AST_GREP=false)
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
                logger.error(f"解析檔案 {file_path} 時發生錯誤: {e}")
                # Error parsing file {file_path}: {e}
        
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
        """使用並行處理模式處理源代碼檔案（支持多語言）
        # Process source files using parallel processing mode (multi-language support)
        
        Args:
            source_files: 源代碼檔案路徑列表
            # source_files: List of source file paths
            codebase_path: 程式碼庫目錄路徑
            # codebase_path: Codebase directory path
            
        Returns:
            節點字典和關係列表
            # Node dictionary and relationship list
        """
        from src.ast_parser.parser import ASTParser
        from src.ast_parser.typescript_parser import TypeScriptParser
        
        try:
            # First pass: Parse all files in parallel to build module definition index
            logger.info("第一遍: 並行解析所有檔案...")
            # First pass: Parse all files in parallel...
            
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
                    # 當啟用 USE_AST_GREP 時，使用 MultiLanguageParser
                    if self.use_ast_grep:
                        parser = MultiLanguageParser(
                            use_ast_grep=True,
                            ast_grep_languages=self.ast_grep_languages,
                            ast_grep_fallback=self.ast_grep_fallback
                        )
                    else:
                        # Legacy routing: Select parser based on file extension
                        # 傳統路由：根據檔案副檔名選擇解析器
                        ext = os.path.splitext(file_path)[1].lower()
                        
                        if ext == '.py':
                            parser = ASTParser()
                        elif ext in ['.js', '.ts', '.jsx', '.tsx']:
                            parser = TypeScriptParser()
                        else:
                            logger.warning(f"不支持的檔案副檔名: {ext} ({file_path})")
                            return ({}, {}, [], {})
                    
                    parser.parse_file(file_path, build_index=True)
                    
                    return (
                        dict(parser.nodes),
                        dict(parser.module_definitions),
                        list(parser.pending_imports),
                        dict(parser.module_to_file)
                    )
                except Exception as e:
                    logger.error(f"解析檔案 {file_path} 時發生錯誤: {e}")
                    # Error parsing file {file_path}: {e}
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
                            logger.info(f"已完成 {completed}/{len(source_files)} 個檔案")
                            # Completed {completed}/{len(source_files)} files
                    except Exception as e:
                        logger.error(f"處理檔案結果時發生錯誤: {e}")
                        # Error processing file result: {e}
            
            logger.info(f"第一遍完成: 解析了 {len(all_nodes)} 個節點")
            # First pass complete: Parsed {len(all_nodes)} nodes
            
            # Second pass: Process pending imports sequentially
            # This must be sequential because it requires the complete module definition index
            logger.info("第二遍: 處理待處理的導入關係...")
            # Second pass: Process pending imports...
            
            # Create a parser with the aggregated data to process imports
            final_parser = ASTParser()
            final_parser.nodes = all_nodes
            final_parser.module_definitions = all_module_definitions
            final_parser.pending_imports = all_pending_imports
            final_parser.module_to_file = all_module_to_file
            
            # Process all pending imports
            final_parser._process_pending_imports()
            
            logger.info(f"第二遍完成: 處理了 {len(final_parser.relations)} 個關係")
            # Second pass complete: Processed {len(final_parser.relations)} relationships
            
            return final_parser.nodes, final_parser.relations
            
        except Exception as e:
            # Graceful degradation: Fall back to sequential processing
            logger.error(f"並行處理失敗: {e}")
            # Parallel processing failed: {e}
            logger.warning("回退到順序處理模式...")
            # Falling back to sequential processing mode...
            
            # Log detailed error for debugging
            import traceback
            logger.debug(f"並行處理錯誤詳情:\n{traceback.format_exc()}")
            # Parallel processing error details
            
            # Use sequential processing with routing
            return self._process_directory_with_routing(codebase_path)
    
    def _generate_embeddings(self, nodes: Dict[str, Any]) -> None:
        """為節點生成嵌入向量
        # Generate embedding vectors for nodes
        
        Args:
            nodes: 節點字典
            # nodes: Node dictionary
        """
        batch_size = 20  # 批次大小，避免API限制
        # Batch size to avoid API limits
        
        # 僅為特定類型的節點生成嵌入
        target_types = ["Function", "Method", "Class", "File"]
        
        nodes_to_embed = [
            (node_id, node) for node_id, node in nodes.items()
            if node.node_type in target_types
        ]
        
        for i in range(0, len(nodes_to_embed), batch_size):
            batch = nodes_to_embed[i:i+batch_size]
            
            # 重置批次資料
            # Reset batch data
            code_texts = []
            node_types = []
            names = []
            node_ids = []
            
            # 收集批次資料
            # Collect batch data
            for node_id, node in batch:
                # 對於檔案類型，使用檔案名稱作為代碼文本
            # For file types, use the file name as the code text
                if node.node_type == "File":
                    code_text = f"File: {node.name}"
                else:
                    code_text = node.code_snippet or f"{node.node_type}: {node.name}"
                
                code_texts.append(code_text)
                node_types.append(node.node_type)
                names.append(node.name)
                node_ids.append(node_id)
            
            # 只在有資料要處理時才進行嵌入向量生成
            # Only generate embeddings if there is data to process
            if code_texts:
                # 批次生成嵌入向量
                # Batch generate embedding vectors
                embeddings = self.code_embedder.embed_code_nodes_batch(
                    code_texts=code_texts,
                    node_types=node_types,
                    names=names
                )
                
                # 確保嵌入向量與節點列表長度匹配
                # Ensure embedding vector matches node list length
                if len(embeddings) >= len(node_ids):
                    # 將嵌入向量添加到節點
                    # Add embedding vector to node
                    for i, node_id in enumerate(node_ids):
                        nodes[node_id].properties["embedding"] = embeddings[i]
                    
                    logger.debug(f"已生成 {len(batch)} 個節點的嵌入向量")
                    # Generated {len(batch)} node embeddings
                else:
                    # 處理嵌入向量數量不足的情況
                    # Handle cases where the number of embedding vectors is insufficient
                    logger.warning(f"嵌入向量數量({len(embeddings)})小於節點數量({len(node_ids)})，使用零向量代替")
                    for i, node_id in enumerate(node_ids):
                        if i < len(embeddings):
                            nodes[node_id].properties["embedding"] = embeddings[i]
                        else:
                            # 使用零向量代替
                            # Use zero vectors as a substitute
                            nodes[node_id].properties["embedding"] = [0.0] * getattr(self.embedder, 'dimension', 1536)
    
    def _convert_nodes_to_neo4j_format(self, nodes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """將節點轉換為Neo4j批量匯入的格式
        # Convert nodes to Neo4j bulk import format
        
        Args:
            nodes: 節點字典
            # nodes: Node dictionary
            
        Returns:
            Neo4j格式的節點列表
            # List of nodes in Neo4j format
        """
        neo4j_nodes = []
        
        for node_id, node in nodes.items():
            # 創建基本屬性
            # Create basic properties
            properties = {
                "id": node_id,
                "name": node.name,
                "file_path": node.file_path,
                "line_no": node.line_no
            }
            
            # 添加節點類型特定的屬性
            # Add node type specific properties
            if node.end_line_no:
                properties["end_line_no"] = node.end_line_no
            
            if node.code_snippet:
                properties["code_snippet"] = node.code_snippet
            
            # 添加嵌入向量（如果有）
            # Add embedding vector (if any)
            if "embedding" in node.properties:
                properties["embedding"] = node.properties["embedding"]
            
            # 合併其他屬性，確保所有屬性都是Neo4j兼容的原始類型
            # Merge other properties, ensuring all properties are Neo4j compatible primitive types
            for key, value in node.properties.items():
                if key != "embedding":  # 跳過已處理的嵌入向量
                    # Skip already processed embedding vectors
                    # 檢查屬性值類型，確保是Neo4j支持的原始類型或其數組
                    # Check property value type, ensure it's a Neo4j-supported primitive type or array thereof
                    if isinstance(value, (str, int, float, bool)) or (
                        isinstance(value, list) and all(isinstance(item, (int, float)) for item in value)
                    ):
                        properties[key] = value
                    else:
                        # 如果不是原始類型，嘗試使用JSON序列化
                        # If not a primitive type, try to use JSON serialization
                        try:
                            properties[key] = json.dumps(value)
                        except (TypeError, ValueError) as e:
                            logger.warning(f"無法序列化屬性 {key}，跳過: {e}")
                            # Could not serialize property {key}, skipping: {e}
            
            # 添加節點標籤
            # Add node labels
            labels = ["Base", node.node_type]
            
            neo4j_nodes.append({
                "labels": labels,
                "properties": properties
            })
        
        return neo4j_nodes
    
    def _convert_relations_to_neo4j_format(self, relations: List[Any]) -> List[Dict[str, Any]]:
        """將關係轉換為Neo4j批量匯入的格式
        
        Args:
            relations: 關係列表
            
        Returns:
            Neo4j格式的關係列表
        """
        neo4j_relations = []
        
        for relation in relations:
            # 確保屬性是Neo4j兼容的
            processed_properties = {}
            
            for key, value in relation.properties.items():
                # 檢查屬性值類型，確保是Neo4j支持的原始類型或其數組
                if isinstance(value, (str, int, float, bool)) or (
                    isinstance(value, list) and all(isinstance(item, (int, float)) for item in value)
                ):
                    processed_properties[key] = value
                else:
                    # 如果不是原始類型，嘗試使用JSON序列化
                    try:
                        processed_properties[key] = json.dumps(value)
                    except (TypeError, ValueError) as e:
                        logger.warning(f"無法序列化關係屬性 {key}，跳過: {e}")
            
            neo4j_relation = {
                "start_node_id": relation.source_id,
                "end_node_id": relation.target_id,
                "type": relation.relation_type,
                "properties": processed_properties
            }
            
            neo4j_relations.append(neo4j_relation)
        
        return neo4j_relations
    
    def close(self) -> None:
        """關閉資源（資料庫連接等）"""
        self.db.close()


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="Codebase知識圖譜創建工具")
    parser.add_argument("--codebase-path", required=True, help="程式碼庫路徑")
    parser.add_argument("--clear-db", action="store_true", help="清空資料庫")
    parser.add_argument("--neo4j-uri", help="Neo4j資料庫URI")
    parser.add_argument("--neo4j-user", help="Neo4j使用者名稱")
    parser.add_argument("--neo4j-password", help="Neo4j密碼")
    parser.add_argument("--openai-api-key", help="OpenAI API金鑰")
    parser.add_argument("--start-mcp-server", action="store_true", help="建立知識圖譜後啟動MCP服務器")
    parser.add_argument("--mcp-transport", choices=["stdio", "sse"], default="stdio", help="MCP傳輸協議")
    parser.add_argument("--mcp-port", type=int, default=8080, help="MCP服務器端口號（僅用於SSE傳輸）")
    
    args = parser.parse_args()
    # --- AST-grep integration feature flags ---
    use_ast_grep = os.getenv("USE_AST_GREP", "false").lower() == "true"
    ast_grep_languages = os.getenv("AST_GREP_LANGUAGES", "python,javascript,typescript").split(',')
    ast_grep_fallback = os.getenv("AST_GREP_FALLBACK_TO_LEGACY", "true").lower() == "true"
    logger.info(f"USE_AST_GREP={use_ast_grep}, AST_GREP_LANGUAGES={ast_grep_languages}, AST_GREP_FALLBACK_TO_LEGACY={ast_grep_fallback}")
    
    # 創建知識圖譜
    kg = CodebaseKnowledgeGraph(
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password,
        openai_api_key=args.openai_api_key
    )
    
    try:
        # 處理程式碼庫
        num_nodes, num_relations = kg.process_codebase(
            codebase_path=args.codebase_path,
            clear_db=args.clear_db
        )
        
        logger.info(f"已成功處理程式碼庫，匯入 {num_nodes} 個節點和 {num_relations} 個關係")
        
        # 啟動MCP服務器（如果需要）
        if args.start_mcp_server:
            logger.info("開始啟動MCP服務器...")
            
            # 導入MCP服務器模組
            from src.mcp.server import CodebaseKnowledgeGraphMCP
            
            # 創建並啟動MCP服務器
            server = CodebaseKnowledgeGraphMCP(
                neo4j_uri=args.neo4j_uri,
                neo4j_user=args.neo4j_user,
                neo4j_password=args.neo4j_password,
                openai_api_key=args.openai_api_key
            )
            
            server.start(port=args.mcp_port, transport=args.mcp_transport)
    finally:
        # 關閉資源
        kg.close()


if __name__ == "__main__":
    main()