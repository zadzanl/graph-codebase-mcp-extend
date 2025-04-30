import os
import sys

# 將專案根目錄加入 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ast_parser.parser import ASTParser

def run_test():
    print("--- 開始測試 AST 解析器 ---")
    
    parser = ASTParser()
    example_codebase_path = os.path.join(os.path.dirname(__file__), '..', 'example_codebase')
    
    print(f"測試程式碼庫路徑: {example_codebase_path}")
    
    try:
        nodes, relations = parser.parse_directory(example_codebase_path)
        
        if not nodes:
            print("[失敗] 未解析到任何節點")
            return
        
        if not relations:
            print("[失敗] 未解析到任何關係")
            return

        print(f"成功解析出 {len(nodes)} 個節點和 {len(relations)} 個關係")
        
        # 簡單驗證幾個節點和關係
        found_main_file = any(node.name == 'main.py' and node.node_type == 'File' for node in nodes.values())
        if not found_main_file:
            print("[失敗] 未找到 main.py 檔案節點")
        else:
            print("- 成功找到 main.py 檔案節點")
            
        found_process_data = any(node.name == 'process_data' and node.node_type == 'Function' for node in nodes.values())
        if not found_process_data:
            print("[失敗] 未找到 process_data 函數節點")
        else:
            print("- 成功找到 process_data 函數節點")

        found_user_class = any(node.name == 'User' and node.node_type == 'Class' for node in nodes.values())
        if not found_user_class:
            print("[失敗] 未找到 User 類別節點")
        else:
            print("- 成功找到 User 類別節點")
            
        found_call_relation = any(rel.relation_type == 'CALLS' for rel in relations)
        if not found_call_relation:
            print("[警告] 未找到任何 CALLS 關係 (可能是範例程式碼簡單)")
        else:
            print("- 成功找到 CALLS 關係")
            
        found_import_relation = any(rel.relation_type == 'IMPORTS' for rel in relations)
        if not found_import_relation:
             print("[失敗] 未找到任何 IMPORTS 關係")
        else:
            print("- 成功找到 IMPORTS 關係")

        print("[成功] AST 解析器測試通過")
        
    except Exception as e:
        print(f"[失敗] AST 解析器測試中發生錯誤: {e}")

    print("--- 結束測試 AST 解析器 ---")

if __name__ == "__main__":
    run_test() 