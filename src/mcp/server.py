import os
import argparse
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.models import InitializationOptions
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.neo4j_storage.graph_db import Neo4jDatabase
from src.embeddings.factory import get_embedding_provider
from src.embeddings.embedder import CodeEmbedder

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CodebaseKnowledgeGraphMCP:
    """Codebase知識圖譜的MCP服務器實現"""
    
    def __init__(self, neo4j_uri=None, neo4j_user=None, neo4j_password=None, server_host=None, server_port=None):
        """初始化MCP服務器
        
        Args:
            neo4j_uri: Neo4j資料庫URI，若為None則從環境變數取得
            neo4j_user: Neo4j使用者名稱，若為None則從環境變數取得
            neo4j_password: Neo4j密碼，若為None則從環境變數取得
            server_host: MCP服務器主機地址，用於HTTP/SSE傳輸
            server_port: MCP服務器端口，用於HTTP/SSE傳輸
        """
        self.neo4j_uri = neo4j_uri or os.environ.get("NEO4J_URI")
        self.neo4j_user = neo4j_user or os.environ.get("NEO4J_USER")
        self.neo4j_password = neo4j_password or os.environ.get("NEO4J_PASSWORD")
        
        # Get server configuration from parameters, environment, or use defaults
        # 從參數、環境變數獲取服務器配置或使用默認值
        self.server_host = server_host or os.environ.get("MCP_SERVER_HOST", "127.0.0.1")
        self.server_port = server_port or int(os.environ.get("MCP_SERVER_PORT", "8080"))
        
        # 初始化FastMCP (配置 host 和 port)
        self.mcp = FastMCP(
            name="Codebase KG Server",
            host=self.server_host,
            port=self.server_port
        )
        
        # 初始化Neo4j資料庫
        self.db = Neo4jDatabase(
            uri=self.neo4j_uri,
            user=self.neo4j_user,
            password=self.neo4j_password
        )
        
        # 初始化嵌入處理器 (使用工廠模式支持多種提供商)
        embedding_provider = get_embedding_provider()
        self.code_embedder = CodeEmbedder(embedding_provider)
        
        # 註冊MCP工具
        self._register_tools()
        
        # 註冊MCP提示詞
        self._register_prompts()
        
        # 註冊MCP資源
        self._register_resources()
    
    def _register_tools(self):
        """註冊MCP工具"""
        
        @self.mcp.tool()
        async def search_code(query: str, limit: int = 10, search_type: str = "vector") -> str:
            """搜索程式碼
            
            Args:
                query: 搜索查詢
                limit: 返回結果的最大數量
                search_type: 搜索類型，可選 "vector" 或 "text"
                
            Returns:
                搜索結果的JSON字符串
            """
            try:
                results = []
                
                if search_type == "vector":
                    # 生成查詢的嵌入向量
                    vector = self.code_embedder.provider.embed_text(query)
                    
                    # 使用向量搜索
                    for node_label in ["Function", "Method", "Class", "File"]:
                        node_results = self.db.search_code_by_vector(vector, node_label, limit)
                        results.extend(node_results)
                    
                    # 根據分數排序
                    results = sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
                    
                elif search_type == "text":
                    # 使用全文檢索
                    results = self.db.search_code_by_text(query, limit)
                
                return json.dumps(results, ensure_ascii=False)
                
            except Exception as e:
                logger.error(f"搜索程式碼時發生錯誤: {e}")
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def execute_cypher_query(query: str, parameters: Dict = None) -> str:
            """執行Cypher查詢
            
            Args:
                query: Cypher查詢語句
                parameters: 查詢參數
                
            Returns:
                查詢結果的JSON字符串
            """
            try:
                results = self.db.execute_cypher(query, parameters)
                return json.dumps(results, ensure_ascii=False)
            except Exception as e:
                logger.error(f"執行Cypher查詢時發生錯誤: {e}")
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def get_code_by_name(name: str, node_type: str = None) -> str:
            """根據名稱獲取程式碼
            
            Args:
                name: 程式碼名稱(類別名、函數名等)
                node_type: 節點類型，可選 "Function", "Method", "Class", "File"
                
            Returns:
                程式碼的JSON字符串
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
                logger.error(f"獲取程式碼時發生錯誤: {e}")
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def find_function_callers(function_name: str, limit: int = 10) -> str:
            """查找調用特定函數的所有位置
            
            Args:
                function_name: 函數名稱
                limit: 返回結果的最大數量
                
            Returns:
                調用者的JSON字符串
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
                logger.error(f"查找函數調用者時發生錯誤: {e}")
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def find_function_callees(function_name: str, limit: int = 10) -> str:
            """查找特定函數調用的所有函數
            
            Args:
                function_name: 函數名稱
                limit: 返回結果的最大數量
                
            Returns:
                被調用函數的JSON字符串
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
                logger.error(f"查找函數調用的函數時發生錯誤: {e}")
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def find_class_inheritance(class_name: str) -> str:
            """查找類別的繼承關係
            
            Args:
                class_name: 類別名稱
                
            Returns:
                繼承關係的JSON字符串
            """
            try:
                # 查找超類
                superclasses_query = """
                MATCH (sub:Class {name: $class_name})-[:EXTENDS]->(super:Class)
                RETURN super
                """
                
                superclasses = self.db.execute_cypher(superclasses_query, {
                    "class_name": class_name
                })
                
                # 查找子類
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
                logger.error(f"查找類別繼承關係時發生錯誤: {e}")
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def find_file_dependencies(file_path: str) -> str:
            """查找檔案的依賴關係
            
            Args:
                file_path: 檔案路徑
                
            Returns:
                依賴關係的JSON字符串
            """
            try:
                # 查找該檔案導入的模組
                imports_query = """
                MATCH (f:File {path: $file_path})-[:IMPORTS]->(m:Module)
                RETURN m
                """
                
                imports = self.db.execute_cypher(imports_query, {
                    "file_path": file_path
                })
                
                # 查找導入該檔案的檔案
                imported_by_query = """
                MATCH (f:File)-[:IMPORTS]->(m:Module)
                WHERE m.name = $file_name
                RETURN f
                """
                
                file_name = os.path.basename(file_path).split(".")[0]
                imported_by = self.db.execute_cypher(imported_by_query, {
                    "file_name": file_name
                })
                
                return json.dumps({
                    "imports": imports,
                    "imported_by": imported_by
                }, ensure_ascii=False)
                
            except Exception as e:
                logger.error(f"查找檔案依賴關係時發生錯誤: {e}")
                return json.dumps({"error": str(e)})
    
    def _register_prompts(self):
        """註冊MCP提示詞"""
        
        @self.mcp.prompt()
        def code_search_prompt(query: str) -> str:
            """創建程式碼搜索提示詞
            
            Args:
                query: 搜索查詢
                
            Returns:
                生成的提示詞
            """
            return f"""
            你是一個程式碼庫專家，請幫助我搜索與以下查詢相關的程式碼：
            
            查詢: {query}
            
            請優先考慮以下方面：
            1. 搜索相關的函數、方法、類別或檔案
            2. 分析代碼之間的關係（如調用關係、繼承關係等）
            3. 解釋找到的代碼的功能和作用
            
            你可以使用提供的工具來執行搜索並分析結果。
            """
        
        @self.mcp.prompt()
        def code_understanding_prompt(code_element: str, element_type: str) -> str:
            """創建程式碼理解提示詞
            
            Args:
                code_element: 程式碼元素名稱（函數名、類別名等）
                element_type: 元素類型（"Function", "Class", "File"等）
                
            Returns:
                生成的提示詞
            """
            return f"""
            你是一個程式碼分析專家，請幫助我理解以下程式碼元素：
            
            元素名稱: {code_element}
            元素類型: {element_type}
            
            請提供以下分析：
            1. 該元素的主要功能和作用
            2. 它與其他代碼元素的關係（如調用關係、繼承關係等）
            3. 該元素的使用方式和示例
            
            你可以使用提供的工具來獲取該元素的詳細信息並分析其結構。
            """
    
    def _register_resources(self):
        """註冊MCP資源"""
        
        @self.mcp.resource("schema://kg")
        def get_kg_schema() -> str:
            """獲取知識圖譜的結構描述
            
            Returns:
                知識圖譜結構的描述
            """
            return """
            知識圖譜結構:
            
            節點類型:
            - File: 代表程式碼檔案
              - 屬性: id, path, name
            - Class: 代表類別定義
              - 屬性: id, name, file_path, line_no, end_line_no, code_snippet
            - Function: 代表全局函數定義
              - 屬性: id, name, file_path, line_no, end_line_no, code_snippet
            - Method: 代表類別方法
              - 屬性: id, name, file_path, line_no, end_line_no, code_snippet
            - Variable: 代表變數定義
              - 屬性: id, name, file_path, line_no
            - Module: 代表導入的模組
              - 屬性: id, name
            
            關係類型:
            - CONTAINS: 表示一個檔案包含某個程式碼元素
              - 例如: (File)-[:CONTAINS]->(Function)
            - DEFINES: 表示一個類別定義了一個方法或屬性
              - 例如: (Class)-[:DEFINES]->(Method)
            - CALLS: 表示函數調用關係
              - 例如: (Function)-[:CALLS]->(Function)
            - EXTENDS: 表示類別的繼承關係
              - 例如: (Class)-[:EXTENDS]->(Class)
            - IMPORTS: 表示檔案導入了某個模組
              - 例如: (File)-[:IMPORTS]->(Module)
            """
        
        @self.mcp.resource("cypher://examples")
        def get_cypher_examples() -> str:
            """獲取Cypher查詢示例
            
            Returns:
                Cypher查詢示例
            """
            return """
            Cypher查詢示例:
            
            1. 查找特定名稱的函數:
            ```
            MATCH (f:Function)
            WHERE f.name = "process_data"
            RETURN f
            ```
            
            2. 查找調用某函數的所有函數:
            ```
            MATCH (caller)-[:CALLS]->(callee:Function)
            WHERE callee.name = "process_data"
            RETURN caller
            ```
            
            3. 查找繼承自某類別的所有類別:
            ```
            MATCH (sub:Class)-[:EXTENDS]->(super:Class)
            WHERE super.name = "BaseProcessor"
            RETURN sub
            ```
            
            4. 查找檔案及其包含的函數:
            ```
            MATCH (file:File)-[:CONTAINS]->(func:Function)
            WHERE file.path = "src/main.py"
            RETURN func
            ```
            
            5. 查找導入某模組的所有檔案:
            ```
            MATCH (file:File)-[:IMPORTS]->(module:Module)
            WHERE module.name = "pandas"
            RETURN file
            ```
            """
    
    def start(self, port=None, transport="stdio"):
        """啟動MCP服務器
        
        Args:
            port: HTTP服務器端口號 (ignored, port is set during initialization)
            transport: 傳輸協議，可選 "stdio", "http" (streamable-http) 或 "sse"
        """
        if transport == "http":
            logger.info(f"MCP服務器以HTTP模式啟動，監聽於 http://{self.server_host}:{self.server_port}/mcp")
            self.mcp.run(transport="streamable-http")
        elif transport == "sse":
            logger.info(f"MCP服務器以SSE模式啟動，監聽於 http://{self.server_host}:{self.server_port}/sse")
            self.mcp.run(transport="sse")
        else:
            logger.info("MCP服務器以stdio模式啟動")
            self.mcp.run(transport="stdio")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="Codebase知識圖譜MCP服務器")
    parser.add_argument("--codebase-path", help="程式碼庫路徑", default=".")
    parser.add_argument("--transport", choices=["stdio", "http", "sse"], default="stdio", help="MCP傳輸協議")
    parser.add_argument("--port", type=int, help="HTTP服務器端口號（僅用於HTTP/SSE傳輸）", default=8080)
    parser.add_argument("--neo4j-uri", help="Neo4j資料庫URI")
    parser.add_argument("--neo4j-user", help="Neo4j使用者名稱")
    parser.add_argument("--neo4j-password", help="Neo4j密碼")
    
    args = parser.parse_args()
    
    # 創建MCP服務器
    server = CodebaseKnowledgeGraphMCP(
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password,
        server_port=args.port
    )
    
    # 啟動服務器
    server.start(transport=args.transport)


if __name__ == "__main__":
    main() 