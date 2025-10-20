# Implementation Tasks: Add JavaScript/TypeScript Support

## Overview
Minimal, non-breaking implementation of JavaScript/TypeScript parsing alongside existing Python support using tree-sitter.

---

## 1. Setup Dependencies & Environment

### 1.1. Add Tree-sitter Dependencies
- [ ] 1.1.1. Add `tree-sitter==0.21.0` to `requirements.txt`
- [ ] 1.1.2. Add `tree-sitter-languages==1.10.2` to `requirements.txt`
- [ ] 1.1.3. Verify dependencies install correctly: `pip install -r requirements.txt`
- [ ] 1.1.4. Test basic tree-sitter import: `python -c "import tree_sitter_languages; print('OK')"`

### 1.2. Document New Dependencies
- [ ] 1.2.1. Update README.md with new dependencies
- [ ] 1.2.2. Add "Supported Languages" section showing Python, JavaScript, TypeScript
- [ ] 1.2.3. Document optional `ENABLE_JS_TS_PARSING` environment variable

**Estimated Time:** 1 hour  
**Risk:** Low - pre-compiled wheels available for all platforms

**Acceptance Criteria:**
- Dependencies install without compilation
- No conflicts with existing packages
- Basic import test passes

---

## 2. Create TypeScriptParser Module

### 2.1. Create Base Parser Class
- [ ] 2.1.1. Create file `src/ast_parser/typescript_parser.py`
- [ ] 2.1.2. Import required modules: `tree_sitter_languages`, `tree_sitter`, `os`, `logging`
- [ ] 2.1.3. Define `TypeScriptParser` class with same interface as `ASTParser`
- [ ] 2.1.4. Initialize tree-sitter parser for JavaScript/TypeScript in `__init__`
- [ ] 2.1.5. Add `nodes` and `relations` dictionaries matching `ASTParser` structure

### 2.2. Implement parse_file() Method
- [ ] 2.2.1. Implement `parse_file(file_path: str, build_index: bool = False)` method signature
- [ ] 2.2.2. Read file content and parse with tree-sitter
- [ ] 2.2.3. Get root node from parse tree
- [ ] 2.2.4. Call extraction methods for each node type
- [ ] 2.2.5. Return `(nodes, relations)` tuple matching `ASTParser` format

### 2.3. Extract Functions
- [ ] 2.3.1. Write tree-sitter query for function declarations: `(function_declaration name: (identifier) @name)`
- [ ] 2.3.2. Write tree-sitter query for arrow functions: `(variable_declarator name: (identifier) value: (arrow_function))`
- [ ] 2.3.3. Write tree-sitter query for method definitions: `(method_definition name: (property_identifier) @name)`
- [ ] 2.3.4. Extract function name, line number, parameters
- [ ] 2.3.5. Create `CodeNode` with type "Function"
- [ ] 2.3.6. Extract function body as code snippet

### 2.4. Extract Classes
- [ ] 2.4.1. Write tree-sitter query for class declarations: `(class_declaration name: (identifier) @name)`
- [ ] 2.4.2. Extract class name, line number
- [ ] 2.4.3. Create `CodeNode` with type "Class"
- [ ] 2.4.4. Check for parent class (extends clause)
- [ ] 2.4.5. Create `INHERITS` relationship if parent exists
- [ ] 2.4.6. Extract class body as code snippet

### 2.5. Extract Variables
- [ ] 2.5.1. Write tree-sitter query for top-level variable declarations
- [ ] 2.5.2. Filter for `const`, `let`, `var` declarations
- [ ] 2.5.3. Extract variable name, line number, declaration type
- [ ] 2.5.4. Create `CodeNode` with type "Variable"
- [ ] 2.5.5. Add `declaration_type` property (const/let/var)

### 2.6. Extract Imports
- [ ] 2.6.1. Write tree-sitter query for import statements: `(import_statement)`
- [ ] 2.6.2. Extract source module path
- [ ] 2.6.3. Extract imported names (named imports)
- [ ] 2.6.4. Handle default imports
- [ ] 2.6.5. Handle namespace imports (`import * as`)
- [ ] 2.6.6. Create `IMPORTS` relationships
- [ ] 2.6.7. Store in `pending_imports` for later resolution (match `ASTParser` pattern)

### 2.7. Extract Exports
- [ ] 2.7.1. Write tree-sitter query for export statements
- [ ] 2.7.2. Mark exported entities with `exported: True` property
- [ ] 2.7.3. Distinguish between named and default exports
- [ ] 2.7.4. Add `export_type` property (named/default)

### 2.8. Error Handling
- [ ] 2.8.1. Wrap entire `parse_file()` in try-except
- [ ] 2.8.2. Log parse errors with file path and error message
- [ ] 2.8.3. Return empty results on error (don't crash)
- [ ] 2.8.4. Add error counter to track failed parses

**Estimated Time:** 1.5 days  
**Risk:** Medium - requires understanding tree-sitter query syntax

**Acceptance Criteria:**
- Parser successfully extracts functions, classes, variables, imports
- Output format matches `ASTParser` (CodeNode, CodeRelation)
- Error handling prevents crashes on malformed code
- Code is well-documented with docstrings

---

## 3. Extend File Collection Logic

### 3.1. Update File Collection Function
- [ ] 3.1.1. Locate `_collect_python_files()` in `src/main.py`
- [ ] 3.1.2. Rename function to `_collect_source_files()`
- [ ] 3.1.3. Update docstring to reflect multi-language support
- [ ] 3.1.4. Add `.js`, `.ts`, `.jsx`, `.tsx` to file extension list
- [ ] 3.1.5. Keep `.py` extension for backward compatibility

### 3.2. Add Configuration Option
- [ ] 3.2.1. Check for `ENABLE_JS_TS_PARSING` environment variable
- [ ] 3.2.2. Default to `True` if not set
- [ ] 3.2.3. Only collect JS/TS files if enabled
- [ ] 3.2.4. Log which languages are enabled

### 3.3. Update Function Calls
- [ ] 3.3.1. Find all calls to `_collect_python_files()`
- [ ] 3.3.2. Replace with `_collect_source_files()`
- [ ] 3.3.3. Verify no breaking changes

**Estimated Time:** 2 hours  
**Risk:** Low - simple refactoring

**Acceptance Criteria:**
- Function collects Python, JavaScript, and TypeScript files
- Backward compatibility maintained (Python-only projects work)
- Configuration option works correctly

---

## 4. Add Parser Routing Logic

### 4.1. Create Parser Selection Function
- [ ] 4.1.1. Create `_get_parser_for_file(file_path: str)` function in `src/main.py`
- [ ] 4.1.2. Extract file extension using `os.path.splitext()`
- [ ] 4.1.3. Route `.py` → `ASTParser()` (import from existing module)
- [ ] 4.1.4. Route `.js/.ts/.jsx/.tsx` → `TypeScriptParser()` (import new module)
- [ ] 4.1.5. Log warning for unknown extensions
- [ ] 4.1.6. Return `None` for unsupported files

### 4.2. Update process_codebase() Function
- [ ] 4.2.1. Locate `process_codebase()` in `src/main.py`
- [ ] 4.2.2. Replace direct `ASTParser()` instantiation with `_get_parser_for_file()`
- [ ] 4.2.3. Skip files where parser is `None`
- [ ] 4.2.4. Ensure parallel processing works with mixed parser types
- [ ] 4.2.5. Update logging to show which parser is used per file

### 4.3. Verify Parallel Processing
- [ ] 4.3.1. Test that parallel pool works with both parser types
- [ ] 4.3.2. Ensure each worker can instantiate TypeScriptParser
- [ ] 4.3.3. Verify no thread-safety issues with tree-sitter

**Estimated Time:** 3 hours  
**Risk:** Low - simple routing logic with clear separation

**Acceptance Criteria:**
- Files correctly routed to appropriate parser
- Parallel processing works for mixed codebases
- Logging clearly shows which parser handles each file

---

## 5. Error Handling & Resilience

### 5.1. Wrap Parser Calls
- [ ] 5.1.1. Add try-except around TypeScriptParser.parse_file() calls
- [ ] 5.1.2. Catch `Exception` broadly to handle all parse errors
- [ ] 5.1.3. Log error with file path, line number (if available), error message

### 5.2. Implement Graceful Degradation
- [ ] 5.2.1. Continue processing remaining files on parse failure
- [ ] 5.2.2. Track failed files separately
- [ ] 5.2.3. Add parse error count to processing summary

### 5.3. Add Parse Metrics
- [ ] 5.3.1. Count total files processed per language
- [ ] 5.3.2. Count successful vs failed parses
- [ ] 5.3.3. Display metrics in final summary
- [ ] 5.3.4. Example: "Processed 50 Python files (48 success, 2 errors), 30 JS/TS files (28 success, 2 errors)"

**Estimated Time:** 2 hours  
**Risk:** Low - defensive programming

**Acceptance Criteria:**
- Parse errors don't stop overall processing
- Failed files are logged with details
- Processing summary includes per-language metrics

---

## 6. Testing

### 6.1. Create Unit Tests
- [ ] 6.1.1. Create `tests/test_typescript_parser.py`
- [ ] 6.1.2. Test function parsing: `function test() {}`
- [ ] 6.1.3. Test arrow function: `const test = () => {}`
- [ ] 6.1.4. Test class parsing: `class Test {}`
- [ ] 6.1.5. Test class with methods: `class Test { method() {} }`
- [ ] 6.1.6. Test class with inheritance: `class Child extends Parent {}`
- [ ] 6.1.7. Test variable parsing: `const x = 1`
- [ ] 6.1.8. Test import parsing: `import { x } from 'y'`
- [ ] 6.1.9. Test default import: `import x from 'y'`
- [ ] 6.1.10. Test namespace import: `import * as x from 'y'`
- [ ] 6.1.11. Test export parsing: `export class Test {}`
- [ ] 6.1.12. Test error handling: malformed code

### 6.2. Create Integration Tests
- [ ] 6.2.1. Create sample JS/TS files in `example_codebase/`
- [ ] 6.2.2. Test mixed Python/JS/TS codebase processing
- [ ] 6.2.3. Verify nodes and relationships created correctly in Neo4j
- [ ] 6.2.4. Test that embeddings are generated for JS/TS code
- [ ] 6.2.5. Test MCP queries work with JS/TS entities

### 6.3. Regression Tests
- [ ] 6.3.1. Run all existing tests: `pytest tests/`
- [ ] 6.3.2. Verify 100% of existing tests pass
- [ ] 6.3.3. Test Python-only codebase (example_codebase with only .py files)
- [ ] 6.3.4. Compare processing time: should be ≤ 105% of baseline
- [ ] 6.3.5. Verify identical output for Python-only projects

### 6.4. Edge Case Testing
- [ ] 6.4.1. Test JSX components (React)
- [ ] 6.4.2. Test TSX components (React with TypeScript)
- [ ] 6.4.3. Test async/await functions
- [ ] 6.4.4. Test generator functions
- [ ] 6.4.5. Test class with static methods
- [ ] 6.4.6. Test nested functions/classes
- [ ] 6.4.7. Test files with syntax errors

**Estimated Time:** 1 day  
**Risk:** Medium - comprehensive testing required

**Acceptance Criteria:**
- Unit test coverage ≥ 90% for TypeScriptParser
- All integration tests pass
- All existing tests pass without modification
- Edge cases handled gracefully

---

## 7. Documentation

### 7.1. Update README
- [ ] 7.1.1. Update "Supported Programming Languages" section
- [ ] 7.1.2. Check Python, JavaScript, TypeScript boxes
- [ ] 7.1.3. Add JS/TS to "Core Features" descriptions
- [ ] 7.1.4. Update "Installation Guide" with tree-sitter dependencies

### 7.2. Add Examples
- [ ] 7.2.1. Add JS/TS example files to `example_codebase/`
- [ ] 7.2.2. Create simple JS utility module (functions)
- [ ] 7.2.3. Create TS class example (class with methods)
- [ ] 7.2.4. Show import/export relationships

### 7.3. Update Technical Documentation
- [ ] 7.3.1. Document TypeScriptParser API in docstrings
- [ ] 7.3.2. Add architecture diagram showing parallel parser system
- [ ] 7.3.3. Document tree-sitter query patterns used
- [ ] 7.3.4. Add troubleshooting section for parse errors

### 7.4. Update CHANGELOG
- [ ] 7.4.1. Add entry for new JS/TS support feature
- [ ] 7.4.2. List new dependencies
- [ ] 7.4.3. Note backward compatibility maintained

**Estimated Time:** 2 hours  
**Risk:** Low

**Acceptance Criteria:**
- README clearly documents JS/TS support
- Examples demonstrate JS/TS parsing
- Technical documentation is complete
- CHANGELOG updated

---

## 8. Performance Validation

### 8.1. Benchmark Tests
- [ ] 8.1.1. Benchmark Python-only codebase processing (baseline)
- [ ] 8.1.2. Benchmark mixed Python/JS/TS codebase
- [ ] 8.1.3. Verify Python processing time ≤ 105% of baseline
- [ ] 8.1.4. Measure JS/TS parsing speed (target: > 1000 LOC/second)

### 8.2. Memory Profiling
- [ ] 8.2.1. Profile memory usage with mixed codebases
- [ ] 8.2.2. Verify memory overhead < 50MB per worker
- [ ] 8.2.3. Check for memory leaks in tree-sitter parser

### 8.3. Scalability Testing
- [ ] 8.3.1. Test with large JS/TS codebase (> 10,000 files)
- [ ] 8.3.2. Verify parallel processing scales correctly
- [ ] 8.3.3. Ensure no connection pool exhaustion

**Estimated Time:** 0.5 day  
**Risk:** Low

**Acceptance Criteria:**
- Performance targets met
- No memory leaks detected
- Scalability confirmed

---

## Definition of Done

**All tasks completed when:**

- [ ] ✅ All task items checked off
- [ ] ✅ All tests passing (existing + new)
- [ ] ✅ Code coverage ≥ 90% for new code
- [ ] ✅ No breaking changes to existing API
- [ ] ✅ Documentation updated and complete
- [ ] ✅ Performance metrics validated (no regression)
- [ ] ✅ Code reviewed (if team process requires)
- [ ] ✅ README demonstrates JS/TS support with examples
- [ ] ✅ CHANGELOG updated
- [ ] ✅ Changes merged to main branch

---

## Estimated Total Time

| Phase | Duration |
|-------|----------|
| Setup & Dependencies | 1 hour |
| TypeScriptParser Implementation | 1.5 days |
| File Collection Updates | 2 hours |
| Parser Routing Logic | 3 hours |
| Error Handling | 2 hours |
| Testing | 1 day |
| Documentation | 2 hours |
| Performance Validation | 0.5 day |
| **TOTAL** | **~4 days** |

---

## Risk Mitigation Summary

| Risk | Mitigation Strategy |
|------|---------------------|
| Tree-sitter learning curve | Reference official docs, use tree-sitter playground for query testing |
| Parse errors crash system | Comprehensive try-except, error logging, graceful degradation |
| Performance regression | Benchmark early, optimize if needed, maintain parallel processing |
| Breaking changes | Never modify existing ASTParser, maintain identical API |
| Incomplete parsing | Start minimal, expand based on real-world usage, document limitations |
