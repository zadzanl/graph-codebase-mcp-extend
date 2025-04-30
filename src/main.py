import os
import argparse
import logging
import sys
from typing import Dict, List, Any, Tuple, Optional
from dotenv import load_dotenv
import json

from ast_parser.parser import ASTParser
from embeddings.embedder import OpenAIEmbeddings, CodeEmbedder
from neo4j_storage.graph_db import Neo4jDatabase

load_dotenv()

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CodebaseKnowledgeGraph:
    """Codebase知識圖譜的創建與管理類"""
    
    def __init__(
        self,
        neo4j_uri: str = None,
        neo4j_user: str = None,
        neo4j_password: str = None,
        openai_api_key: str = None
    ):
        """初始化Codebase知識圖譜
        
        Args:
            neo4j_uri: Neo4j資料庫URI，若為None則從環境變數取得
            neo4j_user: Neo4j使用者名稱，若為None則從環境變數取得
            neo4j_password: Neo4j密碼，若為None則從環境變數取得
            openai_api_key: OpenAI API金鑰，若為None則從環境變數取得
        """
        self.neo4j_uri = neo4j_uri or os.environ.get("NEO4J_URI")
        self.neo4j_user = neo4j_user or os.environ.get("NEO4J_USER")
        self.neo4j_password = neo4j_password or os.environ.get("NEO4J_PASSWORD")
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        
        # 初始化Neo4j資料庫
        self.db = Neo4jDatabase(
            uri=self.neo4j_uri,
            user=self.neo4j_user,
            password=self.neo4j_password
        )
        
        # 初始化程式碼解析器
        self.parser = ASTParser()
        
        # 初始化嵌入處理器
        self.embedder = OpenAIEmbeddings(api_key=self.openai_api_key)
        self.code_embedder = CodeEmbedder(self.embedder)
    
    def process_codebase(self, codebase_path: str, clear_db: bool = False) -> Tuple[int, int]:
        """處理整個程式碼庫，解析並匯入知識圖譜
        
        Args:
            codebase_path: 程式碼庫的目錄路徑
            clear_db: 是否清空資料庫
            
        Returns:
            處理的節點數量和關係數量
        """
        logger.info(f"開始處理程式碼庫: {codebase_path}")
        
        # 驗證資料庫連接
        if not self.db.verify_connection():
            raise ConnectionError("無法連接到Neo4j資料庫，請檢查連接設定")
        
        # 清空資料庫（如果需要）
        if clear_db:
            logger.info("清空資料庫...")
            self.db.clear_database()
        
        # 建立資料庫結構
        logger.info("創建資料庫結構...")
        self.db.create_schema_constraints()
        
        # 解析程式碼庫
        logger.info("解析程式碼庫...")
        nodes, relations = self.parser.parse_directory(codebase_path)
        
        logger.info(f"共解析出 {len(nodes)} 個節點和 {len(relations)} 個關係")
        
        # 為節點生成嵌入向量
        logger.info("為節點生成嵌入向量...")
        self._generate_embeddings(nodes)
        
        # 將節點轉換為Neo4j格式並匯入資料庫
        logger.info("將節點匯入資料庫...")
        neo4j_nodes = self._convert_nodes_to_neo4j_format(nodes)
        self.db.batch_create_nodes(neo4j_nodes)
        
        # 將關係轉換為Neo4j格式並匯入資料庫
        logger.info("將關係匯入資料庫...")
        neo4j_relations = self._convert_relations_to_neo4j_format(relations)
        self.db.batch_create_relationships(neo4j_relations)
        
        # 創建向量索引（用於相似度搜索）
        logger.info("創建向量索引...")
        try:
            for node_label in ["Function", "Method", "Class", "File"]:
                try:
                    self.db.create_vector_index(
                        index_name=f"{node_label.lower()}_vector_index",
                        node_label=node_label,
                        property_name="embedding",
                        dimension=1536  # OpenAI嵌入的維度
                    )
                except Exception as e:
                    logger.warning(f"創建 {node_label} 向量索引時出現警告: {e}")
        except Exception as e:
            logger.error(f"創建向量索引時發生錯誤: {e}")
        
        # 創建全文檢索索引
        logger.info("創建全文檢索索引...")
        try:
            self.db.create_full_text_index(
                index_name="code_index",
                node_labels=["Function", "Method", "Class", "File"],
                properties=["name", "code_snippet"]
            )
        except Exception as e:
            logger.error(f"創建全文檢索索引時發生錯誤: {e}")
        
        logger.info("程式碼庫處理完成！")
        return len(nodes), len(relations)
    
    def _generate_embeddings(self, nodes: Dict[str, Any]) -> None:
        """為節點生成嵌入向量
        
        Args:
            nodes: 節點字典
        """
        batch_size = 20  # 批次大小，避免API限制
        
        # 僅為特定類型的節點生成嵌入
        target_types = ["Function", "Method", "Class", "File"]
        
        nodes_to_embed = [
            (node_id, node) for node_id, node in nodes.items()
            if node.node_type in target_types
        ]
        
        for i in range(0, len(nodes_to_embed), batch_size):
            batch = nodes_to_embed[i:i+batch_size]
            
            # 重置批次資料
            code_texts = []
            node_types = []
            names = []
            node_ids = []
            
            # 收集批次資料
            for node_id, node in batch:
                # 對於檔案類型，使用檔案名稱作為代碼文本
                if node.node_type == "File":
                    code_text = f"File: {node.name}"
                else:
                    code_text = node.code_snippet or f"{node.node_type}: {node.name}"
                
                code_texts.append(code_text)
                node_types.append(node.node_type)
                names.append(node.name)
                node_ids.append(node_id)
            
            # 只在有資料要處理時才進行嵌入向量生成
            if code_texts:
                # 批次生成嵌入向量
                embeddings = self.code_embedder.embed_code_nodes_batch(
                    code_texts=code_texts,
                    node_types=node_types,
                    names=names
                )
                
                # 確保嵌入向量與節點列表長度匹配
                if len(embeddings) >= len(node_ids):
                    # 將嵌入向量添加到節點
                    for i, node_id in enumerate(node_ids):
                        nodes[node_id].properties["embedding"] = embeddings[i]
                    
                    logger.debug(f"已生成 {len(batch)} 個節點的嵌入向量")
                else:
                    # 處理嵌入向量數量不足的情況
                    logger.warning(f"嵌入向量數量({len(embeddings)})小於節點數量({len(node_ids)})，使用零向量代替")
                    for i, node_id in enumerate(node_ids):
                        if i < len(embeddings):
                            nodes[node_id].properties["embedding"] = embeddings[i]
                        else:
                            # 使用零向量代替
                            nodes[node_id].properties["embedding"] = [0.0] * 1536
    
    def _convert_nodes_to_neo4j_format(self, nodes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """將節點轉換為Neo4j批量匯入的格式
        
        Args:
            nodes: 節點字典
            
        Returns:
            Neo4j格式的節點列表
        """
        neo4j_nodes = []
        
        for node_id, node in nodes.items():
            # 創建基本屬性
            properties = {
                "id": node_id,
                "name": node.name,
                "file_path": node.file_path,
                "line_no": node.line_no
            }
            
            # 添加節點類型特定的屬性
            if node.end_line_no:
                properties["end_line_no"] = node.end_line_no
            
            if node.code_snippet:
                properties["code_snippet"] = node.code_snippet
            
            # 添加嵌入向量（如果有）
            if "embedding" in node.properties:
                properties["embedding"] = node.properties["embedding"]
            
            # 合併其他屬性，確保所有屬性都是Neo4j兼容的原始類型
            for key, value in node.properties.items():
                if key != "embedding":  # 跳過已處理的嵌入向量
                    # 檢查屬性值類型，確保是Neo4j支持的原始類型或其數組
                    if isinstance(value, (str, int, float, bool)) or (
                        isinstance(value, list) and all(isinstance(item, (int, float)) for item in value)
                    ):
                        properties[key] = value
                    else:
                        # 如果不是原始類型，嘗試使用JSON序列化
                        try:
                            properties[key] = json.dumps(value)
                        except (TypeError, ValueError) as e:
                            logger.warning(f"無法序列化屬性 {key}，跳過: {e}")
            
            # 添加節點標籤
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
            from mcp.server import CodebaseKnowledgeGraphMCP
            
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