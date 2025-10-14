import os
import sys
import types
import pytest
import dotenv

# Ensure project root is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv.load_dotenv()

from src.embeddings.openai_compatible import OpenAICompatibleProvider  # noqa: E402
from src.embeddings.embedder import CodeEmbedder, OpenAIEmbeddings  # noqa: E402


@pytest.mark.parametrize(
    "model,base_url,expected_dim",
    [
        ("text-embedding-3-small", "https://api.openai.com/v1", 1536),
        ("Qwen/Qwen3-Embedding-0.6B", "https://api.deepinfra.com/v1/openai", 1024),
        ("google/embeddinggemma-300m", "https://api.deepinfra.com/v1/openai", 768),
        ("text-embedding-004", "https://generativelanguage.googleapis.com/v1beta/openai/", 768),
        ("gemini-embedding-001", "https://generativelanguage.googleapis.com/v1beta/openai/", 3072),
    ],
)
def test_openai_compatible_provider_basic_behavior(model, base_url, expected_dim):
    """Verify that the provider sends the expected request fields and returns
    vectors with the documented dimensionality (or the configured dimensionality).
    """

    provider = OpenAICompatibleProvider(api_key="test_key", base_url=base_url, model=model, api_key_name="TEST_KEY")

    # Replace the real HTTP client with a lightweight mock that records kwargs
    recorded = {}

    def create_side_effect(*args, **kwargs):
        # record the last kwargs so we can assert on them
        recorded.update(kwargs)
        inp = kwargs.get("input") or []
        if isinstance(inp, str):
            return types.SimpleNamespace(data=[types.SimpleNamespace(embedding=[0.1] * expected_dim, index=0)], usage=types.SimpleNamespace(prompt_tokens=1))

        # batch case: return a matching embedding per (filtered) input
        data = []
        for i, item in enumerate(inp):
            data.append(types.SimpleNamespace(index=i, embedding=[0.1 * (i + 1)] * expected_dim))
        return types.SimpleNamespace(data=data)

    # assign mock client bypassing static type checks
    object.__setattr__(provider, "client", types.SimpleNamespace(embeddings=types.SimpleNamespace(create=create_side_effect)))

    # Single text embedding
    emb = provider.embed_text("Hello world")
    assert isinstance(emb, list)
    assert len(emb) == expected_dim
    assert recorded.get("model") == model
    assert recorded.get("encoding_format") == "float"

    # Batch embeddings should preserve input order and produce zero-vectors for empty strings
    recorded.clear()
    inputs = ["First text", "", "Third text"]
    batch = provider.embed_batch(inputs)
    assert len(batch) == len(inputs)
    assert len(batch[0]) == expected_dim
    assert len(batch[2]) == expected_dim
    # the empty string should be mapped to a zero-vector of the provider's dimension
    assert len(batch[1]) == expected_dim
    assert all(v == 0.0 for v in batch[1])
    assert recorded.get("model") == model
    assert recorded.get("encoding_format") == "float"

    # Ensure CodeEmbedder uses the provider and returns consistent dimensions
    code_embedder = CodeEmbedder(provider)
    code_emb = code_embedder.embed_code_node("def f(): pass", "Function", "f")
    assert isinstance(code_emb, list)
    assert len(code_emb) == expected_dim

    batch_codes = ["def f(): pass", "class C: pass"]
    node_types = ["Function", "Class"]
    names = ["f", "C"]
    code_batch = code_embedder.embed_code_nodes_batch(batch_codes, node_types, names)
    assert len(code_batch) == 2
    assert all(len(x) == expected_dim for x in code_batch)


def test_openai_embeddings_wrapper_requires_api_key():
    with pytest.raises(ValueError):
        OpenAIEmbeddings(api_key="")