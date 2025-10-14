import os
from .base import EmbeddingProvider
from .openai_compatible import OpenAICompatibleProvider

def get_embedding_provider() -> EmbeddingProvider:
    provider = os.environ.get("EMBEDDING_PROVIDER", "openai").lower()
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")

    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = "https://api.openai.com/v1"
        api_key_name = "OPENAI_API_KEY"
    elif provider == "google":
        api_key = os.environ.get("GEMINI_API_KEY")
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        api_key_name = "GEMINI_API_KEY"
    elif provider == "deepinfra":
        api_key = os.environ.get("DEEPINFRA_API_KEY")
        base_url = "https://api.deepinfra.com/v1/openai"
        api_key_name = "DEEPINFRA_API_KEY"
    else: # Generic OpenAI-compatible
        api_key = os.environ.get("EMBEDDING_API_KEY")
        base_url = os.environ.get("EMBEDDING_API_BASE_URL")
        api_key_name = "EMBEDDING_API_KEY"

    if not api_key:
        raise ValueError(f"Required environment variable {api_key_name} is not set.")

    if not base_url:
        raise ValueError("EMBEDDING_API_BASE_URL must be set for generic providers.")

    return OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model, api_key_name=api_key_name)
