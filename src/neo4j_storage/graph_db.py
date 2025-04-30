import os
from typing import Dict, List, Any, Optional, Tuple, Set
from neo4j import GraphDatabase, Driver
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Neo4jDatabase:
    """Neo4j圖形資料庫操作類"""
    
    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None,
        database: str = "neo4j"
    ):
        """初始化Neo4j資料庫連接
        
        Args:
            uri: Neo4j資料庫URI，若為None則從環境變數NEO4J_URI取得
            user: 使用者名稱，若為None則從環境變數NEO4J_USER取得
            password: 密碼，若為None則從環境變數NEO4J_PASSWORD取得
            database: 資料庫名稱，預設為"neo4j"
        """
        self.uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.environ.get("NEO4J_USER", "neo4j")
        self.password = password or os.environ.get("NEO4J_PASSWORD", "password")
        self.database = database
        self.driver = None
        
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            logger.info(f"已成功連接到Neo4j資料庫: {self.uri}")
        except Exception as e:
            logger.error(f"連接Neo4j資料庫時發生錯誤: {e}")
            raise
    
    def close(self):
        """關閉資料庫連接"""
        if self.driver:
            self.driver.close()
            logger.info("已關閉Neo4j資料庫連接")
    
    def verify_connection(self) -> bool:
        """驗證資料庫連接是否有效
        
        Returns:
            連接是否有效
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as n").single()
                return result and result.get("n") == 1
        except Exception as e:
            logger.error(f"驗證Neo4j連接時發生錯誤: {e}")
            return False
    
    def clear_database(self):
        """清空資料庫中的所有節點和關係"""
        try:
            with self.driver.session(database=self.database) as session:
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("已清空資料庫")
        except Exception as e:
            logger.error(f"清空資料庫時發生錯誤: {e}")
            raise
    
    def create_schema_constraints(self):
        """創建圖形模型的約束和索引"""
        try:
            with self.driver.session(database=self.database) as session:
                # 檢查是否已存在約束
                existing_constraints = session.run(
                    "SHOW CONSTRAINTS"
                ).data()
                
                # 檢查特定約束是否存在
                constraint_exists = False
                for constraint in existing_constraints:
                    if 'name' in constraint and "file_path_constraint" in constraint['name']:
                        constraint_exists = True
                        break
                
                # 只有在約束不存在時才創建
                if not constraint_exists:
                    try:
                        session.run(
                            """
                            CREATE CONSTRAINT file_path_constraint
                            FOR (f:File) REQUIRE f.path IS UNIQUE
                            """
                        )
                        logger.info("已創建 File.path 唯一性約束")
                    except Exception as constraint_error:
                        logger.warning(f"創建約束時出現警告: {constraint_error}")
                
                # 檢查索引是否已存在
                existing_indexes = session.run("SHOW INDEXES").data()
                index_names = [idx.get('name', '') for idx in existing_indexes if 'name' in idx]
                
                # 為節點建立索引 (不使用 IF NOT EXISTS 語法)
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
                        except Exception as index_error:
                            logger.warning(f"創建索引 {config['name']} 時出現警告: {index_error}")
                
                logger.info("已完成圖形模型的約束和索引檢查與創建")
        except Exception as e:
            logger.error(f"創建約束和索引時發生錯誤: {e}")
            raise
    
    def create_vector_index(self, index_name: str, node_label: str, property_name: str, dimension: int = 1536):
        """創建向量索引用於相似度搜索
        
        Args:
            index_name: 索引名稱
            node_label: 節點標籤
            property_name: 屬性名稱（向量存儲的屬性）
            dimension: 向量維度，預設為1536
        """
        try:
            with self.driver.session(database=self.database) as session:
                # 檢查索引是否已存在，使用 data() 方法獲取完整的索引信息
                existing_indexes = session.run(
                    "SHOW INDEXES"
                ).data()
                
                # 檢查索引是否已存在
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
                    except Exception as idx_error:
                        # 檢查是否是因為索引已存在的錯誤
                        if "equivalent index already exists" in str(idx_error).lower():
                            logger.info(f"向量索引已存在 (在創建過程中檢測到): {index_name}")
                        else:
                            # 如果是其他錯誤，則重新拋出
                            raise
                else:
                    logger.info(f"向量索引已存在: {index_name}")
        except Exception as e:
            logger.error(f"創建向量索引時發生錯誤: {e}")
            raise
    
    def batch_create_nodes(self, nodes: List[Dict[str, Any]]):
        """批量創建節點
        
        Args:
            nodes: 節點列表，每個節點為一個字典，包含標籤和屬性
                  格式: [{'labels': ['Label1', 'Label2'], 'properties': {...}}]
        """
        if not nodes:
            return
        
        try:
            with self.driver.session(database=self.database) as session:
                batch_size = 1000  # 設定適當的批次大小
                
                for i in range(0, len(nodes), batch_size):
                    batch = nodes[i:i+batch_size]
                    created = 0
                    
                    # 對每個節點單獨處理
                    for node in batch:
                        labels = node['labels']
                        properties = node['properties']
                        
                        # 構建標籤字串，例如 `:Label1:Label2`
                        labels_str = ''.join([f":{label}" for label in labels])
                        
                        # 構建屬性字串，例如 `{id: 'test1', name: 'Test 1'}`
                        props_str = "{"
                        props_str += ", ".join([f"{k}: ${k}" for k in properties.keys()])
                        props_str += "}"
                        
                        # 創建節點查詢
                        query = f"""
                        CREATE (n{labels_str} {props_str})
                        RETURN n
                        """
                        
                        # 執行查詢
                        session.run(query, properties)
                        created += 1
                    
                    logger.info(f"已創建 {created} 個節點")
        except Exception as e:
            logger.error(f"批量創建節點時發生錯誤: {e}")
            raise
    
    def batch_create_relationships(self, relationships: List[Dict[str, Any]]):
        """批量創建關係
        
        Args:
            relationships: 關係列表，每個關係為一個字典
                          格式: [{'start_node_id': '...', 'end_node_id': '...', 
                                'type': '...', 'properties': {...}}]
        """
        if not relationships:
            return
        
        try:
            with self.driver.session(database=self.database) as session:
                batch_size = 1000  # 設定適當的批次大小
                
                for i in range(0, len(relationships), batch_size):
                    batch = relationships[i:i+batch_size]
                    processed = 0
                    
                    # 對每個關係單獨處理，避免生成動態Cypher查詢
                    for rel in batch:
                        start_id = rel['start_node_id']
                        end_id = rel['end_node_id']
                        rel_type = rel['type']
                        properties = rel['properties'] or {}
                        
                        # 使用參數化查詢
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
        except Exception as e:
            logger.error(f"批量創建關係時發生錯誤: {e}")
            raise
    
    def create_full_text_index(self, index_name: str, node_labels: List[str], properties: List[str]):
        """創建全文檢索索引
        
        Args:
            index_name: 索引名稱
            node_labels: 節點標籤列表
            properties: 屬性名稱列表
        """
        try:
            with self.driver.session(database=self.database) as session:
                # 檢查索引是否已存在
                existing_indexes = session.run(
                    "SHOW INDEXES"
                ).data()
                
                # 檢查索引是否已存在
                index_exists = False
                for idx in existing_indexes:
                    if 'name' in idx and idx['name'] == index_name:
                        index_exists = True
                        break
                
                if not index_exists:
                    try:
                        # 使用 Neo4j 5.x 版本的全文檢索索引語法
                        # 為每個標籤創建單獨的索引
                        for label in node_labels:
                            session.run(
                                f"""
                                CREATE FULLTEXT INDEX {index_name}_{label.lower()}
                                FOR (n:{label})
                                ON EACH [{', '.join([f'n.{prop}' for prop in properties])}]
                                """
                            )
                            logger.info(f"已創建全文檢索索引: {index_name}_{label.lower()}")
                    except Exception as idx_error:
                        # 檢查是否是因為索引已存在的錯誤
                        if "already exists" in str(idx_error).lower():
                            logger.info(f"全文檢索索引已存在 (在創建過程中檢測到): {index_name}")
                        else:
                            # 如果是其他錯誤，則重新拋出
                            raise
                else:
                    logger.info(f"全文檢索索引已存在: {index_name}")
        except Exception as e:
            logger.error(f"創建全文檢索索引時發生錯誤: {e}")
            raise
    
    def search_code_by_text(self, query: str, limit: int = 10):
        """使用全文檢索搜索程式碼
        
        Args:
            query: 搜索查詢
            limit: 返回結果的最大數量
            
        Returns:
            搜索結果列表
        """
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
            raise
    
    def search_code_by_vector(self, vector: List[float], node_label: str, limit: int = 10):
        """使用向量相似度搜索程式碼
        
        Args:
            vector: 查詢向量
            node_label: 要搜索的節點標籤
            limit: 返回結果的最大數量
            
        Returns:
            搜索結果列表
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(
                    f"""
                    MATCH (n:{node_label})
                    WHERE n.embedding IS NOT NULL
                    WITH n, gds.similarity.cosine(n.embedding, $vector) AS score
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
            logger.error(f"向量相似度搜索時發生錯誤: {e}")
            raise
    
    def execute_cypher(self, query: str, parameters: Dict = None):
        """執行Cypher查詢
        
        Args:
            query: Cypher查詢語句
            parameters: 查詢參數
            
        Returns:
            查詢結果
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"執行Cypher查詢時發生錯誤: {e}")
            raise


# 使用範例
if __name__ == "__main__":
    # 從環境變數中獲取連接資訊
    db = Neo4jDatabase()
    
    try:
        # 驗證連接
        if db.verify_connection():
            print("Neo4j 連接成功!")
            
            # 創建圖形模型的約束和索引
            db.create_schema_constraints()
            
            # 建立一個簡單的節點
            with db.driver.session(database=db.database) as session:
                session.run(
                    """
                    CREATE (f:File {id: 'file:example.py', path: 'example.py', name: 'example.py'})
                    """
                )
                
                print("已創建示例節點")
                
                # 查詢創建的節點
                result = session.run("MATCH (f:File) RETURN f.path AS path").single()
                if result:
                    print(f"查詢結果: {result['path']}")
    finally:
        db.close() 