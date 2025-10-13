## 1. Abstracted Embedding Provider
- [ ] 1.1. Define the `EmbeddingProvider` abstract base class in `src/embeddings/base.py`.
- [ ] 1.2. Implement the `OpenAICompatibleProvider` in `src/embeddings/openai_compatible.py`, using the `openai` library to connect to a configurable endpoint.
- [ ] 1.3. Implement a factory function `get_embedding_provider` in `src/embeddings/factory.py` that reads environment variables and returns the appropriate provider.

## 2. Integration
- [ ] 2.1. Modify `src/embeddings/embedder.py` to use the `get_embedding_provider` factory.
- [ ] 2.2. Add robust error handling for rate limits, API errors, and input size limits.
- [ ] 2.3. Ensure backward compatibility by defaulting to the original OpenAI provider if no new configuration is provided.

## 3. Documentation
- [ ] 3.1. Update `README.md` to document the new environment variables for configuring the embedding provider.
