import os
import sys
import dotenv

# 將專案根目錄加入 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv.load_dotenv()

from src.embeddings.embedder import OpenAIEmbeddings, CodeEmbedder

# 從環境變數讀取 API Key，如果沒有則設為 None
API_KEY = os.environ.get("OPENAI_API_KEY")

def run_test():
    print("--- 開始測試 Embeddings 處理器 ---")

    # 只有在提供 API Key 時才執行實際的嵌入測試
    if not API_KEY:
        print("[跳過] 未提供 OPENAI_API_KEY 環境變數，跳過實際的嵌入測試")
        try:
            # 測試初始化時是否正確拋出錯誤
            OpenAIEmbeddings(api_key=None)
            print("[失敗] 未提供 API Key 時，OpenAIEmbeddings 初始化未引發 ValueError")
        except ValueError:
            print("- 成功: 未提供 API Key 時，OpenAIEmbeddings 初始化正確引發 ValueError")
            print("[警告] Embeddings 處理器測試未完全執行 (缺少 API Key)")
        except Exception as e:
             print(f"[失敗] 測試初始化錯誤時發生意外錯誤: {e}")
        print("--- 結束測試 Embeddings 處理器 ---")
        return

    try:
        openai_embedder = OpenAIEmbeddings(api_key=API_KEY)
        code_embedder = CodeEmbedder(openai_embedder)
        
        # 測試單個文本嵌入
        sample_text = "This is a sample text for embedding."
        embedding = openai_embedder.embed_text(sample_text)
        if not embedding or len(embedding) != 1536: # text-embedding-3-small 維度
            print(f"[失敗] 單個文本嵌入失敗或維度錯誤: 維度 {len(embedding) if embedding else 'None'}")
        else:
            print("- 成功: 單個文本嵌入完成，維度正確")

        # 測試批量文本嵌入
        sample_texts = ["First text", "", "Third text"]
        batch_embeddings = openai_embedder.embed_batch(sample_texts)
        if len(batch_embeddings) != len(sample_texts):
            print("[失敗] 批量文本嵌入返回數量錯誤")
        elif len(batch_embeddings[0]) != 1536 or len(batch_embeddings[2]) != 1536:
             print("[失敗] 批量文本嵌入向量維度錯誤")
        elif not all(v == 0.0 for v in batch_embeddings[1]): # 檢查空字串的嵌入是否為零向量
            print("[失敗] 批量文本嵌入中空字串未返回零向量")
        else:
            print("- 成功: 批量文本嵌入完成，維度正確，空字串處理正確")
        
        # 測試單個程式碼嵌入
        sample_code = "def greet(name):\n  print(f\"Hello, {name}!\")"
        code_embedding = code_embedder.embed_code_node(
            code_text=sample_code,
            node_type="Function",
            name="greet"
        )
        if not code_embedding or len(code_embedding) != 1536:
            print(f"[失敗] 單個程式碼嵌入失敗或維度錯誤: 維度 {len(code_embedding) if code_embedding else 'None'}")
        else:
            print("- 成功: 單個程式碼嵌入完成，維度正確")
            
        # 測試批量程式碼嵌入
        sample_codes = [sample_code, "class MyClass:\n  pass"]
        node_types = ["Function", "Class"]
        names = ["greet", "MyClass"]
        batch_code_embeddings = code_embedder.embed_code_nodes_batch(
            code_texts=sample_codes,
            node_types=node_types,
            names=names
        )
        if len(batch_code_embeddings) != len(sample_codes):
            print("[失敗] 批量程式碼嵌入返回數量錯誤")
        elif any(len(emb) != 1536 for emb in batch_code_embeddings):
            print("[失敗] 批量程式碼嵌入向量維度錯誤")
        else:
            print("- 成功: 批量程式碼嵌入完成，維度正確")

        print("[成功] Embeddings 處理器測試通過")

    except Exception as e:
        print(f"[失敗] Embeddings 處理器測試中發生錯誤: {e}")

    print("--- 結束測試 Embeddings 處理器 ---")

if __name__ == "__main__":
    run_test() 