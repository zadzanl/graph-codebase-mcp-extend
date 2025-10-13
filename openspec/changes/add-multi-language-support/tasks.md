## 1. Universal Parsing Engine
- [ ] 1.1. Integrate `tree-sitter` and `tree-sitter-typescript` into the project dependencies.
- [ ] 1.2. Implement a parser factory in `src/ast_parser/parser.py` that loads the appropriate Tree-sitter grammar based on file extension.
- [ ] 1.3. Create a `TypeScriptParser` class that uses Tree-sitter queries to extract entities (functions, classes, imports, etc.) from TypeScript/JavaScript files, as specified in the PRD.

## 2. Schema Extension
- [ ] 2.1. Update `src/neo4j_storage/graph_db.py` to include new node labels (`Interface`, `Enum`, `TypeAlias`, `Namespace`) and relationship types (`IMPLEMENTS`, `EXTENDS`, `TYPE_DEPENDS_ON`).

## 3. Integration
- [ ] 3.1. Modify `src/main.py` to use the new parser factory and direct files to the appropriate parser.
- [ ] 3.2. Write unit tests for the `TypeScriptParser` to validate entity extraction against sample code.
