## Why
The current system has a hardcoded dependency on the OpenAI API for generating semantic embeddings. This limits user choice, creates vendor lock-in, and prevents users from using self-hosted or alternative embedding models. A pluggable architecture is needed to support a variety of embedding providers.

## What Changes
- **BREAKING**: Refactor the embedding generation module to use a provider-based architecture.
- Introduce an `EmbeddingProvider` abstract base class.
- Implement a generic `OpenAICompatibleProvider` that can connect to any OpenAI-compatible API endpoint.
- Create a factory function to instantiate the correct provider based on environment variables (`EMBEDDING_PROVIDER`, `EMBEDDING_API_BASE_URL`, `EMBEDDING_MODEL_NAME`, `EMBEDDING_API_KEY`).
- Update the core logic to use the new provider factory.

## Impact
- **Affected specs**: `embeddings`
- **Affected code**: `src/embeddings/embedder.py`, `src/main.py`
