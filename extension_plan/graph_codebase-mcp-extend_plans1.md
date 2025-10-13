# graph-codebase-mcp v2.0: Product Requirement Document and Technical Specification

## Part 1: Product Requirement Document (PRD)

### 1.0 Vision and Strategic Context

#### 1.1 Executive Summary

This document provides the comprehensive product requirements and detailed technical specifications for the second major iteration of `graph-codebase-mcp`, designated as v2.0. The central objective of this evolution is to transform the tool from a specialized, Python-centric utility into a versatile, high-performance, and extensible code intelligence platform. This strategic enhancement is designed to meet the demands of modern software development, where polyglot codebases are the norm, and to significantly broaden the tool's utility within the rapidly expanding ecosystem of AI-powered developer assistants.

The core feature set for v2.0 includes:

1. **Multi-Language Support:** Extending analysis capabilities beyond Python to include comprehensive support for TypeScript and JavaScript, including JSX and TSX variants.
2. **Pluggable Embedding Architecture:** Decoupling the semantic embedding functionality from its current hardcoded dependency on OpenAI, allowing users to configure alternative providers.
3. **High-Throughput Parallel Indexing:** Re-architecting the file processing pipeline to leverage modern concurrency models, drastically reducing the time required to index large-scale codebases.

By implementing these features, `graph-codebase-mcp` v2.0 will deliver a more powerful, flexible, and scalable solution for generating rich, contextual knowledge graphs from source code, making it an indispensable tool for both human developers and AI agents.

#### 1.2 Strategic Alignment

The `graph-codebase-mcp` project is strategically positioned within the burgeoning field of AI-assisted software development. Its foundation is the Model Context Protocol (MCP), an open standard introduced by Anthropic and rapidly adopted by industry leaders like OpenAI and Google to standardize how AI models interact with external tools and data sources. By adhering to the MCP standard, `graph-codebase-mcp` functions as a powerful, local context server, enabling AI agents within compatible IDEs and desktop applications (e.g., VS Code, Cursor, Claude Desktop) to access deep, structural knowledge about a user's codebase.

The current landscape of MCP servers for code analysis includes projects that already offer multi-language support and advanced features like real-time file monitoring. To remain competitive and best-in-class, `graph-codebase-mcp` must evolve. The enhancements proposed in this document—specifically the expansion to the widely used TypeScript/JavaScript ecosystem, the introduction of a flexible embedding provider model, and a significant boost in indexing performance—are critical for addressing the practical needs of modern development teams and solidifying the project's position as a leading open-source solution in this domain.

### 2.0 Feature Requirements and User Stories

#### 2.1 Feature: Multi-Language Codebase Analysis (TypeScript/JavaScript)

- **Description:** The system's code analysis and graph construction capabilities will be extended to fully support TypeScript (`.ts`, `.tsx`) and JavaScript (`.js`, `.jsx`) files. The parser must accurately identify and model key language constructs, including functions, classes, interfaces, enums, imports, exports, and their relationships, creating a unified knowledge graph that seamlessly integrates with the existing Python analysis.
- **User Story 1 (Full-Stack Developer):** "As a full-stack developer working on a monorepo with a React frontend written in TypeScript and a Django backend in Python, I want to index my entire project to generate a single, unified knowledge graph. This will empower my AI assistant to trace a user action from a frontend component, through the API call it makes, to the specific backend endpoint and database model it interacts with. This capability is crucial for understanding the full data flow, performing impact analysis, and debugging complex cross-language issues."
- **User Story 2 (Frontend Team Lead):** "As the lead of a frontend team maintaining a large-scale Next.js application, I need to analyze our component hierarchy, state management patterns, and type dependencies. I require the tool to deeply understand TypeScript constructs like interfaces, enums, and decorators. This will enable me to ask my AI agent sophisticated queries such as, 'Show me all components that implement the `WithAnalytics` interface,' 'Find all usages of the `UserRole` enum across the application,' or 'Trace the inheritance chain for our `BaseController` class'."
- **User Story 3 (AI Agent):** "As an AI coding agent tasked with refactoring a legacy JavaScript codebase to TypeScript, I need access to a complete graph of the existing code. This graph must accurately represent function calls, module dependencies (`require` and `import`), and prototype-based inheritance, allowing me to identify dead code, understand component relationships, and safely execute the migration task."

#### 2.2 Feature: Pluggable Embedding Architecture

- **Description:** The semantic embedding generation module will be refactored to eliminate the hardcoded dependency on the OpenAI API. The system must provide a configuration-driven mechanism for selecting an embedding provider, supporting any service that adheres to an OpenAI-compatible API specification, as well as providing a clear interface for future expansion.
- **User Story 1 (Enterprise Architect):** "As an enterprise architect, our corporate policy strictly prohibits sending proprietary source code or its derivatives to external third-party services for security and intellectual property reasons. I need to configure `graph-codebase-mcp` to use our company's internal, self-hosted embedding model, which exposes an OpenAI-compatible API endpoint. This will allow our development teams to benefit from powerful semantic code search capabilities without violating data governance and security protocols."
- **User Story 2 (MLOps Engineer):** "As an MLOps engineer focused on code intelligence, I am constantly benchmarking different embedding models for their effectiveness in code similarity and retrieval tasks. I require the flexibility to seamlessly switch between various providers—such as OpenAI's latest models, Google's Gemini embeddings, and open-source models hosted on platforms like DeepInfra or Together AI. I must be able to change the active provider by simply updating environment variables for the API base URL, model name, and API key, without needing to modify or re-deploy the `graph-codebase-mcp` server itself."
- **User Story 3 (Open-Source Contributor):** "As a contributor to an open-source project, I want to use `graph-codebase-mcp` without being forced to have a paid OpenAI account. I want to configure the tool to use a freely available, locally running embedding model (e.g., via LM Studio or Ollama) that provides an OpenAI-compatible endpoint. This lowers the barrier to entry and makes the tool more accessible to the wider developer community."

#### 2.3 Feature: High-Throughput Parallel Indexing

- **Description:** The codebase indexing process will be re-architected to perform file parsing, embedding generation, and database ingestion in parallel. The system should efficiently utilize multi-core processors to significantly reduce the total time required to build the knowledge graph for large and very large codebases.
- **User Story 1 (New Developer Onboarding):** "As a developer joining a new team with a legacy codebase spanning several million lines of code, my first task is to understand its architecture. I want to run the `graph-codebase-mcp` indexing process and have a complete, queryable knowledge graph available in minutes, not hours. The tool must leverage all the cores on my development machine to make this initial onboarding step as fast as possible, enabling me to start asking meaningful questions and contributing productively on my first day."
- **User Story 2 (CI/CD Pipeline Maintainer):** "As a DevOps engineer, I am integrating `graph-codebase-mcp` into our continuous integration pipeline to generate a fresh knowledge graph artifact for every major release. This artifact is used for automated code quality checks and documentation generation. The indexing process must be highly efficient and complete within the strict time budget of our CI pipeline to avoid becoming a bottleneck that slows down deployments."
- **User Story 3 (Lead Engineer):** "As a lead engineer on a large project, I periodically need to re-index the entire repository from scratch to incorporate major refactoring changes. I need this process to be a fast, 'fire-and-forget' operation that I can run in the background without monopolizing my system's resources for an extended period, allowing me to continue with other development tasks."

## Part 2: Technical Specification and Implementation Blueprint

### 3.0 Evolved System Architecture

#### 3.1 Current Architecture (v1.0)

The existing `graph-codebase-mcp` architecture is a monolithic Python application with a sequential, language-specific workflow. A detailed analysis of the current codebase reveals the following modular structure and data flow:

- **Codebase Structure:**
    - **AST Parser (`src/ast_parser/parser.py`):** Uses Python's built-in `ast` module to parse Python files and extract entities like classes, functions, and imports. This is the primary component limiting multi-language support.
    - **Embeddings (`src/embeddings/`):** Handles generating vector embeddings for code elements using a hardcoded dependency on the OpenAI API (e.g., `text-embedding-ada-002`).
    - **Neo4j Storage (`src/neo4j_storage/`):** Manages the connection to a Neo4j database and persists the code graph using Cypher queries. The schema includes nodes like `Module`, `Class`, `Function` and relationships such as `IMPORTS_FROM`, `EXTENDS`, and `CALLS`.
    - **MCP Server (`src/mcp/` and `src/mcp_server.py`):** Implements an MCP-compliant server that exposes the graph to AI agents via standardized tools (e.g., 'search code', 'find callers').
    - **Main Entrypoint (`src/main.py`):** Orchestrates the indexing pipeline: walking the codebase path, filtering for `.py` files, and coordinating the parsing, embedding, and storage steps.
    - **Configuration:** Relies on environment variables (`NEO4J_URI`, `OPENAI_API_KEY`, etc.), typically loaded from a `.env` file.

- **Data Flow:** The current data flow is linear: a Python code file is parsed by the `ast` module, the extracted entities are sent for embedding via the OpenAI API, and the resulting nodes and relationships are stored in Neo4j. The MCP server then queries this graph to respond to agent requests.

    ```mermaid
    flowchart LR
        A[Source Code Files] -->|AST parse| B(Python AST Parser)
        B -->|extracts entities & relations| C[Neo4j GraphDB]
        C -->|store nodes & relationships| C
        C -->|MCP query (Cypher)| D[MCP Server]
        D -->|answers agent queries| D
    ```

- **Limitations and Technical Debt:**
    - **Language Support:** The system is functionally limited to Python, as other language parsers are not implemented.
    - **Performance:** The process is entirely sequential, making it slow for large codebases. There is no caching or incremental update logic; every run rebuilds the graph from scratch.
    - **Error Handling:** The existing error handling for parsing or API failures is not explicitly detailed and may not be robust.

#### 3.2 Proposed Architecture (v2.0)

The v2.0 architecture introduces modularity, abstraction, and concurrency to address the new requirements. The system will be refactored into a set of distinct, loosely coupled components orchestrated by a parallel processing manager.

- **Core Application & Orchestration:** The main entry point will initialize a `ProcessingPoolManager` and create a queue of file paths to be processed.
- **Universal Parsing Engine:** A new, abstracted `Parser` module will serve as the central point for code analysis. It will contain a factory that, based on a file's extension, returns a language-specific parser instance. Each of these instances will be built upon the **Tree-sitter** parsing framework, providing a consistent interface for syntax tree traversal and querying across all supported languages.
- **Abstracted Embedding Provider:** All embedding logic will be encapsulated behind a standardized `EmbeddingProvider` interface. A factory function will be responsible for instantiating the correct provider implementation (e.g., `OpenAIProvider`, `GenericOpenAICompatibleProvider`) based on external configuration. This design completely decouples the core application logic from any specific embedding service.
- **Parallel Processing Core:** A `ProcessingPoolManager` will manage a `concurrent.futures.ThreadPoolExecutor` (for Python 3.14+ free-threaded builds) or a `ProcessPoolExecutor` (as a fallback). It will be responsible for distributing file processing tasks (parsing, embedding, and graph ingestion) across a pool of worker processes or threads, dramatically improving throughput.
- **Thread-Safe Database Interface:** The application will maintain a single, global `neo4j.Driver` instance, which is thread-safe and manages the underlying connection pool. Each worker in the processing pool will be responsible for acquiring and releasing its own short-lived, non-shared `Session` object from the driver for its database transactions, ensuring concurrent database access is handled safely and correctly.

### 4.0 Universal Parsing Engine: Implementation with Tree-sitter

#### 4.1 Rationale for Tree-sitter Selection

The decision to adopt Tree-sitter as the universal parsing engine is the most critical architectural choice for v2.0. The existing implementation's reliance on Python's native `ast` module is a dead end for multi-language support, as it is fundamentally incapable of parsing any language other than Python. A complete replacement of the parsing strategy is therefore not just recommended but necessary.

Tree-sitter is a parser generator tool and incremental parsing library designed specifically for this type of use case. It is engineered to be general enough to parse any programming language, fast enough for real-time applications, and robust enough to handle syntax errors gracefully. The availability of official Python bindings (`py-tree-sitter`) and mature, well-maintained grammars for JavaScript and TypeScript makes it the ideal choice.

This architectural shift from a language-specific parser to a generic parsing framework provides a crucial, second-order benefit: future extensibility. By abstracting the parsing logic behind a consistent interface powered by Tree-sitter, the system becomes "language-pluggable." Adding support for new languages like Go, Rust, or Java in the future will no longer require re-architecting the core application. Instead, it will be a far simpler process of integrating the relevant Tree-sitter grammar and defining the corresponding set of extraction queries. This decision future-proofs the tool and positions it for long-term scalability and relevance in a polyglot world.

#### 4.2 Integration and Setup

The project's dependencies and setup process will be updated to incorporate the Tree-sitter ecosystem.

1. **Dependency Management:** The `requirements.txt` file will be updated to include the core `tree-sitter` library and the pre-compiled grammar packages for each supported language:
	```markdown
	tree-sitter>=0.25.0
	tree-sitter-python>=0.25.0
	tree-sitter-javascript>=0.25.0
	tree-sitter-typescript>=0.23.0
	```
	These packages provide binary wheels for all major platforms, eliminating the need for local C compilers or Node.js during installation for most users.
2. **Parser Factory:** A parser factory will be implemented to manage the loading and instantiation of language-specific parsers. This ensures that grammars are loaded only once and parsers are efficiently reused.
	Python
	```markdown
	# src/parsing/factory.py
	from tree_sitter import Language, Parser
	import tree_sitter_python as tspython
	import tree_sitter_javascript as tsjavascript
	import tree_sitter_typescript as tstypescript
	# Load languages once at module level
	PY_LANGUAGE = Language(tspython.language())
	JS_LANGUAGE = Language(tsjavascript.language())
	# The typescript package provides two grammars: 'typescript' and 'tsx'
	TS_LANGUAGE = Language(tstypescript.language_typescript())
	TSX_LANGUAGE = Language(tstypescript.language_tsx())
	LANGUAGES = {
	    '.py': PY_LANGUAGE,
	    '.js': JS_LANGUAGE,
	    '.jsx': JS_LANGUAGE, # The JS grammar handles JSX
	    '.ts': TS_LANGUAGE,
	    '.tsx': TSX_LANGUAGE,
	}
	def get_parser(file_extension: str) -> Parser | None:
	    """Returns a configured Tree-sitter parser for a given file extension."""
	    language = LANGUAGES.get(file_extension)
	    if language is None:
	        return None
	    parser = Parser()
	    parser.set_language(language)
	    return parser
	```

#### 4.3 Entity and Relationship Extraction via Tree-sitter Queries

The core parsing logic will transition from traversing Python `ast` nodes to executing structured queries against the Concrete Syntax Tree (CST) generated by Tree-sitter. This approach is more declarative, robust, and maintainable. The `py-tree-sitter` library's `Language.query()` method will be used to compile S-expression patterns, and the resulting query object will be used to find all matching nodes in a given syntax tree.

The following table serves as the definitive specification for extracting key language constructs from JavaScript and TypeScript code. It provides the precise node types and capture queries required by the engineering team, eliminating ambiguity and standardizing the extraction process.

**Table 1: Tree-sitter Queries for TypeScript/JavaScript Constructs**

| Construct | Language(s) | Tree-sitter Node Type(s) | Query |
| --- | --- | --- | --- |
| Function Declaration | JS, TS | `function_declaration` | `(function_declaration name: (identifier) @name) @function` |
| Arrow Function (Variable) | JS, TS | `lexical_declaration` > `variable_declarator` > `arrow_function` | `(lexical_declaration (variable_declarator name: (identifier) @name value: (arrow_function))) @function.arrow` |
| Class Declaration | JS, TS | `class_declaration` | `(class_declaration name: (type_identifier) @name) @class` |
| Import Statement | JS, TS | `import_statement` | `(import_statement source: (string) @source) @import` |
| Named Imports | JS, TS | `import_specifier` | `(import_statement (import_clause (named_imports (import_specifier name: (property_identifier) @name))))` |
| Default Import | JS, TS | `import_clause` > `identifier` | `(import_statement (import_clause (identifier) @default)) ` |
| Namespace Import | JS, TS | `namespace_import` | `(import_statement (import_clause (namespace_import (identifier) @namespace)))` |
| Dynamic Import | JS, TS | `import_expression` | `(call_expression function: (import_expression) arguments: (arguments (string) @source)) @import.dynamic` |
| Export Statement | JS, TS | `export_statement` | `(export_statement declaration: _ @declaration) @export` |
| Default Export | JS, TS | `export_statement` with `default` | `(export_statement value: _ @value "default") @export.default` |
| Interface Declaration | TS | `interface_declaration` | `(interface_declaration name: (type_identifier) @name) @interface` |
| Enum Declaration | TS | `enum_declaration` | `(enum_declaration name: (identifier) @name) @enum` |
| Type Alias Declaration | TS | `type_alias_declaration` | `(type_alias_declaration name: (type_identifier) @name) @type.alias` |
| Decorator | TS | `decorator` | `(decorator name: (identifier) @name) @decorator` |
| Namespace Declaration | TS | `module` (for `namespace`) or `internal_module` | `(module name: [ (identifier) (nested_identifier) ] @name) @namespace` |
| Function/Method Call | JS, TS | `call_expression` | `(call_expression function: [(identifier) @function.call (member_expression property: (property_identifier) @function.call)])` |

#### 4.4 AST Traversal and Element Extraction

After parsing a source file with Tree-sitter, the resulting Concrete Syntax Tree (CST) will be traversed to extract code entities and their relationships. This process will be implemented in a new `JavaScriptParser` or `TypeScriptParser` class. The logic will navigate the tree, identify nodes corresponding to the constructs defined in the query table above, and create a structured representation of the file's contents.

The following pseudo-code illustrates the traversal logic:

```python
def extract_elements(tree, source_code_bytes):
    root = tree.root_node
    elements = {"functions": [], "classes": [], "imports": [], "exports": []}

    def traverse(node, parent_class=None):
        # Example for function_declaration
        if node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            func_name = name_node.text.decode('utf8') if name_node else "<anonymous>"
            # ... more extraction logic for params, return type, etc.
            elements["functions"].append({
                "name": func_name,
                "parent_class": parent_class,
                # ... other properties
            })

        # Example for class_declaration
        elif node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            class_name = name_node.text.decode('utf8') if name_node else "<anonymous>"
            elements["classes"].append({"name": class_name})
            # Recursively traverse children to find methods
            body_node = node.child_by_field_name("body")
            if body_node:
                for child in body_node.children:
                    traverse(child, parent_class=class_name)

        # Example for import_statement
        elif node.type == "import_statement":
            source_node = node.child_by_field_name("source")
            module_source = source_node.text.decode('utf8') if source_node else ""
            # ... logic to extract named imports from import_clause
            elements["imports"].append({"module": module_source, "names": [...]})

        # Recursively traverse all other children
        else:
            for child in node.children:
                # Avoid re-traversing class bodies handled above
                if not (node.type == "class_declaration" and child.type == "class_body"):
                    traverse(child, parent_class)

    traverse(root)
    return elements
```

**Note on Out-of-Scope Items:**
To ensure a focused initial implementation, the following will be explicitly excluded from this phase but documented for future enhancement:
- **JSX/TSX:** While the parsers can handle the syntax, specific logic to interpret JSX elements and component hierarchies will be deferred.
- **CommonJS:** Analysis of `require()` calls and `module.exports` patterns will be excluded in favor of focusing on modern ES6+ `import`/`export` syntax.
- **Deep Type Resolution:** The parser will not perform full type checking or flow analysis. It will rely on explicit import statements to establish cross-file relationships.

### 5.0 Abstracted Embedding Provider Framework

#### 5.1 Rationale and Interface Definition

To fulfill the requirement for a configurable embedding provider, the architecture must move away from a direct dependency on the `openai` library. A naive approach would involve writing bespoke client implementations for each potential service, creating a significant maintenance burden and an "N×M" integration problem where every new provider requires custom code.

A more strategic and scalable solution is to leverage the industry trend of providers offering OpenAI-compatible API endpoints. Services such as Google Gemini, DeepInfra, and Together AI provide drop-in replacements for the OpenAI API, typically requiring only a change of the base URL and API key.

By standardizing the internal application interface on the OpenAI `/v1/embeddings` API specification, we create a powerful abstraction. This allows the system to support a wide range of current and future embedding services with a single, generic client implementation. Adding a new OpenAI-compatible provider becomes a zero-code-change configuration task for the end-user, dramatically simplifying integration and enhancing the tool's flexibility.

An abstract base class, `EmbeddingProvider`, will define the contract for all embedding implementations. Its method signature will mirror the essential components of the `openai.embeddings.create` method.

Python

```markdown
# src/embeddings/base.py
from abc import ABC, abstractmethod
from typing import List

class EmbeddingProvider(ABC):
    @abstractmethod
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a list of text strings.

        Args:
            texts: A list of strings to be embedded.

        Returns:
            A list of embedding vectors, where each vector is a list of floats.
        """
        pass
```

#### 5.2 Configuration and Factory Implementation

The application's configuration, loaded from a `.env` file or `mcp.json`, will be extended to support the new embedding architecture.

- **Configuration Variables:**
	- `EMBEDDING_PROVIDER`: (Optional) A string identifier for the provider (e.g., `openai`, `deepinfra`, `generic`). Defaults to `openai`.
	- `EMBEDDING_MODEL`: The specific model name required by the provider (e.g., `text-embedding-3-small`, `BAAI/bge-large-en-v1.5`).
	- `EMBEDDING_API_BASE`: (Optional) The base URL for the API endpoint. If not provided, the default for the specified provider will be used.
	- `EMBEDDING_API_KEY`: The authentication key for the embedding service.

A factory function will be responsible for interpreting this configuration and instantiating the appropriate provider.

Python

```markdown
# src/embeddings/factory.py
from.base import EmbeddingProvider
from.openai_compatible import OpenAICompatibleProvider

def get_embedding_provider(config: dict) -> EmbeddingProvider:
    """Instantiates and returns the configured embedding provider."""
    provider_name = config.get("EMBEDDING_PROVIDER", "openai").lower()
    api_key = config
    model = config
    
    if provider_name == "openai":
        base_url = config.get("EMBEDDING_API_BASE", "https://api.openai.com/v1")
    elif provider_name == "deepinfra":
        base_url = config.get("EMBEDDING_API_BASE", "https://api.deepinfra.com/v1/openai")
    else: # Generic OpenAI-compatible
        base_url = config

    return OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model)
```

The `OpenAICompatibleProvider` will use the official `openai` Python library, configured with the custom `base_url` and `api_key`, to make requests.

Python

```markdown
# src/embeddings/openai_compatible.py
from openai import OpenAI, RateLimitError
import time
from.base import EmbeddingProvider

class OpenAICompatibleProvider(EmbeddingProvider):
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def create_embeddings(self, texts: list[str]) -> list[list[float]]:
        # Implementation should include error handling and retry logic
        # for rate limits, as recommended by OpenAI's best practices.
        try:
            response = self.client.embeddings.create(input=texts, model=self.model)
            return [item.embedding for item in response.data]
        except RateLimitError as e:
            # Implement exponential backoff retry logic here
            print(f"Rate limit exceeded. Retrying... Error: {e}")
            time.sleep(5) # Simplified for example
            return self.create_embeddings(texts)
        except Exception as e:
            print(f"An error occurred during embedding creation: {e}")
            return [[] for _ in texts]

#### 5.3 Provider-Specific Considerations and Error Handling

The embedding provider implementation must be robust and handle provider-specific nuances and potential failures gracefully.

- **Backward Compatibility:** If no new embedding variables are set, the system will default to `EMBEDDING_PROVIDER="openai"` and use the existing `OPENAI_API_KEY`, ensuring current setups continue to work without modification.
- **Error Handling:**
    - **Rate Limits:** The client must catch rate limit errors (e.g., `openai.RateLimitError`, HTTP 429) and implement a retry mechanism with exponential backoff.
    - **Authentication:** Invalid API key errors (HTTP 401/403) should be handled by logging a clear error message and aborting the indexing process.
    - **Network Failures:** Connection timeouts and other network errors should also be handled with a retry strategy.
    - **Input Size Limits:** Embedding models have token limits (e.g., 8191 for `text-embedding-ada-002`). The client must check the size of the input text and, if it exceeds the model's limit, either truncate it or skip embedding that specific code chunk, logging a warning in either case.
- **Provider-Specific Behavior:**
    - **DeepInfra:** Some providers like DeepInfra may have different default response formats (e.g., base64 instead of float arrays). While the `openai` library is the primary interface, a fallback using the `requests` library may be necessary to explicitly request the `float` encoding format if the default proves problematic.
    - **Azure:** Support for Azure OpenAI Service requires additional configuration parameters (`api_type`, `api_version`, `deployment_id`) which can be incorporated into the factory logic.
- **Optional Embeddings:** If no API key is provided, the system should not fail. Instead, it should disable the embedding step, log a warning that semantic search capabilities will be unavailable, and proceed with building the structural graph.
```

### 6.0 High-Concurrency Processing Model

#### 6.1 Concurrency Strategy: Free-Threading First, Multiprocessing as Fallback

The primary performance bottleneck during indexing is the parsing of source code files—a CPU-bound task. Traditional Python threading is ineffective for such tasks due to the Global Interpreter Lock (GIL), which prevents multiple threads from executing Python bytecode simultaneously. This has historically forced developers into using the `multiprocessing` module, which, while effective, comes with significant overhead related to process creation, memory duplication, and inter-process communication (IPC).

A more advanced and efficient approach is to leverage the new free-threading capabilities of modern Python. With the acceptance of PEP 779, the free-threaded (no-GIL) build of CPython is officially supported as of Python 3.14. Benchmarks demonstrate that this build offers substantial performance gains (often 2-3x or more) for multi-threaded, CPU-bound workloads by allowing true parallel execution on multi-core systems. This directly addresses the project's core performance requirement.

Therefore, the primary concurrency strategy will be to use a `concurrent.futures.ThreadPoolExecutor` when running on a free-threaded Python 3.14+ interpreter. This model offers the lowest overhead and most efficient memory sharing. To maintain compatibility with older, GIL-bound Python versions, the implementation will include a fallback mechanism that uses a `concurrent.futures.ProcessPoolExecutor`. This dual strategy ensures optimal performance on modern runtimes while preserving broad usability.

**Caveat on C Extensions:** A critical consideration is that the performance benefits of free-threading depend on the thread-safety of C extension modules. If a C extension used by the application (e.g., the `tree-sitter` bindings) is not marked as free-thread safe, the interpreter may re-enable the GIL when calling into it, effectively serializing execution and negating the benefits of multi-threading for that task. The implementation must include runtime detection of the GIL status (`sys._is_gil_enabled()`) and log a warning if free-threading is expected but not fully available. The performance of parallel parsing will be validated to ensure it scales as expected.

#### 6.2 Thread-Safe Database Operations

A multi-threaded architecture requires strict adherence to thread-safe practices for database interactions. The official Neo4j Python driver documentation provides clear guidance: the main `neo4j.Driver` object is thread-safe and is designed to be instantiated once and shared across the entire application. It manages an internal connection pool. However, the `Session` objects obtained from the driver are **not** thread-safe and must not be shared between threads.

This dictates a mandatory implementation pattern to ensure data integrity and prevent connection state corruption:

1. A single, global `GraphDatabase.driver()` instance will be created at application startup and passed to the worker pool.
2. Each worker thread, upon receiving a task (e.g., processing a file), **must** acquire its own `Session` from the shared driver instance, typically using a `with driver.session() as session:` block.
3. All database operations for that task (e.g., running one or more transactions) must be performed using this thread-local session.
4. The session is automatically closed and its underlying connection is returned to the pool when the `with` block is exited.

This pattern isolates database communication on a per-thread basis, leveraging the driver's built-in connection pooling while guaranteeing safe concurrent operations.

Python

```markdown
# Example worker function demonstrating thread-safe session management
import os
from concurrent.futures import ThreadPoolExecutor
from neo4j import GraphDatabase

def process_file_worker(filepath: str, driver):
    """
    Worker function to parse a file and write to Neo4j.
    This function is executed in a separate thread.
    """
    try:
        # Each thread MUST create its own session.
        with driver.session(database="neo4j") as session:
            # 1. Parse the file using Tree-sitter
            # parsed_data = parse_file(filepath)
            
            # 2. Execute a managed transaction to write data
            # session.execute_write(write_data_to_graph, parsed_data)
            print(f"Processed {filepath} in thread {os.getpid()}")
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

# Main application logic
def run_indexing(file_paths: list[str], neo4j_uri, neo4j_auth):
    # Create ONE driver instance for the entire application
    with GraphDatabase.driver(neo4j_uri, auth=neo4j_auth) as driver:
        # Use a ThreadPoolExecutor for concurrency
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            # Submit tasks to the pool, passing the shared driver instance
            futures = [executor.submit(process_file_worker, path, driver) for path in file_paths]
            for future in futures:
                future.result() # Wait for all tasks to complete
```

#### 6.3 Performance Tuning and Configuration

To achieve maximum throughput, the concurrency settings must be tunable.

- **Worker Count:** The number of worker threads in the `ThreadPoolExecutor` should be configurable via an environment variable or command-line argument, with a sensible default of `os.cpu_count()`.
- **Connection Pool Size:** The Neo4j driver's connection pool size is a critical parameter. It is configured during the `GraphDatabase.driver()` instantiation via the `max_connection_pool_size` keyword argument. To prevent worker threads from being blocked while waiting for a database connection, this value **must** be set to at least the maximum number of worker threads. A recommended default is `os.cpu_count() * 2` to accommodate any ancillary connections, providing a buffer and ensuring the pool is never a bottleneck.

### 7.0 Graph Schema and Data Integrity

#### 7.1 Schema Extension

The existing graph schema, which includes nodes for `File`, `Class`, `Function`, and `Variable`, will be extended to natively represent key TypeScript constructs.

- **New Node Labels:**
	- `Interface`: Represents a TypeScript `interface` declaration.
	- `Enum`: Represents a TypeScript `enum` declaration.
	- `TypeAlias`: Represents a TypeScript `type` alias.
	- `Decorator`: Represents a TypeScript decorator.
	- `Namespace`: Represents a TypeScript `namespace` (or `module`).
- **New Relationship Types:**
	- `IMPLEMENTS`: Connects a `Class` node to an `Interface` node.
	- `HAS_DECORATOR`: Connects a `Class` or `Function` (method) node to a `Decorator` node.
	- `TYPE_DEPENDS_ON`: A generic relationship to link entities (e.g., a `Function` 's parameter) to a `TypeAlias` or `Interface`.

#### 7.2 Atomic Write Operations

In a concurrent processing environment where multiple threads are writing to the database simultaneously, ensuring data integrity and preventing race conditions is paramount. A naive approach using `CREATE` statements for new nodes or relationships is unsafe. For example, if two worker threads process files that both import from a common `utils.ts`, both might attempt to create the `(:File {path: 'path/to/utils.ts'})` node at the same time, leading to duplicate nodes or constraint violation errors.

The correct and required approach is to use Cypher's `MERGE` clause for all write operations that involve creating or finding entities. `MERGE` acts as an atomic "get-or-create" operation. It guarantees that a pattern will exist in the graph, either by matching an existing one or by creating a new one, all within a single, database-level atomic action. This makes the write operations idempotent—running the same `MERGE` statement multiple times has the exact same effect as running it once. This property is not only crucial for handling concurrency but also aligns with the Neo4j driver's best practice of using idempotent transaction functions to allow for safe, automatic retries on transient failures.

While the APOC library offers procedures like `apoc.atomic.update`, the standard `MERGE` clause is sufficient, more idiomatic for this use case, and does not require an external dependency.

- **Mandatory Cypher Pattern:** All Cypher queries that add nodes or relationships to the graph must use `MERGE`.
	- **Bad (Non-Atomic):**`CREATE (f:File {path: $path})`
	- **Good (Atomic & Idempotent):**`MERGE (f:File {path: $path})`
	- **Example for Relationship:**
		Cypher
		```markdown
		// Find or create the source and target nodes
		MERGE (source:Function {id: $source_id})
		MERGE (target:Function {id: $target_id})
		// Atomically create the relationship only if it doesn't already exist
		MERGE (source)-->(target)
		```

### 8.0 Future Architectural Considerations

To ensure the long-term viability and utility of the platform, the following architectural enhancements are planned for future iterations. The v2.0 implementation should lay the groundwork for these features where possible.

#### 8.1 Incremental Codebase Update Strategy

On large codebases, re-indexing the entire project after every change is inefficient. A robust incremental update strategy is required.

- **Change Detection:** The recommended method is file content hashing. On the initial scan, a SHA-256 hash of each file's content will be computed and stored as a `hash` property on the corresponding `:File` node in the graph. On subsequent runs, the tool will compare the current file hashes against the stored ones to detect new, modified, and deleted files.
- **Update Algorithm:**
    1.  **Scan:** Identify all current files in the codebase.
    2.  **Compare:** Retrieve all `:File` nodes and their hashes from Neo4j.
    3.  **Categorize:** Determine which files are new, modified, or deleted. Unchanged files are ignored.
    4.  **Execute:**
        -   **New Files:** Process and add to the graph as normal.
        -   **Deleted Files:** Remove the corresponding `:File` node and all its owned entities from the graph using a `DETACH DELETE` query.
        -   **Modified Files:** The simplest robust approach is to treat a modification as a deletion followed by an addition. The subgraph of entities belonging to the modified file will be deleted, and the file will be re-parsed and its new subgraph created.
- **Relationship Integrity:** The main challenge with incremental updates is maintaining the integrity of cross-file relationships (e.g., `CALLS`, `IMPORTS_FROM`). Deleting a node (like a function) will also delete all incoming relationships. A global linking step (e.g., re-resolving all `CALLS` and `IMPORTS` relationships) may be required after a batch of incremental updates to ensure the graph remains consistent.
- **Groundwork in v2.0:** The v2.0 implementation will facilitate this by storing the file hash on each `:File` node created.

#### 8.2 Real-Time Synchronization ("Watch Mode")

Building on the incremental update strategy, a "watch mode" will provide real-time graph synchronization.
- **Implementation:** Use the `watchdog` library to monitor the codebase for file system events (`on_created`, `on_modified`, `on_deleted`).
- **Event Handling:** Each event will trigger a targeted, incremental update for the affected file(s), providing a near-instantaneously consistent view of the codebase.

#### 8.3 Advanced Source Control Integration (Handling File Renames)

A simple file rename is often seen by file watchers as a `delete` and a `create` event, which would cause the node to lose its identity and relationships. A more robust solution involves Git integration.
- **Detection:** Use `git status` or `git diff` to detect file renames explicitly.
- **Update:** When a rename is detected, execute a Cypher query to update the `path` property of the existing `:File` node, preserving its identity and all existing relationships.
    ```cypher
    MATCH (f:File {path: $old_path})
    SET f.path = $new_path
    RETURN f
    ```
This maintains the historical integrity of code entities across refactoring operations.

### 9.0 Risk Assessment and Mitigation

A formal risk assessment is crucial for project success. The following risks have been identified, along with their mitigation strategies.

| Risk Category | Description | Mitigation Strategy |
| :--- | :--- | :--- |
| **High** | **Tree-sitter Parsing Gaps:** The Tree-sitter grammars, while robust, may not perfectly parse all edge cases in complex or legacy TypeScript/JavaScript codebases. | Perform comprehensive testing on a diverse set of real-world open-source projects. Implement graceful error handling to skip un-parsable files without crashing the entire indexing process. |
| **Medium** | **Neo4j Performance Under Load:** The free Neo4j Community Edition has connection and performance limits that could be reached during high-concurrency indexing of very large codebases. | Implement conservative connection pooling (e.g., pool size of 50), use batched write operations where possible, and conduct load testing against codebases with >10,000 files to identify bottlenecks. |
| **Medium** | **C Extension Thread-Safety:** The performance of the free-threaded model is contingent on C extensions like the Tree-sitter bindings being thread-safe. If they are not, the GIL may be re-enabled, negating performance gains. | Monitor the status of key dependencies in the Python 3.14 ecosystem. Implement the concurrency model with a fallback to `multiprocessing` to ensure performance gains regardless of the free-threading environment. |
| **Low** | **Python 3.14 Stability:** As a new feature, free-threading may have initial stability issues. | The feature is officially supported in Python 3.14. The implementation will include a graceful fallback to sequential or multiprocessing-based indexing for older Python versions or if issues are encountered. |

### 10.0 Implementation Roadmap and Validation

The project will be implemented in phases to manage complexity and allow for iterative testing.

- **Phase 1: Multi-Language AST Parsing (Est. 15-20 developer-days)**
    - Integrate Tree-sitter with parsers for JavaScript and TypeScript.
    - Develop a unified entity extraction layer that maps constructs from all supported languages to the graph schema.
    - Ensure backward compatibility with the existing Python `ast` parser.
- **Phase 2: Configurable Embedding Providers (Est. 10-12 developer-days)**
    - Implement the `EmbeddingProvider` abstraction layer.
    - Build and test the configuration system for selecting providers (OpenAI, DeepInfra, generic) via environment variables.
    - Implement robust error handling, rate limiting, and retry logic.
- **Phase 3: Parallel Processing Core (Est. 12-15 developer-days)**
    - Implement the `ThreadPoolExecutor` for parallel file processing, with detection for free-threaded Python.
    - Ensure all Neo4j operations are thread-safe using the recommended session management patterns.
    - Implement a fallback to `ProcessPoolExecutor` for GIL-bound Python versions.

**Validation Checkpoints:**
- **Parser Compatibility:** Test the Tree-sitter implementation against a wide variety of complex, real-world TypeScript and JavaScript codebases.
- **Provider Integration:** Verify API compatibility and successful embedding generation with OpenAI, DeepInfra, and a generic self-hosted OpenAI-compatible endpoint.
- **Threading Performance:** Benchmark the indexing speed of free-threaded Python vs. multiprocessing vs. sequential execution to validate performance gains.
- **Neo4j Scalability:** Load test the system with a large codebase to ensure the Neo4j Community Edition instance remains stable under concurrent writes.

### 11.0 Edge Cases and Error Handling

The system must be robust to a wide variety of real-world edge cases.

- **Parsing Edge Cases:**
    - **Syntax Errors:** Files with syntax errors will be detected by checking for `ERROR` nodes in the Tree-sitter CST. Such files will be skipped with a logged warning to prevent corrupting the graph.
    - **Large Files:** Files exceeding a configurable size threshold will be flagged. Their content may be truncated before embedding to avoid exceeding API token limits.
    - **File Encodings:** Files will be read as bytes and decoded as UTF-8, with replacement characters for any invalid sequences to prevent crashing on non-UTF8 files.
    - **Binary Files & Symlinks:** The file collection process will be restricted to specific file extensions (`.py`, `.js`, `.ts`, etc.) to avoid attempting to parse binary files. Directory traversal will not follow symbolic links to prevent infinite loops.
- **Embedding Edge Cases:**
    - **API Failures:** All API calls will be wrapped in error handling to catch rate limits, authentication failures, and network timeouts, with a retry-with-backoff strategy for transient errors.
    - **Token Limits:** Code snippets that are too long for the embedding model's context window will be skipped with a warning.
    - **Missing API Key:** If no embedding API key is provided, the embedding step will be skipped entirely, and the system will proceed to build a purely structural graph.
- **Neo4j Database Edge Cases:**
    - **Connection Failures:** The application will handle database connection errors gracefully at startup.
    - **Transaction Integrity:** By using `MERGE` for all node and relationship creation and managing sessions on a per-thread basis, the risk of race conditions and data duplication is minimized. Unique constraints will be created on `:File(path)` to guarantee integrity.
    - **Transaction Size:** By processing and committing data on a per-file basis, the system avoids creating excessively large transactions that could strain the database.