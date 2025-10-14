from typing import List, Optional
import os
from .base import EmbeddingProvider
from .openai_compatible import OpenAICompatibleProvider


class OpenAIEmbeddings(EmbeddingProvider):
    """Compatibility wrapper exposing a simple OpenAI-like embeddings API.

    This wrapper enforces an api_key requirement on init (matching existing
    tests' expectations) and delegates actual embedding work to
    OpenAICompatibleProvider.
    """

    def __init__(self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None):
        if not api_key:
            raise ValueError("API key is required to initialize OpenAIEmbeddings")

        base_url = base_url or os.environ.get("EMBEDDING_API_BASE_URL") or os.environ.get("OPENAI_API_BASE") or "https://api.openai.com/v1"
        model = model or os.environ.get("EMBEDDING_MODEL") or "text-embedding-3-small"

        # Use the OpenAI-compatible provider under the hood
        self._provider = OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model, api_key_name="OPENAI_API_KEY")

    @property
    def dimension(self) -> int:
        return self._provider.dimension

    def embed_text(self, text: str) -> List[float]:
        return self._provider.embed_text(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return self._provider.embed_batch(texts)


class CodeEmbedder:
    """Processor for generating embeddings for code elements.

    The CodeEmbedder formats code snippets with their node type and name
    before delegating to the underlying embedding provider.
    """

    def __init__(self, provider: EmbeddingProvider):
        self.provider = provider

    def prepare_code_text(self, code_text: str, node_type: str, name: str) -> str:
        """Prepare a code snippet for embedding by adding context about the node."""
        return f"{node_type} {name}:\n{code_text}"

    def embed_code_node(self, code_text: str, node_type: str, name: str) -> List[float]:
        prepared = self.prepare_code_text(code_text, node_type, name)
        return self.provider.embed_text(prepared)

    def embed_code_nodes_batch(self, code_texts: List[str], node_types: List[str], names: List[str]) -> List[List[float]]:
        if not (len(code_texts) == len(node_types) == len(names)):
            raise ValueError("code_texts, node_types, and names must have the same length")

        prepared = [self.prepare_code_text(c, t, n) for c, t, n in zip(code_texts, node_types, names)]
        return self.provider.embed_batch(prepared)