import os
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from openai import OpenAI

class Embedder:
    """基礎的嵌入向量處理介面"""
    
    def embed_text(self, text: str) -> List[float]:
        """將文字轉換為嵌入向量"""
        raise NotImplementedError("子類別必須實現此方法")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量將文字轉換為嵌入向量"""
        return [self.embed_text(text) for text in texts]


class OpenAIEmbeddings(Embedder):
    """使用OpenAI API生成嵌入向量"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "text-embedding-3-small"
    ):
        """初始化OpenAI嵌入處理器
        
        Args:
            api_key: OpenAI API金鑰。若為None，則嘗試從環境變數取得
            model: 使用的模型名稱，預設為text-embedding-3-small
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("需要提供OpenAI API金鑰，可通過參數或OPENAI_API_KEY環境變數")
        
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
    
    def embed_text(self, text: str) -> List[float]:
        """使用OpenAI API將文字轉換為嵌入向量
        
        Args:
            text: 要轉換的文字
            
        Returns:
            生成的向量表示
        """
        if not text or text.strip() == "":
            # 對空文字回傳零向量，避免API錯誤
            return [0.0] * 1536  # 預設維度
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text.strip(),
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"生成嵌入時發生錯誤: {e}")
            # 發生錯誤時回傳零向量
            return [0.0] * 1536
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量使用OpenAI API將多個文字轉換為嵌入向量
        
        Args:
            texts: 要轉換的文字列表
            
        Returns:
            生成的向量表示列表
        """
        # 過濾空字串
        filtered_texts = [text.strip() for text in texts if text and text.strip()]
        
        if not filtered_texts:
            return []
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=filtered_texts,
                encoding_format="float"
            )
            
            # 創建一個字典來確保返回的向量順序與輸入相同
            embedding_dict = {}
            
            for i, emb_data in enumerate(response.data):
                embedding_dict[emb_data.index] = emb_data.embedding
            
            # 按照索引順序排列嵌入向量
            sorted_embeddings = [embedding_dict[i] for i in range(len(filtered_texts))]
            
            # 為原始texts列表中的空字串補充零向量
            result = []
            filtered_index = 0
            
            for text in texts:
                if text and text.strip():
                    if filtered_index < len(sorted_embeddings):
                        result.append(sorted_embeddings[filtered_index])
                        filtered_index += 1
                    else:
                        # 預防批量處理中的錯誤
                        result.append([0.0] * 1536)
                else:
                    result.append([0.0] * 1536)
            
            return result
            
        except Exception as e:
            print(f"批量生成嵌入時發生錯誤: {e}")
            # 發生錯誤時為所有文字回傳零向量
            return [[0.0] * 1536 for _ in texts]


class CodeEmbedder:
    """專門用於程式碼嵌入的處理器"""
    
    def __init__(self, embedder: Embedder):
        """初始化程式碼嵌入處理器
        
        Args:
            embedder: 實際用於生成嵌入的處理器實例
        """
        self.embedder = embedder
    
    def prepare_code_text(self, code_text: str, node_type: str, name: str) -> str:
        """預處理程式碼文字，以便更好地生成嵌入
        
        Args:
            code_text: 原始程式碼文字
            node_type: 節點類型 (例如："Function", "Class", "Method")
            name: 節點名稱
            
        Returns:
            預處理後的文字
        """
        # 添加節點類型和名稱作為上下文，改善嵌入質量
        prepared_text = f"{node_type} {name}:\n{code_text}"
        return prepared_text
    
    def embed_code_node(self, 
                       code_text: str, 
                       node_type: str, 
                       name: str) -> List[float]:
        """為單個程式碼節點生成嵌入向量
        
        Args:
            code_text: 程式碼文字
            node_type: 節點類型
            name: 節點名稱
            
        Returns:
            生成的向量表示
        """
        prepared_text = self.prepare_code_text(code_text, node_type, name)
        return self.embedder.embed_text(prepared_text)
    
    def embed_code_nodes_batch(self, 
                             code_texts: List[str], 
                             node_types: List[str], 
                             names: List[str]) -> List[List[float]]:
        """批量為多個程式碼節點生成嵌入向量
        
        Args:
            code_texts: 程式碼文字列表
            node_types: 節點類型列表
            names: 節點名稱列表
            
        Returns:
            生成的向量表示列表
        """
        if not (len(code_texts) == len(node_types) == len(names)):
            raise ValueError("code_texts, node_types, 和 names 必須具有相同長度")
        
        prepared_texts = [
            self.prepare_code_text(code, node_type, name)
            for code, node_type, name in zip(code_texts, node_types, names)
        ]
        
        return self.embedder.embed_batch(prepared_texts)


# 使用範例
if __name__ == "__main__":
    # 從環境變數獲取API金鑰
    api_key = os.environ.get("OPENAI_API_KEY")
    
    # 創建嵌入處理器
    openai_embedder = OpenAIEmbeddings(api_key=api_key)
    code_embedder = CodeEmbedder(openai_embedder)
    
    # 測試單個程式碼嵌入
    sample_code = """
    def calculate_sum(a, b):
        \"\"\"Calculate the sum of two numbers.\"\"\"
        return a + b
    """
    
    embedding = code_embedder.embed_code_node(
        code_text=sample_code,
        node_type="Function",
        name="calculate_sum"
    )
    
    print(f"嵌入向量維度: {len(embedding)}")
    print(f"嵌入向量前10個元素: {embedding[:10]}") 