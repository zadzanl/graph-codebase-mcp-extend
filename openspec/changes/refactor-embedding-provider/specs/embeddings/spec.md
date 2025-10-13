## MODIFIED Requirements

### Requirement: Configurable Embedding Provider
The system SHALL allow users to configure the embedding provider via environment variables.

#### Scenario: Default OpenAI provider
- **GIVEN** no embedding provider is specified
- **WHEN** the application starts
- **THEN** the system SHALL use the default OpenAI provider with the `OPENAI_API_KEY`.

#### Scenario: Generic OpenAI-compatible provider
- **GIVEN** `EMBEDDING_PROVIDER` is set to `generic`
- **AND** `EMBEDDING_API_BASE_URL`, `EMBEDDING_MODEL_NAME`, and `EMBEDDING_API_KEY` are configured
- **WHEN** embeddings are generated
- **THEN** the system SHALL make requests to the specified base URL.

#### Scenario: No provider configured
- **GIVEN** no embedding API key is provided
- **WHEN** the application starts
- **THEN** the embedding step SHALL be disabled and a warning logged.

## ADDED Requirements

### Requirement: Robust Error Handling
The embedding provider SHALL handle API errors gracefully.

#### Scenario: Rate limit error
- **WHEN** the embedding API returns a rate limit error (HTTP 429)
- **THEN** the system SHALL retry the request with exponential backoff.

#### Scenario: Input size limit exceeded
- **WHEN** a code chunk exceeds the model's token limit
- **THEN** the system SHALL truncate the input and log a warning before generating the embedding.
