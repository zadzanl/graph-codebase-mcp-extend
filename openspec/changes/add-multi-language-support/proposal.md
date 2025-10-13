## Why
The current system only supports Python, which limits its applicability in modern polyglot development environments. Adding support for TypeScript and JavaScript is crucial for the tool to remain competitive and serve a broader user base, especially in full-stack and front-end development.

## What Changes
- **BREAKING**: Replace the existing Python-specific AST parser with a universal parsing engine based on Tree-sitter.
- Add parsers for TypeScript and JavaScript, including support for `.ts`, `.tsx`, `.js`, and `.jsx` files.
- Extend the graph schema to include nodes and relationships for TypeScript-specific constructs like interfaces, enums, and type aliases.
- Update the main processing logic to use the new parser factory.

## Impact
- **Affected specs**: `parser`, `graph-schema`
- **Affected code**: `src/ast_parser/parser.py`, `src/main.py`, `src/neo4j_storage/graph_db.py`
