from openai import OpenAI, RateLimitError
import time
from .base import EmbeddingProvider
from typing import List
import tiktoken

class OpenAICompatibleProvider(EmbeddingProvider):
    def __init__(self, api_key: str, base_url: str, model: str, api_key_name: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.api_key_name = api_key_name
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.max_tokens = 511 # Conservative value, multilingual-e5 are 512 token max
        # Determine expected embedding dimensionality for the configured model
        self.dimension = self._infer_dimension_from_model(model)

    def _truncate_text(self, text: str) -> str:
        """Truncates text to the maximum token limit."""
        tokens = self.encoding.encode(text)
        if len(tokens) > self.max_tokens:
            truncated_tokens = tokens[:self.max_tokens]
            return self.encoding.decode(truncated_tokens)
        return text

    def embed_text(self, text: str) -> List[float]:
        text = self._truncate_text(text)
        if not text or text.strip() == "":
            return [0.0] * self.dimension
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text.strip(),
                encoding_format="float"
            )
            return response.data[0].embedding
        except RateLimitError:
            print("Rate limit reached, waiting...")
            time.sleep(60)
            return self.embed_text(text)
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return [0.0] * self.dimension

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        truncated_texts = [self._truncate_text(text) for text in texts]
        filtered_texts = [text.strip() for text in truncated_texts if text and text.strip()]
        if not filtered_texts:
            return [[0.0] * self.dimension for _ in texts]

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=filtered_texts,
                encoding_format="float"
            )
            
            embedding_dict = {emb_data.index: emb_data.embedding for emb_data in response.data}
            
            result = []
            filtered_index = 0
            for text in texts:
                if text and text.strip():
                    result.append(embedding_dict.get(filtered_index, [0.0] * self.dimension))
                    filtered_index += 1
                else:
                    result.append([0.0] * self.dimension)
            return result
        except RateLimitError:
            print("Rate limit reached, waiting...")
            time.sleep(60)
            return self.embed_batch(texts)
        except Exception as e:
            print(f"Error generating batch embeddings: {e}")
            return [[0.0] * self.dimension for _ in texts]

    def _infer_dimension_from_model(self, model_name: str) -> int:
        """Infer embedding dimensionality from the model name using common mappings.

        Falls back to 1536 when the model is unknown to preserve OpenAI small default.
        """
        if not model_name:
            return 1536

        name = model_name.lower()

        # Common OpenAI models
        if "text-embedding-3-small" in name:
            return 1536
        if "text-embedding-3-large" in name or "text-embedding-3" in name:
            return 3072

        # Google / Gemini embedding models
        # text-embedding-004 uses 768d by default
        if "text-embedding-004" in name:
            return 768
        # Gemini embedding models default to 3072 unless otherwise configured
        if "gemini-embedding" in name or "gemini" in name:
            return 3072

        # Google / Gemma family
        if "embeddinggemma" in name or "gemma" in name:
            # EmbeddingGemma defaults to 768d
            return 768

        # Qwen3 Embedding models
        # Qwen3-Embedding-0.6B has 1024d max
        if "qwen3-embedding-0.6b" in name or "qwen/qwen3-embedding-0.6b" in name:
            return 1024
        # Qwen3-Embedding-4B has 2560d max
        if "qwen3-embedding-4b" in name or "qwen/qwen3-embedding-4b" in name:
            return 2560
        # Qwen3-Embedding-8B has 4096d max
        if "qwen3-embedding-8b" in name or "qwen/qwen3-embedding-8b" in name:
            return 4096

        # DeepInfra or other third-party providers: try to parse "_dim" suffix (e.g., -768)
        import re
        m = re.search(r"(\d{3,4})d|-(\d{2,4})b?d?$", name)
        if m:
            for g in m.groups():
                if g:
                    try:
                        val = int(g)
                        # Sanity check
                        if 8 <= val <= 16384:
                            return val
                    except Exception:
                        pass

        # Default fallback
        return 1536
