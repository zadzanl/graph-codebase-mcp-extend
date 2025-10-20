# Proposal: Add JavaScript/TypeScript Support

## Why

The current system only supports Python, which limits its applicability in modern polyglot development environments. Many codebases contain both Python and JavaScript/TypeScript files, especially in full-stack applications. Adding support for JavaScript and TypeScript will enable comprehensive analysis of these mixed codebases without requiring users to switch tools.

**Key Business Drivers:**
- Full-stack projects typically combine Python backends with JS/TS frontends
- Developers need unified code analysis across their entire codebase
- Competitive positioning requires multi-language support

## What Changes

This proposal adds **minimal** JavaScript and TypeScript parsing capabilities **alongside** existing Python support with **zero breaking changes**.

### ✅ Additive Changes Only

1. **Add TypeScriptParser Module**
   - New `src/ast_parser/typescript_parser.py` module
   - Implements same interface as existing `ASTParser`
   - Uses tree-sitter for parsing JS/TS files

2. **Extend File Collection**
   - Support `.js`, `.ts`, `.jsx`, `.tsx` file extensions
   - Rename `_collect_python_files()` → `_collect_source_files()`
   - Maintain backward compatibility

3. **Add Parser Routing Logic**
   - Route `.py` files to existing `ASTParser`
   - Route `.js/.ts/.jsx/.tsx` files to new `TypeScriptParser`
   - File extension-based selection (simple and reliable)

4. **Reuse Existing Schema**
   - Use existing node types: `Function`, `Class`, `Variable`, `File`
   - Use existing relationships: `CONTAINS`, `DEFINES`, `CALLS`, `IMPORTS`, `INHERITS`
   - No new Neo4j schema changes required

5. **Add Dependencies**
   - `tree-sitter==0.21.0` (Python bindings)
   - `tree-sitter-languages==1.10.2` (pre-compiled JS/TS grammars)
   - Total size: < 10MB (pre-compiled wheels)

### ❌ No Breaking Changes

- **Keep** existing `ASTParser` completely unchanged
- **Keep** current graph schema (no new node labels)
- **Keep** existing API and configuration
- **Keep** current performance characteristics
- **Keep** existing tests passing without modification

### Minimal Construct Support

**Phase 1 Scope (Essential Only):**
- Function declarations: `function foo() {}` → `Function` node
- Arrow functions: `const foo = () => {}` → `Function` node
- Class declarations: `class Foo {}` → `Class` node
- Class methods: `myMethod() {}` → `Function` node with parent class
- Variable declarations: `const x = 1` → `Variable` node
- ES6 imports: `import { x } from 'y'` → `IMPORTS` relationship
- ES6 exports: `export class Foo` → exported property on node

**Not Included (Scope Creep Prevention):**
- ❌ TypeScript interfaces (compile-time only)
- ❌ TypeScript enums (can be added later if needed)
- ❌ TypeScript type aliases (compile-time only)
- ❌ Namespaces (rarely used in modern code)
- ❌ Decorators (experimental feature)
- ❌ Complex generic types (compile-time only)

## Impact

### Affected Specs
- `specs/parser/spec.md` - Add JS/TS parsing requirements

### Affected Code Files

**Modified Files:**
- `src/main.py` - Add parser routing logic (~50 lines)
- `requirements.txt` - Add tree-sitter dependencies (2 lines)

**New Files:**
- `src/ast_parser/typescript_parser.py` - New parser class (~250 lines)
- `tests/test_typescript_parser.py` - Unit tests (~300 lines)
- `example_codebase/*.js` - Sample JS test files

**Unchanged Files (Backward Compatibility):**
- ✅ `src/ast_parser/parser.py` - Python parser unchanged
- ✅ `src/neo4j_storage/graph_db.py` - No schema changes
- ✅ `src/embeddings/` - Works with any parser output
- ✅ `src/mcp/server.py` - Language-agnostic
- ✅ All existing tests - Continue passing

### User Impact

**For Existing Users:**
- Zero migration effort required
- Python-only codebases work identically
- Optional: Process JS/TS files by default (can be disabled)
- No configuration changes needed

**For New Users:**
- Out-of-box support for Python + JS/TS codebases
- Unified analysis across multiple languages
- Single tool for full-stack projects

## Technical Approach

### Architecture: Parallel Parser System

```
Current:                      New:
┌─────────────┐              ┌─────────────┐
│   main.py   │              │   main.py   │
└──────┬──────┘              └──────┬──────┘
       │                            │
       v                            v
┌─────────────┐              ┌─────────────┐
│  ASTParser  │              │  Parser     │
│  (.py only) │              │  Router     │
└─────────────┘              └──────┬──────┘
                                    │
                         ┌──────────┴──────────┐
                         v                     v
                  ┌─────────────┐      ┌─────────────────┐
                  │  ASTParser  │      │ TypeScriptParser│
                  │  (.py)      │      │  (.js/.ts)      │
                  └─────────────┘      └─────────────────┘
```

### Parser Selection Logic

```python
def _get_parser_for_file(file_path: str):
    """Route files to appropriate parser based on extension."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.py':
        return ASTParser()  # Existing Python parser
    elif ext in ['.js', '.ts', '.jsx', '.tsx']:
        return TypeScriptParser()  # New JS/TS parser
    else:
        logger.warning(f"Unsupported file extension: {ext}")
        return None
```

### Library Choice: Tree-sitter

**Why Tree-sitter:**
1. ✅ **Lightweight**: Pre-compiled wheels, no compilation required
2. ✅ **Python-native**: Official Python bindings (`py-tree-sitter`)
3. ✅ **Unified**: Single grammar handles both JS and TS
4. ✅ **Proven**: Used by VS Code, Atom, Neovim, GitHub
5. ✅ **Fast**: Written in C, optimized for performance
6. ✅ **Maintained**: Active development, regular updates

**Alternatives Considered:**

| Library | Why Not Chosen |
|---------|----------------|
| **Esprima** | JavaScript-only, requires Node.js runtime |
| **Acorn** | JavaScript-only, no TypeScript support |
| **Babel Parser** | Heavy dependency (~20MB), designed for transpilation not analysis |
| **SWC** | Rust-based, complex setup, overkill for parsing |

**Dependencies:**
```
tree-sitter==0.21.0              # Core parser library
tree-sitter-languages==1.10.2    # Pre-compiled JS/TS grammars
```

### Output Format Compatibility

Both parsers produce identical output structures:

```python
# CodeNode structure (same for Python and JS/TS)
CodeNode(
    node_id="file:utils.js:function:formatDate",
    node_type="Function",
    name="formatDate",
    file_path="/path/to/utils.js",
    line_no=10,
    end_line_no=15,
    properties={
        "parameters": ["date", "format"],
        "exported": True,
        "language": "javascript"
    },
    code_snippet="function formatDate(date, format) { ... }"
)

# CodeRelation structure (same for Python and JS/TS)
CodeRelation(
    source_id="file:app.js:class:App",
    target_id="file:utils.js:function:formatDate",
    relation_type="CALLS",
    properties={
        "line_no": 25,
        "context": "method"
    }
)
```

## Success Criteria

### Functional Requirements
- ✅ Process `.js`, `.ts`, `.jsx`, `.tsx` files successfully
- ✅ Parse functions, classes, variables, imports correctly
- ✅ Extract relationships (calls, imports, inheritance)
- ✅ Handle syntax errors gracefully (log and continue)
- ✅ 100% of existing Python tests pass unchanged

### Performance Requirements
- ✅ Python-only processing time: ≤ 105% of baseline
- ✅ JS/TS parsing speed: > 1000 lines of code per second
- ✅ Memory overhead: < 50MB per worker process
- ✅ Parallel processing works with mixed codebases

### Quality Requirements
- ✅ Zero breaking changes to existing API
- ✅ Code coverage: ≥ 90% for new TypeScriptParser
- ✅ Documentation: 100% complete and updated
- ✅ Code maintainability: A or B grade

## Risk Analysis

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Parse errors break processing** | High | Medium | Wrap parser calls in try-except, log errors, continue processing |
| **Performance degradation** | Medium | Low | Use same parallel processing pattern, benchmark against baseline |
| **Dependency conflicts** | Medium | Low | Pin versions, use pre-compiled wheels |
| **Schema incompatibility** | High | Low | Validate output matches existing CodeNode/CodeRelation format |
| **Memory exhaustion** | Medium | Low | Monitor memory usage, limit tree-sitter cache size |
| **Incomplete parsing** | Medium | Medium | Start with minimal constructs, expand based on user feedback |

## Implementation Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Research** | ✅ Complete | Library selection, architecture design |
| **Setup** | 1 hour | Add dependencies, verify installation |
| **Core Implementation** | 1 day | Create TypeScriptParser class |
| **Integration** | 0.5 day | Add parser routing, extend file collection |
| **Testing** | 1 day | Unit tests, integration tests, regression tests |
| **Documentation** | 0.5 day | Update README, add examples |
| **Review & Polish** | 0.5 day | Code review, performance validation |

**Total Estimated Time: ~4 days**

## Configuration

### New Environment Variables

```bash
# Optional: Enable/disable JS/TS parsing (default: true)
ENABLE_JS_TS_PARSING=true

# Optional: Tree-sitter parser timeout (default: 30 seconds)
TREE_SITTER_TIMEOUT=30
```

### Existing Configuration (Unchanged)

All existing environment variables remain unchanged:
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `OPENAI_API_KEY`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`
- `PARALLEL_INDEXING_ENABLED`, `MAX_WORKERS`
- All other configuration options

## Migration Path

### For Existing Users

1. **Update Installation**
   ```bash
   git pull
   pip install -r requirements.txt
   ```

2. **No Configuration Changes Required**
   - JS/TS support automatically enabled
   - Existing Python codebases work identically

3. **Optional: Process Mixed Codebases**
   ```bash
   python src/main.py --codebase-path /path/to/mixed/codebase
   ```

### For New Users

Standard installation process works for all languages:
```bash
pip install -r requirements.txt
python src/main.py --codebase-path /path/to/codebase
```

## Alternatives Considered

### Alternative 1: Replace Python Parser with Tree-sitter

**Pros:**
- Unified parsing approach for all languages
- Consistent AST structure

**Cons:**
- ❌ **BREAKING CHANGE** - would break existing Python processing
- ❌ Risk of introducing bugs in stable Python parsing
- ❌ Requires rewriting existing parser logic
- ❌ Violates user requirement: "do not over engineer"

**Decision: Rejected**

### Alternative 2: Use Language-Specific Parsers

**Pros:**
- Optimal parsing for each language
- Language-specific features fully supported

**Cons:**
- More dependencies (Esprima + Acorn + TypeScript compiler)
- Complex integration (Node.js runtime required)
- Maintenance burden across multiple parsers

**Decision: Rejected**

### Alternative 3: Minimal Tree-sitter Integration (CHOSEN)

**Pros:**
- ✅ Non-breaking addition to existing system
- ✅ Single lightweight dependency
- ✅ Handles both JS and TS
- ✅ Simple integration

**Cons:**
- Two parsing approaches in codebase (Python AST + Tree-sitter)

**Decision: Accepted - best balance of simplicity and functionality**

## Open Questions

1. **Should we support CommonJS `require()` statements?**
   - Recommendation: Yes, add in Phase 1 (common in Node.js code)

2. **Should we parse JSX components as classes?**
   - Recommendation: Yes, treat functional components as functions, class components as classes

3. **Should we extract JSDoc comments?**
   - Recommendation: Phase 2 feature (not essential for MVP)

4. **Should we support Flow type annotations?**
   - Recommendation: No, Flow usage is declining (focus on TypeScript)

5. **Should we add configuration to disable JS/TS parsing?**
   - Recommendation: Yes, add `ENABLE_JS_TS_PARSING` environment variable

## References

- [Tree-sitter Official Site](https://tree-sitter.github.io/tree-sitter/)
- [py-tree-sitter GitHub](https://github.com/tree-sitter/py-tree-sitter)
- [tree-sitter-languages PyPI](https://pypi.org/project/tree-sitter-languages/)
- [Tree-sitter JavaScript Grammar](https://github.com/tree-sitter/tree-sitter-javascript)
- [Tree-sitter TypeScript Grammar](https://github.com/tree-sitter/tree-sitter-typescript)
- [ESTree Specification](https://github.com/estree/estree) (AST format reference)
