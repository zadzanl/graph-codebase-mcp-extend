import os
from typing import Dict, List, Any, Optional, Tuple, Set
from neo4j import GraphDatabase, Driver
import logging

# 設定日誌
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Neo4jDatabase:
    """Neo4j圖形資料庫操作類 / Neo4j graph database operations class
    Neo4j graph database operations class"""
    
    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None,
        database: str = "neo4j",
        max_connection_pool_size: Optional[int] = None,
    ):
        """初始化Neo4j資料庫連接 / Initialize Neo4j database connection
        Initialize Neo4j database connection
        
        Args:
            uri: Neo4j資料庫URI，若為None則從環境變數NEO4J_URI取得
                 / Neo4j database URI, if None get from NEO4J_URI environment variable
                 Neo4j database URI, if None get from NEO4J_URI environment variable
            user: 使用者名稱，若為None則從環境變數NEO4J_USER取得
                  / Username, if None get from NEO4J_USER environment variable
                  Username, if None get from NEO4J_USER environment variable
            password: 密碼，若為None則從環境變數NEO4J_PASSWORD取得
                     / Password, if None get from NEO4J_PASSWORD environment variable
                     Password, if None get from NEO4J_PASSWORD environment variable
            database: 資料庫名稱，預設為"neo4j"
                     / Database name, default is "neo4j"
                     Database name, default is "neo4j"
            max_connection_pool_size: 最大連線池大小，若為None則從環境變數取得或使用預設值
                                     / Max connection pool size, if None get from env or use default
                                     Max connection pool size, if None get from env or use default
        """
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "password")
        self.database = database
        
        # Configure connection pool size for parallel operations
        # 為平行操作配置連線池大小
        # Configure connection pool size for parallel operations
        if max_connection_pool_size is None:
            # Try to get from environment, otherwise calculate based on MAX_WORKERS
            env_pool_size = os.environ.get("NEO4J_MAX_CONNECTION_POOL_SIZE")
            if env_pool_size:
                try:
                    max_connection_pool_size = int(env_pool_size)
                except ValueError:
                    logger.warning(
                        f"Invalid NEO4J_MAX_CONNECTION_POOL_SIZE: {env_pool_size}, "
                        "using default calculation"
                    )
            
            if max_connection_pool_size is None:
                # Default: MAX_WORKERS * 2, or at least 16
                max_workers = int(os.environ.get("MAX_WORKERS", "8"))
                max_connection_pool_size = max(16, max_workers * 2)

        self.max_connection_pool_size = max_connection_pool_size
        self.driver = None
        self._connection_verified = False

        # Initialize connection with retry logic
        self._init_connection_with_retry()

    def _init_connection_with_retry(self, max_retries: int = 3, initial_delay: float = 1.0):
        """Initialize Neo4j connection with retry logic
        Initialize Neo4j connection with retry logic
        
        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            initial_delay: Initial delay between retries in seconds (default: 1.0)
        """
        import time

        # Log connection attempt details (without exposing password)
        logger.info(f"Initializing Neo4j connection to {self.uri} as user '{self.user}'")

        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                # Create driver with connection pool configuration
                # Driver is thread-safe and should be shared across threads
                # 創建具有連線池配置的驅動程式
                # Create driver with connection pool configuration
                # Driver 是執行緒安全的，應在執行緒之間共享
                # Driver is thread-safe and should be shared across threads
                self.driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    max_connection_pool_size=self.max_connection_pool_size,
                    connection_acquisition_timeout=30.0,  # 30 seconds timeout
                    connection_timeout=30.0,
                )

                # Verify the connection actually works
                if self.verify_connection():
                    self._connection_verified = True
                    logger.info(
                        f"已成功連接到Neo4j資料庫 / Successfully connected to Neo4j: {self.uri}"
                    )
                    logger.info(
                        f"Successfully connected to Neo4j: {self.uri}"
                    )
                    logger.info(
                        f"連線池大小 / Connection pool size: {self.max_connection_pool_size}"
                    )
                    logger.info(
                        f"Connection pool size: {self.max_connection_pool_size}"
                    )
                    # Connection successful, exit retry loop
                    return
                else:
                    # Verification failed but driver was created
                    logger.warning(f"Driver created but connection verification failed (attempt {retry_count + 1}/{max_retries + 1})")
                    last_error = Exception("Connection verification failed")

            except Exception as e:
                last_error = e
                retry_count += 1

                if retry_count <= max_retries:
                    # Calculate exponential backoff delay
                    delay = initial_delay * (2 ** (retry_count - 1))
                    logger.warning(
                        f"連接Neo4j失敗 (嘗試 {retry_count}/{max_retries + 1}): {e}"
                    )
                    logger.warning(
                        f"Failed to connect to Neo4j (attempt {retry_count}/{max_retries + 1}): {e}"
                    )
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    # Max retries exceeded
                    logger.error(f"連接Neo4j資料庫時發生錯誤 / Error connecting to Neo4j: {e}")
                    logger.error(f"Error connecting to Neo4j: {e}")

                    # Check for authentication failures and provide helpful messages.
                    error_str = str(e)
                    if "Unauthorized" in error_str or "authentication failed" in error_str.lower():
                        logger.error("")
                        logger.error("="*80)
                        logger.error("AUTHENTICATION FAILED")
                        logger.error("="*80)
                        logger.error("The provided credentials are incorrect.")
                        logger.error("")
                        logger.error("Please verify:")
                        logger.error("1. NEO4J_USER in .env file (default: 'neo4j')")
                        logger.error("2. NEO4J_PASSWORD in .env file")
                        logger.error("3. If this is a fresh install, default password is usually 'neo4j'")
                        logger.error("4. Check if you need to change password on first login")
                        logger.error("="*80)
                        logger.error("")

        # If we get here, all retries failed
        logger.error(f"Failed to connect to Neo4j after {max_retries + 1} attempts")
        # Don't raise - allow server to start but operations will fail gracefully
        self.driver = None
        self._connection_verified = False
    
    def close(self):
        """關閉資料庫連接
        Close database connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j database connection closed")

    def reconnect(self):
        """嘗試重新連接到Neo4j資料庫
        Attempt to reconnect to Neo4j database

        Returns:
            bool: True if reconnection successful, False otherwise
        """
        logger.info("Attempting to reconnect to Neo4j...")

        # Close existing connection if any
        if self.driver:
            try:
                self.driver.close()
            except Exception as e:
                logger.warning(f"Error closing existing driver: {e}")

        # Reset state
        self.driver = None
        self._connection_verified = False

        # Try to reconnect
        self._init_connection_with_retry(max_retries=2, initial_delay=0.5)

        return self._connection_verified

    def _ensure_driver(self):
        """Ensure driver is initialized before operations

        Raises:
            RuntimeError: If driver is not initialized
        """
        if not self.driver:
            raise RuntimeError(
                "Neo4j driver is not initialized. Database connection failed. "
                "Please check your Neo4j credentials in .env file and ensure Neo4j server is running."
            )
    
    def verify_connection(self) -> bool:
        """驗證資料庫連接是否有效 / Verify database connection is valid
        Verify database connection is valid
        
        Returns:
            連接是否有效 / Whether the connection is valid
            Whether the connection is valid
        """
        if not self.driver:
            logger.error("Cannot verify connection - driver is not initialized")
            return False

        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as n").single()
                return result and result.get("n") == 1
        except Exception as e:
            logger.error(f"驗證Neo4j連接時發生錯誤 / Error verifying Neo4j connection: {e}")
            logger.error(f"Error verifying Neo4j connection: {e}")
            return False
    
    def get_session(self):
        """
        Create a new thread-safe session for database operations.
        
        IMPORTANT FOR PARALLEL PROCESSING:
        - The Driver instance is thread-safe and should be shared across threads
        - Session instances are NOT thread-safe and must not be shared
        - Each worker thread/process must create its own session
        - Always use sessions within a context manager (with statement)
        
        重要提示（用於平行處理）:
        Important notes (for parallel processing):
        - Driver 實例是執行緒安全的，應在執行緒之間共享
        - The Driver instance is thread-safe and should be shared across threads
        - Session 實例不是執行緒安全的，不得共享
        - Session instances are NOT thread-safe and must not be shared
        - 每個工作執行緒/程序必須創建自己的 session
        - Each worker thread/process must create its own session
        - 始終在上下文管理器（with 語句）中使用 session
        - Always use sessions within a context manager (with statement)
        
        Returns:
            A new Neo4j session (use with context manager)
        
        Example:
            >>> db = Neo4jDatabase()
            >>> with db.get_session() as session:
            ...     session.run("CREATE (n:Node {id: $id})", id=1)
        """
        if not self.driver:
            raise RuntimeError("Cannot create session - Neo4j driver is not initialized. Please check connection credentials.")
        return self.driver.session(database=self.database)
    
    def clear_database(self):
        """清空資料庫中的所有節點和關係
        Clear all nodes and relationships in the database"""
        self._ensure_driver()
        try:
            with self.driver.session(database=self.database) as session:
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("已清空資料庫")
                logger.info("Database cleared")
        except Exception as e:
            logger.error(f"清空資料庫時發生錯誤: {e}")
            logger.error(f"Error clearing database: {e}")
            raise
    
    def create_schema_constraints(self):
        """創建圖形模型的約束和索引
        Create constraints and indexes for the graph model"""
        self._ensure_driver()
        try:
            with self.driver.session(database=self.database) as session:
                # 檢查是否已存在約束
                # Check if constraints already exist
                existing_constraints = session.run(
                    "SHOW CONSTRAINTS"
                ).data()
                
                # 檢查特定約束是否存在
                # Check if specific constraint exists
                constraint_exists = False
                for constraint in existing_constraints:
                    if 'name' in constraint and "file_path_constraint" in constraint['name']:
                        constraint_exists = True
                        break
                
                # 只有在約束不存在時才創建
                # Only create constraint if it doesn't exist
                if not constraint_exists:
                    try:
                        session.run(
                            """
                            CREATE CONSTRAINT file_path_constraint
                            FOR (f:File) REQUIRE f.path IS UNIQUE
                            """
                        )
                        logger.info("已創建 File.path 唯一性約束")
                        logger.info("Created File.path uniqueness constraint")
                    except Exception as constraint_error:
                        logger.warning(f"創建約束時出現警告: {constraint_error}")
                        logger.warning(f"Warning when creating constraint: {constraint_error}")
                
                # 檢查索引是否已存在
                # Check if indexes already exist
                existing_indexes = session.run("SHOW INDEXES").data()
                index_names = [idx.get('name', '') for idx in existing_indexes if 'name' in idx]
                
                # 為節點建立索引 (不使用 IF NOT EXISTS 語法)
                # Create indexes for nodes (without using IF NOT EXISTS syntax)
                index_configs = [
                    {"name": "file_name_idx", "label": "File", "property": "name"},
                    {"name": "class_name_idx", "label": "Class", "property": "name"},
                    {"name": "function_name_idx", "label": "Function", "property": "name"},
                    {"name": "method_name_idx", "label": "Method", "property": "name"},
                    {"name": "variable_name_idx", "label": "Variable", "property": "name"},
                    {"name": "module_name_idx", "label": "Module", "property": "name"}
                ]
                
                for config in index_configs:
                    if config["name"] not in index_names:
                        try:
                            session.run(
                                f"CREATE INDEX {config['name']} FOR (n:{config['label']}) ON (n.{config['property']})"
                            )
                            logger.info(f"已創建索引: {config['name']}")
                            logger.info(f"Created index: {config['name']}")
                        except Exception as index_error:
                            logger.warning(f"創建索引 {config['name']} 時出現警告: {index_error}")
                            logger.warning(f"Warning when creating index {config['name']}: {index_error}")
                
                logger.info("已完成圖形模型的約束和索引檢查與創建")
                logger.info("Completed checking and creating constraints and indexes for graph model")
        except Exception as e:
            logger.error(f"創建約束和索引時發生錯誤: {e}")
            logger.error(f"Error creating constraints and indexes: {e}")
            raise
    
    def create_vector_index(self, index_name: str, node_label: str, property_name: str, dimension: int = 1536):
        """創建向量索引用於相似度搜索
        Create vector index for similarity search
        
        Args:
            index_name: 索引名稱
                       Index name
            node_label: 節點標籤
                       Node label
            property_name: 屬性名稱（向量存儲的屬性）
                          Property name (property where vectors are stored)
            dimension: 向量維度，預設為1536
                      Vector dimension, default is 1536
        """
        self._ensure_driver()
        try:
            with self.driver.session(database=self.database) as session:
                # 檢查索引是否已存在，使用 data() 方法獲取完整的索引信息
                # Check if index already exists, use data() method to get complete index information
                existing_indexes = session.run(
                    "SHOW INDEXES"
                ).data()
                
                # 檢查索引是否已存在
                # Check if index already exists
                index_exists = False
                for idx in existing_indexes:
                    if 'name' in idx and idx['name'] == index_name:
                        index_exists = True
                        break
                
                if not index_exists:
                    try:
                        session.run(
                            f"""
                            CREATE VECTOR INDEX {index_name}
                            FOR (n:{node_label}) ON (n.{property_name})
                            OPTIONS {{indexConfig: {{
                                `vector.dimensions`: {dimension},
                                `vector.similarity_function`: 'cosine'
                            }}}}
                            """
                        )
                        logger.info(f"已創建向量索引: {index_name}")
                        logger.info(f"Created vector index: {index_name}")
                    except Exception as idx_error:
                        # 檢查是否是因為索引已存在的錯誤
                        # Check if error is because index already exists
                        if "equivalent index already exists" in str(idx_error).lower():
                            logger.info(f"向量索引已存在 (在創建過程中檢測到): {index_name}")
                            logger.info(f"Vector index already exists (detected during creation): {index_name}")
                        else:
                            # 如果是其他錯誤，則重新拋出
                            # If it's another error, re-raise it
                            raise
                else:
                    logger.info(f"向量索引已存在: {index_name}")
                    logger.info(f"Vector index already exists: {index_name}")
        except Exception as e:
            logger.error(f"創建向量索引時發生錯誤: {e}")
            logger.error(f"Error creating vector index: {e}")
            raise
    
    def batch_create_nodes(self, nodes: List[Dict[str, Any]]):
        """批量創建節點
        Batch create nodes
        
        Args:
            nodes: 節點列表，每個節點為一個字典，包含標籤和屬性
                  格式: [{'labels': ['Label1', 'Label2'], 'properties': {...}}]
                  Node list, each node is a dictionary containing labels and properties
                  Format: [{'labels': ['Label1', 'Label2'], 'properties': {...}}]
        """
        if not nodes:
            return
        
        self._ensure_driver()
        try:
            with self.driver.session(database=self.database) as session:
                batch_size = 1000  # 設定適當的批次大小
                                   # Set appropriate batch size
                
                for i in range(0, len(nodes), batch_size):
                    batch = nodes[i:i+batch_size]
                    created = 0
                    
                    # 對每個節點單獨處理
                    # Process each node individually
                    for node in batch:
                        labels = node['labels']
                        properties = node['properties']
                        
                        # 構建標籤字串，例如 `:Label1:Label2`
                        # Build label string, e.g., `:Label1:Label2`
                        labels_str = ''.join([f":{label}" for label in labels])
                        
                        # 構建屬性字串，例如 `{id: 'test1', name: 'Test 1'}`
                        # Build property string, e.g., `{id: 'test1', name: 'Test 1'}`
                        props_str = "{"
                        props_str += ", ".join([f"{k}: ${k}" for k in properties.keys()])
                        props_str += "}"
                        
                        # 創建節點查詢
                        # Create node query
                        query = f"""
                        CREATE (n{labels_str} {props_str})
                        RETURN n
                        """
                        
                        # 執行查詢
                        # Execute query
                        session.run(query, properties)
                        created += 1
                    
                    logger.info(f"已創建 {created} 個節點")
                    logger.info(f"Created {created} nodes")
        except Exception as e:
            logger.error(f"批量創建節點時發生錯誤: {e}")
            logger.error(f"Error batch creating nodes: {e}")
            raise
    
    def batch_create_relationships(self, relationships: List[Dict[str, Any]]):
        """批量創建關係
        Batch create relationships

        Args:
            relationships: 關係列表，每個關係為一個字典
                          格式: [{'start_node_id': '...', 'end_node_id': '...',
                                'type': '...', 'properties': {...}}]
                          Relationship list, each relationship is a dictionary
                          Format: [{'start_node_id': '...', 'end_node_id': '...',
                                'type': '...', 'properties': {...}}]
        """
        if not relationships:
            return

        self._ensure_driver()
        try:
            with self.driver.session(database=self.database) as session:
                batch_size = 1000  # 設定適當的批次大小
                                   # Set appropriate batch size

                for i in range(0, len(relationships), batch_size):
                    batch = relationships[i:i+batch_size]
                    processed = 0

                    # 對每個關係單獨處理，避免生成動態Cypher查詢
                    # Process each relationship individually, avoid generating dynamic Cypher queries
                    for rel in batch:
                        start_id = rel['start_node_id']
                        end_id = rel['end_node_id']
                        rel_type = rel['type']
                        properties = rel['properties'] or {}

                        # 使用參數化查詢
                        # Use parameterized query
                        query = f"""
                        MATCH (start:Base {{id: $start_id}})
                        MATCH (end:Base {{id: $end_id}})
                        CREATE (start)-[r:{rel_type}]->(end)
                        SET r = $props
                        RETURN r
                        """

                        params = {
                            "start_id": start_id,
                            "end_id": end_id,
                            "props": properties
                        }

                        session.run(query, params)
                        processed += 1

                    logger.info(f"已處理 {processed} 個關係")
                    logger.info(f"Processed {processed} relationships")
        except Exception as e:
            logger.error(f"批量創建關係時發生錯誤: {e}")
            logger.error(f"Error batch creating relationships: {e}")
            raise
    
    def create_full_text_index(self, index_name: str, node_labels: List[str], properties: List[str]):
        """創建全文檢索索引
        Create full-text search index
        
        Args:
            index_name: 索引名稱
                       Index name
            node_labels: 節點標籤列表
                        Node label list
            properties: 屬性名稱列表
                       Property name list
        """
        self._ensure_driver()
        try:
            with self.driver.session(database=self.database) as session:
                # 檢查索引是否已存在
                # Check if index already exists
                existing_indexes = session.run(
                    "SHOW INDEXES"
                ).data()

                # 檢查索引是否已存在
                # Check if index already exists
                index_exists = False
                for idx in existing_indexes:
                    if 'name' in idx and idx['name'] == index_name:
                        index_exists = True
                        break
                
                if not index_exists:
                    try:
                        # 使用 Neo4j 5.x 版本的全文檢索索引語法
                        # Use Neo4j 5.x full-text search index syntax
                        # 創建一個跨多個標籤的單一索引
                        # Create a single index across multiple labels
                        labels_str = '|'.join(node_labels)
                        props_str = ', '.join([f'n.{prop}' for prop in properties])

                        session.run(
                            f"""
                            CREATE FULLTEXT INDEX {index_name}
                            FOR (n:{labels_str})
                            ON EACH [{props_str}]
                            """
                        )
                        logger.info(f"已創建全文檢索索引: {index_name}")
                        logger.info(f"Created full-text search index: {index_name}")
                    except Exception as idx_error:
                        # 檢查是否是因為索引已存在的錯誤
                        # Check if error is because index already exists
                        if "already exists" in str(idx_error).lower():
                            logger.info(f"全文檢索索引已存在 (在創建過程中檢測到): {index_name}")
                            logger.info(f"Full-text search index already exists (detected during creation): {index_name}")
                        else:
                            # 如果是其他錯誤，則重新拋出
                            # If it's another error, re-raise it
                            raise
                else:
                    logger.info(f"全文檢索索引已存在: {index_name}")
                    logger.info(f"Full-text search index already exists: {index_name}")
        except Exception as e:
            logger.error(f"創建全文檢索索引時發生錯誤: {e}")
            logger.error(f"Error creating full-text search index: {e}")
            raise
    
    def search_code_by_text(self, query: str, limit: int = 10):
        """使用全文檢索搜索程式碼
        Search code using full-text search
        
        Args:
            query: 搜索查詢
                  Search query
            limit: 返回結果的最大數量
                  Maximum number of results to return

        Returns:
            搜索結果列表
            Search result list
        """
        self._ensure_driver()
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(
                    """
                    CALL db.index.fulltext.queryNodes("code_index", $query) 
                    YIELD node, score
                    RETURN node, score
                    LIMIT $limit
                    """,
                    {"query": query, "limit": limit}
                )

                return [
                    {
                        "node": dict(record["node"]),
                        "score": record["score"]
                    }
                    for record in result
                ]
        except Exception as e:
            logger.error(f"全文檢索搜索時發生錯誤: {e}")
            logger.error(f"Error during full-text search: {e}")
            raise
    
    def search_code_by_vector(self, vector: List[float], node_label: str, limit: int = 10):
        """使用向量相似度搜索程式碼
        Search code using vector similarity
        
        Args:
            vector: 查詢向量
                   Query vector
            node_label: 要搜索的節點標籤
                       Node label to search
            limit: 返回結果的最大數量
                  Maximum number of results to return

        Returns:
            搜索結果列表
            Search result list
        """
        self._ensure_driver()
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                with self.driver.session(database=self.database) as session:
                    result = session.run(
                        f"""
                        MATCH (n:{node_label})
                        WHERE n.embedding IS NOT NULL
                        AND size(n.embedding) > 0
                        AND any(v IN n.embedding WHERE v <> 0.0)
                        WITH n, vector.similarity.cosine(n.embedding, $vector) AS score
                        ORDER BY score DESC
                        LIMIT $limit
                        RETURN n, score
                        """,
                        {"vector": vector, "limit": limit}
                    )

                    return [
                        {
                            "node": dict(record["n"]),
                            "score": record["score"]
                        }
                        for record in result
                    ]
            except Exception as e:
                retry_count += 1
                logger.warning(f"向量相似度搜索時發生錯誤 (嘗試 {retry_count}/{max_retries}): {e}")
                logger.warning(f"Error during vector similarity search (attempt {retry_count}/{max_retries}): {e}")

                if retry_count >= max_retries:
                    logger.error(f"向量相似度搜索失敗，已達最大重試次數")
                    logger.error(f"Vector similarity search failed after maximum retries")
                    raise

                # Wait a bit before retrying
                import time
                time.sleep(0.5 * retry_count)

    def get_node_relationships(
        self,
        node_id: str,
        relationship_types: Optional[List[str]] = None,
        limit: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """獲取特定節點的關係 / Get relationships for a specific node.

        Supported buckets: calls, called_by, extends, extended_by, imports, imported_by.
        Upper-case task names such as CALLS and IMPORTS_FROM are also accepted.
        Inheritance buckets (extends, extended_by) have a hard limit of 3.
        Others use the provided limit.
        """
        bucket_names = ["calls", "called_by", "extends", "extended_by", "imports", "imported_by"]
        relationships: Dict[str, List[Dict[str, Any]]] = {bucket_name: [] for bucket_name in bucket_names}

        aliases = {
            "calls": "calls",
            "call": "calls",
            "called_by": "called_by",
            "called-by": "called_by",
            "callees": "calls",
            "callers": "called_by",
            "extends": "extends",
            "extended_by": "extended_by",
            "extended-by": "extended_by",
            "imports": "imports",
            "imports_from": "imports",
            "imports-from": "imports",
            "imported_by": "imported_by",
            "imported-by": "imported_by",
        }

        if relationship_types is None:
            selected_buckets = set(bucket_names)
        else:
            selected_buckets = {
                aliases.get(str(relationship_type).strip().lower())
                for relationship_type in relationship_types
            }
            selected_buckets.discard(None)

        if not selected_buckets:
            return relationships

        try:
            normalized_limit = max(1, int(limit))
        except (TypeError, ValueError):
            normalized_limit = 5

        inheritance_limit = min(normalized_limit, 3)
        bucket_queries = {
            "calls": (
                "MATCH (n:Base {id: $node_id})-[:CALLS]->(m) RETURN m LIMIT $limit",
                normalized_limit,
            ),
            "called_by": (
                "MATCH (n:Base {id: $node_id})<-[:CALLS]-(m) RETURN m LIMIT $limit",
                normalized_limit,
            ),
            "extends": (
                "MATCH (n:Base {id: $node_id})-[:EXTENDS]->(m) RETURN m LIMIT $limit",
                inheritance_limit,
            ),
            "extended_by": (
                "MATCH (n:Base {id: $node_id})<-[:EXTENDS]-(m) RETURN m LIMIT $limit",
                inheritance_limit,
            ),
            "imports": (
                "MATCH (n:Base {id: $node_id})-[:IMPORTS_FROM]->(m) RETURN m LIMIT $limit",
                normalized_limit,
            ),
            "imported_by": (
                "MATCH (n:Base {id: $node_id})<-[:IMPORTS_FROM]-(m) RETURN m LIMIT $limit",
                normalized_limit,
            ),
        }

        def get_property(node: Any, key: str) -> Any:
            if hasattr(node, "get"):
                return node.get(key)
            if isinstance(node, dict):
                return node.get(key)
            return None

        def format_node(node: Any) -> Dict[str, Any]:
            labels = list(getattr(node, "labels", []) or [])
            node_type = next((label for label in labels if label != "Base"), None)
            node_type = node_type or get_property(node, "type") or (labels[0] if labels else "Unknown")
            return {
                "id": get_property(node, "id"),
                "name": get_property(node, "name"),
                "type": node_type,
                "file_path": get_property(node, "file_path") or get_property(node, "path"),
            }

        try:
            self._ensure_driver()
        except Exception as e:
            logger.warning(f"Cannot get relationships for node {node_id}: {e}")
            return relationships

        for bucket_name in bucket_names:
            if bucket_name not in selected_buckets:
                continue

            query, bucket_limit = bucket_queries[bucket_name]
            try:
                with self.driver.session(database=self.database) as session:
                    db_result = session.run(
                        query,
                        {"node_id": node_id, "limit": bucket_limit},
                    )
                    relationships[bucket_name] = [format_node(record["m"]) for record in db_result]
            except Exception as e:
                logger.warning(f"Error fetching relationship bucket '{bucket_name}' for node {node_id}: {e}")
                relationships[bucket_name] = []

        return relationships

    def execute_cypher(self, query: str, parameters: Dict = None):
        """執行Cypher查詢
        Execute Cypher query
        
        Args:
            query: Cypher查詢語句
                  Cypher query statement
            parameters: 查詢參數
                       Query parameters

        Returns:
            查詢結果
            Query result
        """
        self._ensure_driver()
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                with self.driver.session(database=self.database) as session:
                    result = session.run(query, parameters or {})
                    return [record.data() for record in result]
            except Exception as e:
                retry_count += 1
                logger.warning(f"執行Cypher查詢時發生錯誤 (嘗試 {retry_count}/{max_retries}): {e}")
                logger.warning(f"Error executing Cypher query (attempt {retry_count}/{max_retries}): {e}")

                if retry_count >= max_retries:
                    logger.error(f"執行Cypher查詢失敗，已達最大重試次數")
                    logger.error(f"Cypher query execution failed after maximum retries")
                    raise

                # Wait a bit before retrying
                import time
                time.sleep(0.5 * retry_count)


# 使用範例
# Usage example
if __name__ == "__main__":
    # 從環境變數中獲取連接資訊
    # Get connection information from environment variables
    db = Neo4jDatabase()
    
    try:
        # 驗證連接
        # Verify connection
        if db.verify_connection():
            print("Neo4j 連接成功!")
            print("Neo4j connection successful!")
            
            # 創建圖形模型的約束和索引
            # Create constraints and indexes for graph model
            db.create_schema_constraints()
            
            # 建立一個簡單的節點
            # Create a simple node
            with db.driver.session(database=db.database) as session:
                session.run(
                    """
                    CREATE (f:File {id: 'file:example.py', path: 'example.py', name: 'example.py'})
                    """
                )
                
                print("已創建示例節點")
                print("Created example node")
                
                # 查詢創建的節點
                # Query the created node
                result = session.run("MATCH (f:File) RETURN f.path AS path").single()
                if result:
                    print(f"查詢結果: {result['path']}")
                    print(f"Query result: {result['path']}")
    finally:
        db.close() 