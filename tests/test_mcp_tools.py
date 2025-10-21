import os
import sys
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import dotenv

# 將專案根目錄加入 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv.load_dotenv()

# Mock 依賴項
fast_mcp_mock = MagicMock()
sys.modules['mcp.server.fastmcp'] = fast_mcp_mock
sys.modules['mcp.server.models'] = MagicMock()

from src.mcp.server import CodebaseKnowledgeGraphMCP

# 檢查環境變數
NEO4J_URI_PRESENT = os.environ.get("NEO4J_URI") is not None
OPENAI_API_KEY_PRESENT = os.environ.get("OPENAI_API_KEY") is not None

async def run_test():
    print("--- 開始測試 MCP Server 工具 ---")

    # Mock Neo4j 和 embedding factory
    with patch('src.mcp.server.Neo4jDatabase') as MockNeo4jDatabase, \
         patch('src.mcp.server.get_embedding_provider') as MockGetEmbeddingProvider, \
         patch('src.mcp.server.CodeEmbedder') as MockCodeEmbedder:

        # 配置 Mock 物件
        mock_db_instance = MockNeo4jDatabase.return_value
        mock_embedding_provider = MagicMock()
        MockGetEmbeddingProvider.return_value = mock_embedding_provider
        mock_code_embedder_instance = MockCodeEmbedder.return_value

        # 模擬 DB 返回值 (使用 AsyncMock)
        mock_db_instance.search_code_by_vector = AsyncMock(return_value=[{"node": {"name": "mock_func"}, "score": 0.9}])
        mock_db_instance.search_code_by_text = AsyncMock(return_value=[{"node": {"name": "mock_text"}, "score": 0.8}])
        mock_db_instance.execute_cypher = AsyncMock(return_value=[{"result": "mock_cypher_data"}])

        # 模擬 Embedder 返回值
        # Configure embedding provider mock to return a vector
        default_dim = 1536
        mock_embedding_provider.embed_text = MagicMock(return_value=[0.1] * default_dim)
        
        # Configure code embedder to have access to the provider
        mock_code_embedder_instance.provider = mock_embedding_provider

        # 配置 FastMCP Mock - 讓 .tool() 返回一個簡單的裝飾器，它什麼都不做
        def mock_tool_decorator(*args, **kwargs):
            def decorator(func):
                return func # 直接返回原函數，不實際註冊到 Mock 物件
            return decorator
        
        mock_fast_mcp_instance = fast_mcp_mock.FastMCP.return_value
        mock_fast_mcp_instance.tool.side_effect = mock_tool_decorator
        
        mcp_server = None
        try:
            # 初始化 MCP Server (使用 Mock)
            mcp_server = CodebaseKnowledgeGraphMCP(
                neo4j_uri="mock_uri",
                neo4j_user="mock_user",
                neo4j_password="mock_pass"
            )
            print("- 成功: 初始化 CodebaseKnowledgeGraphMCP (使用 Mock)")

            # --- 直接訪問實例上的異步方法進行測試 --- 
            # 由於裝飾器被 Mock 掉了，我們直接測試類別中的異步方法

            # 測試 search_code (vector)
            print("正在測試 search_code (vector)...")
            # 假設 search_code 是 CodebaseKnowledgeGraphMCP 的一個異步方法
            if hasattr(mcp_server, 'search_code') and asyncio.iscoroutinefunction(mcp_server.search_code):
                result_str = await mcp_server.search_code(query="find similar functions", search_type="vector")
                result = json.loads(result_str)
                if isinstance(result, list) and len(result) > 0 and "node" in result[0]:
                    print("- 成功: search_code (vector) 返回預期格式")
                    mock_db_instance.search_code_by_vector.assert_awaited()
                else:
                    print(f"[失敗] search_code (vector) 返回格式錯誤: {result_str}")
            else:
                 print("[跳過] CodebaseKnowledgeGraphMCP 實例上未找到異步方法 search_code")

            # 測試 search_code (text)
            print("正在測試 search_code (text)...")
            if hasattr(mcp_server, 'search_code') and asyncio.iscoroutinefunction(mcp_server.search_code):
                mock_db_instance.search_code_by_text.reset_mock()
                result_str = await mcp_server.search_code(query="find text match", search_type="text")
                result = json.loads(result_str)
                if isinstance(result, list) and len(result) > 0 and "node" in result[0]:
                     print("- 成功: search_code (text) 返回預期格式")
                     mock_db_instance.search_code_by_text.assert_awaited_once()
                else:
                     print(f"[失敗] search_code (text) 返回格式錯誤: {result_str}")
            else:
                 print("[跳過] CodebaseKnowledgeGraphMCP 實例上未找到異步方法 search_code")

            # 測試 execute_cypher_query
            print("正在測試 execute_cypher_query...")
            if hasattr(mcp_server, 'execute_cypher_query') and asyncio.iscoroutinefunction(mcp_server.execute_cypher_query):
                mock_db_instance.execute_cypher.reset_mock()
                result_str = await mcp_server.execute_cypher_query(query="MATCH (n) RETURN n")
                result = json.loads(result_str)
                if isinstance(result, list) and len(result) > 0 and "result" in result[0]:
                    print("- 成功: execute_cypher_query 返回預期格式")
                    mock_db_instance.execute_cypher.assert_awaited_once_with("MATCH (n) RETURN n", None)
                else:
                    print(f"[失敗] execute_cypher_query 返回格式錯誤: {result_str}")
            else:
                print("[跳過] CodebaseKnowledgeGraphMCP 實例上未找到異步方法 execute_cypher_query")

            # 測試 find_function_callers
            print("正在測試 find_function_callers...")
            if hasattr(mcp_server, 'find_function_callers') and asyncio.iscoroutinefunction(mcp_server.find_function_callers):
                 mock_db_instance.execute_cypher.reset_mock()
                 mock_db_instance.execute_cypher.return_value = [{"caller": {"name":"caller_func"}}]
                 result_str = await mcp_server.find_function_callers(function_name="test_func")
                 result = json.loads(result_str)
                 if isinstance(result, list) and len(result)>0 and 'caller' in result[0]:
                     print("- 成功: find_function_callers 返回預期格式")
                     mock_db_instance.execute_cypher.assert_awaited_once()
                     call_args, call_kwargs = mock_db_instance.execute_cypher.call_args
                     assert "MATCH (caller)-[:CALLS]->(callee)" in call_args[0]
                     assert call_args[1]["function_name"] == "test_func"
                 else:
                     print(f"[失敗] find_function_callers 返回格式錯誤: {result_str}")
            else:
                 print("[跳過] CodebaseKnowledgeGraphMCP 實例上未找到異步方法 find_function_callers")

            # ... 添加對 find_function_callees, find_class_inheritance, find_file_dependencies 的類似測試 ...

            print("[成功] MCP Server 工具測試完成 (使用 Mock)")

        except Exception as e:
            import traceback
            print(f"[失敗] MCP Server 工具測試中發生錯誤: {e}")
            traceback.print_exc() # 打印詳細錯誤堆疊
        finally:
            # 不需要實際關閉 DB，因為它是 Mock
            pass

    print("--- 結束測試 MCP Server 工具 ---")

if __name__ == "__main__":
    asyncio.run(run_test())