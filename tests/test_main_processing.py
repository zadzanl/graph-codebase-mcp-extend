import os
import sys
import shutil
from unittest.mock import patch, MagicMock
import dotenv

# 將專案根目錄加入 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv.load_dotenv()

from src.main import CodebaseKnowledgeGraph

# 檢查是否有必要的環境變數 (用於模擬，非實際連接)
NEO4J_URI_PRESENT = os.environ.get("NEO4J_URI") is not None
OPENAI_API_KEY_PRESENT = os.environ.get("OPENAI_API_KEY") is not None

def run_test():
    print("--- 開始測試主處理流程 ---")
    
    # 創建一個臨時的測試代碼庫目錄
    test_codebase_path = os.path.join(os.path.dirname(__file__), 'temp_test_codebase')
    example_codebase_path = os.path.join(os.path.dirname(__file__), '..', 'example_codebase')
    
    if os.path.exists(test_codebase_path):
        shutil.rmtree(test_codebase_path)
    shutil.copytree(example_codebase_path, test_codebase_path)
    print(f"創建臨時測試代碼庫於: {test_codebase_path}")
    
    # Mock Neo4j 和 OpenAI 的互動
    # 使用 patch 來替換實際的類別或方法
    with patch('src.main.Neo4jDatabase') as MockNeo4jDatabase, \
         patch('src.main.OpenAIEmbeddings') as MockOpenAIEmbeddings, \
         patch('src.main.CodeEmbedder') as MockCodeEmbedder:
        
        # 配置 Mock 物件的行為
        mock_db_instance = MockNeo4jDatabase.return_value
        mock_db_instance.verify_connection.return_value = True
        mock_db_instance.batch_create_nodes.return_value = None
        mock_db_instance.batch_create_relationships.return_value = None
        mock_db_instance.create_schema_constraints.return_value = None
        mock_db_instance.create_vector_index.return_value = None
        mock_db_instance.create_full_text_index.return_value = None
        mock_db_instance.clear_database.return_value = None

        # 配置 Mock Embedder
        mock_embedder_instance = MockOpenAIEmbeddings.return_value
        mock_code_embedder_instance = MockCodeEmbedder.return_value
        # 模擬返回固定維度的零向量 - 增加數量以覆蓋所有節點
        mock_code_embedder_instance.embed_code_nodes_batch.return_value = [[0.0] * 1536] * 30 # 提供足夠多的嵌入向量

        kg = None
        try:
            # 初始化 CodebaseKnowledgeGraph (使用 Mock 物件)
            kg = CodebaseKnowledgeGraph()
            print("- 成功: 初始化 CodebaseKnowledgeGraph")
            
            # 執行處理流程
            print("正在執行 process_codebase...")
            num_nodes, num_relations = kg.process_codebase(test_codebase_path, clear_db=True)
            
            # 驗證是否呼叫了 Mock 的方法
            mock_db_instance.verify_connection.assert_called_once()
            print("- 成功: 驗證資料庫連接已呼叫")
            mock_db_instance.clear_database.assert_called_once()
            print("- 成功: 清空資料庫已呼叫")
            mock_db_instance.create_schema_constraints.assert_called_once()
            print("- 成功: 創建結構已呼叫")
            mock_code_embedder_instance.embed_code_nodes_batch.assert_called()
            print("- 成功: 嵌入向量生成已呼叫")
            mock_db_instance.batch_create_nodes.assert_called_once()
            print("- 成功: 批量創建節點已呼叫")
            mock_db_instance.batch_create_relationships.assert_called_once()
            print("- 成功: 批量創建關係已呼叫")
            mock_db_instance.create_vector_index.assert_called()
            print("- 成功: 創建向量索引已呼叫")
            mock_db_instance.create_full_text_index.assert_called_once()
            print("- 成功: 創建全文索引已呼叫")
            
            # 驗證返回的節點和關係數量是否合理 (基於 example_codebase)
            # 注意：實際數量取決於 ASTParser 的實現
            if num_nodes > 5 and num_relations > 5:
                print(f"- 成功: 返回了合理的節點 ({num_nodes}) 和關係 ({num_relations}) 數量")
            else:
                print(f"[警告] 返回的節點 ({num_nodes}) 或關係 ({num_relations}) 數量可能不符預期")

            print("[成功] 主處理流程測試通過 (使用 Mock)")
            
        except Exception as e:
            print(f"[失敗] 主處理流程測試中發生錯誤: {e}")
        finally:
            if kg:
                kg.close() # 這裡會呼叫 mock_db_instance.close()
            # 清理臨時文件
            if os.path.exists(test_codebase_path):
                shutil.rmtree(test_codebase_path)
                print(f"已清理臨時測試代碼庫: {test_codebase_path}")

    print("--- 結束測試主處理流程 ---")

if __name__ == "__main__":
    run_test() 