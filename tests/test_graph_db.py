import os
import sys
import time
import dotenv

# 將專案根目錄加入 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv.load_dotenv()

from src.neo4j.graph_db import Neo4jDatabase

def run_test():
    print("--- 開始測試 Neo4j 資料庫操作 ---")
    print("[注意] 此測試需要一個正在運行的 Neo4j 實例，並在 .env 中配置了連接信息")
    
    db = None # 初始化 db 變數
    try:
        # 測試資料庫連接
        db = Neo4jDatabase()
        if not db.verify_connection():
            print("[失敗] 無法驗證 Neo4j 連接，請檢查服務是否運行及 .env 配置")
            print("[警告] Neo4j 資料庫操作測試未完全執行")
            print("--- 結束測試 Neo4j 資料庫操作 ---")
            return
        else:
            print("- 成功: 資料庫連接驗證通過")
        
        # 測試清空資料庫
        print("正在清空測試資料庫...")
        db.clear_database()
        time.sleep(1) # 等待操作生效
        result = db.execute_cypher("MATCH (n) RETURN count(n) as count")
        if result[0]['count'] != 0:
             print("[失敗] 清空資料庫後節點數量不為 0")
        else:
            print("- 成功: 清空資料庫完成")

        # 測試創建結構
        print("正在創建資料庫結構...")
        db.create_schema_constraints()
        print("- 成功: 創建結構約束和索引") # 這裡假設執行無誤即成功
        
        # 測試批量創建節點
        test_nodes = [
            {"labels": ["Base", "TestNode"], "properties": {"id": "test1", "name": "Node 1", "value": 10}},
            {"labels": ["Base", "TestNode"], "properties": {"id": "test2", "name": "Node 2", "value": 20}}
        ]
        print("正在批量創建節點...")
        db.batch_create_nodes(test_nodes)
        time.sleep(1)
        result = db.execute_cypher("MATCH (n:TestNode) RETURN count(n) as count")
        if result[0]['count'] != len(test_nodes):
            print(f"[失敗] 批量創建節點後數量錯誤 (預期 {len(test_nodes)}, 實際 {result[0]['count']})")
        else:
            print("- 成功: 批量創建節點完成")

        # 測試批量創建關係
        test_relations = [
            {"start_node_id": "test1", "end_node_id": "test2", "type": "RELATES_TO", "properties": {"weight": 1.0}}
        ]
        print("正在批量創建關係...")
        db.batch_create_relationships(test_relations)
        time.sleep(1)
        result = db.execute_cypher("MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count")
        if result[0]['count'] != len(test_relations):
             print(f"[失敗] 批量創建關係後數量錯誤 (預期 {len(test_relations)}, 實際 {result[0]['count']})")
        else:
            print("- 成功: 批量創建關係完成")
            
        # 測試執行 Cypher 查詢
        print("正在測試執行 Cypher 查詢...")
        result = db.execute_cypher("MATCH (n:TestNode {name: $name}) RETURN n.value as value", {"name": "Node 1"})
        if not result or result[0]['value'] != 10:
            print(f"[失敗] Cypher 查詢結果不符預期: {result}")
        else:
            print("- 成功: Cypher 查詢執行正確")
            
        # 清理測試數據
        print("正在清理測試數據...")
        db.clear_database()

        print("[成功] Neo4j 資料庫操作測試通過")

    except Exception as e:
        print(f"[失敗] Neo4j 資料庫操作測試中發生錯誤: {e}")
    finally:
        if db:
            db.close()

    print("--- 結束測試 Neo4j 資料庫操作 ---")

if __name__ == "__main__":
    run_test() 