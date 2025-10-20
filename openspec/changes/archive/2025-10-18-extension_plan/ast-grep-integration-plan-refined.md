# AST-grep Integration Plan (Refined and Actionable)

This plan turns Graph-Codebase-MCP from Python-only parsing into a multi-language platform using ast-grep, while preserving existing behavior, schema, and MCP APIs. It is written for a junior developer to follow step-by-step.

- Backward compatibility: Python parsing must remain identical (node/edge counts, IDs, properties) unless explicitly feature-flagged.
- Multi-language: Add JavaScript, TypeScript first; then Java, C++, Rust, Go.
- Data model unchanged: keep CodeNode and CodeRelation, Neo4j schema, embeddings, and MCP interfaces as-is.
- Gradual rollout with feature flags and easy rollback.


## Executive summary

We will introduce a new adapter layer that uses ast-grep’s Python API (SgRoot/SgNode) to parse code from multiple languages and normalize it to the existing CodeNode/CodeRelation model. We’ll first build an ast-grep Python adapter and verify it reproduces current output 1:1. Next we’ll add a JavaScript/TypeScript adapter to replace the current tree-sitter-only path over time (kept as fallback initially). Then we’ll add minimal adapters for Java/C++/Rust/Go, expand tests, and switch the main pipeline to a small “multi-language parser coordinator” that preserves the current two-pass import resolution and parallelization model.

Success criteria:
- Python: identical outputs vs legacy for a representative set of projects (regression tests). Performance no worse than -20%.
- JS/TS: parity with current TypeScriptParser on tests, then replace by default behind a flag.
- Other languages: basic nodes and imports extracted; stable and test-covered.


## Repository orientation you’ll rely on (current code)
- Parser you must mirror exactly for Python: `src/ast_parser/parser.py` (ASTParser)
- Current JS/TS parser (tree-sitter): `src/ast_parser/typescript_parser.py`
- Main pipeline and routing: `src/main.py` (two-pass indexing, parallel processing, embedding, Neo4j load)
- Node/edge data classes: `CodeNode`, `CodeRelation` in `src/ast_parser/parser.py`
- Tests to look at first: `tests/test_ast_parser.py`, `tests/test_typescript_parser.py`


## Feature flags you will introduce and use
- USE_AST_GREP=true|false (default false) – master switch to enable ast-grep-based parsing.
- AST_GREP_LANGUAGES=python,javascript,typescript,java,cpp,rust,go – list of enabled adapters.
- AST_GREP_FALLBACK_TO_LEGACY=true|false (default true) – on error, fall back to existing parser.
- ENABLE_JS_TS_PARSING (already exists) – keep as-is; ast-grep adapter will respect it.

Note: we will only wire these flags in Phase 3 after the Python adapter is ready.


## File structure to add
```
src/ast_parser/
  adapters/
    __init__.py
    base_adapter.py          # common interface
    python_adapter.py        # ast-grep Python (Phase 2)
    javascript_adapter.py    # ast-grep JS/TS (Phase 4)
    java_adapter.py          # minimal (Phase 5)
    cpp_adapter.py           # minimal (Phase 5)
    rust_adapter.py          # minimal (Phase 5)
    go_adapter.py            # minimal (Phase 5)
  multi_parser.py            # coordinator that picks adapter by extension
  language_detector.py       # tiny extension->language map
```
We DO NOT delete `parser.py` or `typescript_parser.py`; they remain fallbacks.


## PHASE 1: Foundation 

- Objective: Install ast-grep dependency, verify API locally, and create project feature flags (no behavior change yet).
- Prerequisites: None.

### 1.1 Add dependency
- File to modify: `requirements.txt`
- What to implement: Append `ast-grep-py>=0.39.0`.
- Code example (requirements.txt):
  - Add a single line: `ast-grep-py>=0.39.0`
- Testing approach:
  - Install deps, then open a Python REPL and import:
    - `from ast_grep_py import SgRoot, SgNode`
    - `SgRoot("print('x')", "python").root()`
  - It should create a root node without error.
- Success criteria: Import works on your machine; no breakage to current tests.
- Risk mitigation: If wheels are unavailable for your Python version/OS, pin to a compatible version in requirements or try a commonly supported Python version (3.10–3.12).

### 1.2 Introduce feature flags
- File to modify: `src/main.py`
- What to implement: Read `USE_AST_GREP`, `AST_GREP_LANGUAGES`, `AST_GREP_FALLBACK_TO_LEGACY` from env. Don’t switch behavior yet; just parse and store values for later logs.
- Code example (<= 30 lines):
  - Add near other env reads:
    - `use_ast_grep = os.getenv("USE_AST_GREP", "false").lower() == "true"`
    - `ast_grep_languages = os.getenv("AST_GREP_LANGUAGES", "python,javascript,typescript").split(',')`
    - `ast_grep_fallback = os.getenv("AST_GREP_FALLBACK_TO_LEGACY", "true").lower() == "true"`
- Testing approach: Run and ensure the app starts and logs flag values; no behavior change.
- Success criteria: App boots and logs flags; existing tests pass.
- Risks: None (read-only configuration).


## PHASE 2: Base adapter + Python adapter 

- Objective: Define a small adapter interface and implement an ast-grep-based Python adapter that produces identical outputs to `ASTParser` for Python.
- Prerequisites: Phase 1.

### 2.1 Create base adapter
- File to create: `src/ast_parser/adapters/base_adapter.py`
- What to implement: A small interface that returns two accumulators `nodes` and `relations`, and maintains the same ancillary indices used by current pipeline (module_definitions, pending_imports, module_to_file, established_relations). Keep signatures similar to `ASTParser`/`TypeScriptParser` to simplify Phase 3.
- Code example (<= 30 lines):
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple
from src.ast_parser.parser import CodeNode, CodeRelation

class LanguageAdapter(ABC):
    def __init__(self, language: str):
        self.language = language
        self.nodes: Dict[str, CodeNode] = {}
        self.relations: List[CodeRelation] = []
        self.module_definitions: Dict[str, Dict[str, str]] = {}
        self.pending_imports: List[Dict[str, Any]] = []
        self.module_to_file: Dict[str, str] = {}
        self.established_relations: set[str] = set()

    @abstractmethod
    def parse_file(self, file_path: str, build_index: bool = False) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        ...
```
- Testing approach: Import the class; no functional behavior yet.
- Success criteria: Imports fine; no runtime errors.

### 2.2 Implement Python adapter with ast-grep
- File to create: `src/ast_parser/adapters/python_adapter.py`
- What to implement: Use `ast_grep_py` to extract classes, functions, methods, variables, imports; emit identical `CodeNode`/`CodeRelation` and maintain indexes exactly like `ASTParser`. IDs must match: `f"{node_type}:{file_path}:{name}:{line_no}"` for nodes and `file:{file_path}` for file nodes.
- Code example (<= 30 lines; minimal core):
```python
from ast_grep_py import SgRoot
from src.ast_parser.parser import CodeNode, CodeRelation
from .base_adapter import LanguageAdapter
import os

class PythonAstGrepAdapter(LanguageAdapter):
    def __init__(self):
        super().__init__("python")

    def parse_file(self, file_path: str, build_index: bool = False):
        with open(file_path, "r", encoding="utf-8") as f:
            src = f.read()
        root = SgRoot(src, "python").root()
        file_node_id = f"file:{file_path}"
        self.nodes[file_node_id] = CodeNode(file_node_id, "File", os.path.basename(file_path), file_path, 0)
        # Example: functions
        for fn in root.find_all(kind="function_definition"):
            name = fn.field("name")
            if not name: continue
            line = fn.range().start.line + 1
            nid = f"Function:{file_path}:{name.text()}:{line}"
            self.nodes[nid] = CodeNode(nid, "Function", name.text(), file_path, line, fn.range().end.line + 1, {"is_method": False})
            self.nodes[nid].code_snippet = fn.text()
            self.relations.append(CodeRelation(file_node_id, nid, "CONTAINS"))
        # TODO: classes, methods, variables, imports, calls to parity with ASTParser
        return self.nodes, self.relations
```
- Testing approach: Write a tiny local script to parse a simple Python file; verify nodes appear.
- Success criteria: Adapter can parse basic Python and emit nodes/relations without exceptions.
- Risk mitigation: Build out in small increments; next step (Phase 3) adds strict regression tests.


## PHASE 3: Coordinator and feature toggle for Python 

- Objective: Add a multi-language coordinator that picks parser per extension. Gate Python via `USE_AST_GREP`; when enabled, Python files use `PythonAstGrepAdapter`, else legacy `ASTParser`.
- Prerequisites: Phase 2.

### 3.1 Language detector
- File to create: `src/ast_parser/language_detector.py`
- What to implement: Map extensions to ast-grep languages.
- Code example (<= 20 lines):
```python
EXT_TO_LANG = {
  ".py": "python", ".js": "javascript", ".jsx": "javascript",
  ".ts": "typescript", ".tsx": "typescript",
  ".java": "java", ".cpp": "cpp", ".cc": "cpp", ".rs": "rust", ".go": "go",
}
```

### 3.2 Multi-language coordinator
- File to create: `src/ast_parser/multi_parser.py`
- What to implement: `parse_file()` chooses adapter by extension. For `.py`, use `PythonAstGrepAdapter` only when `USE_AST_GREP=true`; else use existing `ASTParser`. For `.js/.ts/...` still route to existing `TypeScriptParser` for now.
- Code example (<= 30 lines):
```python
import os
from typing import Tuple, Dict, List
from src.ast_parser.parser import ASTParser, CodeNode, CodeRelation
from src.ast_parser.typescript_parser import TypeScriptParser
from src.ast_parser.adapters.python_adapter import PythonAstGrepAdapter

class MultiLanguageParser:
    def __init__(self, use_ast_grep: bool):
        self.use_ast_grep = use_ast_grep
    def parse_file(self, file_path: str) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".py" and self.use_ast_grep:
            return PythonAstGrepAdapter().parse_file(file_path, build_index=True)
        if ext == ".py":
            return ASTParser().parse_file(file_path, build_index=True)
        if ext in [".js", ".ts", ".jsx", ".tsx"]:
            return TypeScriptParser().parse_file(file_path, build_index=True)
        return {}, []
```
- Testing approach: Point the coordinator at a mixed folder; confirm outputs match current behavior when `USE_AST_GREP=false`.
- Success criteria: No behavior change by default; coordinator compiles and runs.

### 3.3 Wire coordinator into main (non-invasive)
- File to modify: `src/main.py`
- What to implement: Replace direct calls to `_get_parser_for_file()` with coordinator when `USE_AST_GREP=true`; otherwise keep existing flow. Keep two-pass aggregation exactly as implemented today (reusing import resolution in `ASTParser/_process_pending_imports`).
- Testing approach: Run existing tests, then run the pipeline on `tests/example_codebase` and confirm same counts as before with `USE_AST_GREP=false`.
- Success criteria: No regressions.


## PHASE 4: Python parity regression tests 

- Objective: Guarantee Python adapter’s output equals legacy `ASTParser` 1:1.
- Prerequisites: Phases 2–3.

### 4.1 Add regression test
- File to create: `tests/test_python_adapter_compat.py`
- What to implement: Parse the same directory twice: once with `ASTParser`, once with `PythonAstGrepAdapter` via `MultiLanguageParser` and `USE_AST_GREP=true`. Compare:
  - Node count and set of node_ids
  - Relation count and multiset of (source_id, type, target_id)
- Code example (<= 30 lines):
```python
from src.ast_parser.parser import ASTParser
from src.ast_parser.adapters.python_adapter import PythonAstGrepAdapter
from src.ast_parser.multi_parser import MultiLanguageParser

def _key(r): return (r.source_id, r.relation_type, r.target_id)

def test_python_parity(tmp_path):
    legacy_nodes, legacy_rels = ASTParser().parse_directory("tests/../example_codebase")
    mlp = MultiLanguageParser(use_ast_grep=True)
    # Reuse coordinator single-file over directory (simple loop)
    nodes2, rels2 = {}, []
    import os
    for root,_,files in os.walk("tests/../example_codebase"):
        for f in files:
            if f.endswith('.py'):
                n2, r2 = mlp.parse_file(os.path.join(root, f))
                nodes2.update(n2); rels2 += r2
    assert set(legacy_nodes.keys()) == set(nodes2.keys())
    assert len(legacy_rels) == len(rels2)
    assert sorted(map(_key, legacy_rels)) == sorted(map(_key, rels2))
```
- Testing approach: Run `pytest -q`.
- Success criteria: Test passes; if not, iterate adapter until parity achieved.
- Risk mitigation: Start by matching IDs, properties gradually; write small helper functions to normalize order.


## PHASE 5: JS/TS ast-grep adapter and toggle 

- Objective: Implement `javascript_adapter.py` using ast-grep. Keep `TypeScriptParser` as fallback behind a flag. Reach parity with `tests/test_typescript_parser.py`.
- Prerequisites: Phases 2–3–4.

### 5.1 Implement adapter
- File to create: `src/ast_parser/adapters/javascript_adapter.py`
- What to implement: Extract functions (declarations and arrow), classes + methods, variables, imports/exports. Emit nodes/relations exactly like `TypeScriptParser` does now (IDs, CONTAINS, DEFINES, EXTENDS). Maintain indexes (module_definitions, pending_imports, module_to_file) to keep two-pass import resolution compatible.
- Code example (<= 30 lines; core idea):
```python
from ast_grep_py import SgRoot
from .base_adapter import LanguageAdapter
from src.ast_parser.parser import CodeNode, CodeRelation
import os

class JavaScriptAstGrepAdapter(LanguageAdapter):
    def __init__(self, use_tsx=False):
        super().__init__("javascript")
    def parse_file(self, file_path: str, build_index: bool=False):
        src = open(file_path, encoding='utf-8').read()
        lang = 'typescript' if file_path.endswith(('.ts','.tsx')) else 'javascript'
        root = SgRoot(src, lang).root()
        file_id = f"file:{file_path}"
        self.nodes[file_id] = CodeNode(file_id, "File", os.path.basename(file_path), file_path, 0)
        for cls in root.find_all(kind='class_declaration'):
            name = (cls.field('name') or cls.find(kind='identifier'))
            if not name: continue
            line = cls.range().start.line + 1
            cid = f"Class:{file_path}:{name.text()}:{line}"
            self.nodes[cid] = CodeNode(cid, "Class", name.text(), file_path, line, cls.range().end.line + 1, {"language": lang})
            self.nodes[cid].code_snippet = cls.text()
            self.relations.append(CodeRelation(file_id, cid, "CONTAINS"))
        # TODO functions, methods, variables, imports to parity with TypeScriptParser
        return self.nodes, self.relations
```

### 5.2 Add flag and routing
- File to modify: `src/ast_parser/multi_parser.py`
- What to implement: When `USE_AST_GREP=true`, route `.js/.jsx/.ts/.tsx` to the new adapter; otherwise use `TypeScriptParser`.
- Testing approach: Run `tests/test_typescript_parser.py` for both modes; ensure no regressions when flag is off. Iterate adapter until all tests pass with flag on.
- Success criteria: All JS/TS tests pass under ast-grep path. Default remains legacy (flag off).


## PHASE 6: Additional languages 

- Objective: Provide minimal support for Java, C++, Rust, Go.
- Prerequisites: Phase 5 green.

### 6.1 Implement skeleton adapters
- Files to create:
  - `src/ast_parser/adapters/java_adapter.py`
  - `src/ast_parser/adapters/cpp_adapter.py`
  - `src/ast_parser/adapters/rust_adapter.py`
  - `src/ast_parser/adapters/go_adapter.py`
- What to implement: For each, support at least:
  - File node; top-level classes/structs; functions/methods; simple imports (`import`/`#include`/`use`/`import`); basic CONTAINS/DEFINES/EXTENDS relations.
  - Maintain module indexes and pending_imports as the Python/JS adapters do.
- Code example (Java core, <= 25 lines):
```python
from ast_grep_py import SgRoot
from .base_adapter import LanguageAdapter
from src.ast_parser.parser import CodeNode, CodeRelation
import os
class JavaAdapter(LanguageAdapter):
    def __init__(self): super().__init__('java')
    def parse_file(self, file_path, build_index=False):
        src = open(file_path, encoding='utf-8').read()
        root = SgRoot(src, 'java').root()
        fid = f"file:{file_path}"; self.nodes[fid]=CodeNode(fid,'File',os.path.basename(file_path),file_path,0)
        for cd in root.find_all(kind='class_declaration'):
            nm = cd.field('name');
            if not nm: continue
            ln = cd.range().start.line+1
            cid=f"Class:{file_path}:{nm.text()}:{ln}"
            self.nodes[cid]=CodeNode(cid,'Class',nm.text(),file_path,ln,cd.range().end.line+1)
            self.relations.append(CodeRelation(fid,cid,'CONTAINS'))
        return self.nodes, self.relations
```
- Testing approach: Add tiny unit tests per adapter with 1–2 files; assert presence of nodes and basic relations. Keep tests small and deterministic.
- Success criteria: Tests pass; adapters don’t crash on empty or simple files.


## PHASE 7: Integrate end-to-end, parallelism preserved 

- Objective: Use `MultiLanguageParser` across the pipeline with flags; maintain two-pass import resolution and parallel processing. Keep Neo4j/embeddings unchanged.
- Prerequisites: Phases 3–6.

### 7.1 Wire into main pipeline
- File to modify: `src/main.py`
- What to implement:
  - When `USE_AST_GREP=true`, replace the internal `_get_parser_for_file` routing with `MultiLanguageParser` usage in both sequential and parallel paths.
  - Preserve the existing two-pass import resolution by aggregating `nodes`, `module_definitions`, `pending_imports`, `module_to_file` from adapters, then calling the existing `ASTParser._process_pending_imports()` exactly like now.
- Testing approach: Run end-to-end on the existing `tests/example_codebase` and on `tests/fixtures/js_ts_sample`. Compare node and relation counts to current baseline (with flag off). Compare performance roughly.
- Success criteria:
  - With flag off: identical results.
  - With flag on: Python parity tests pass; JS/TS tests pass; pipeline runs to completion.


## Testing and validation strategy (apply per phase)

- Unit tests: For each adapter, add tests that assert counts and representative properties. Use small code snippets.
- Regression tests: Phase 4 test ensures Python parity. Keep it green.
- Integration tests: Reuse `tests/test_main_processing.py`, `tests/test_mixed_codebase.py` patterns; add new if needed to cover ast-grep path.
- Performance: Add a lightweight benchmark script to compare total parse time over a small mixed fixture with flag on vs off. Target: within -20% of current parse time; otherwise investigate.
- Windows/PowerShell quick runs:
```powershell
# Install
pip install -r requirements.txt

# Run existing tests
pytest -q

# Enable ast-grep for Python only
$env:USE_AST_GREP="true"; $env:AST_GREP_LANGUAGES="python"; pytest -q tests/test_python_adapter_compat.py

# JS/TS adapter tests when ready
$env:USE_AST_GREP="true"; $env:AST_GREP_LANGUAGES="python,javascript,typescript"; pytest -q tests/test_typescript_parser.py
```


## Configuration and rollout guide

- Environment variables:
  - `USE_AST_GREP`: master switch (default false)
  - `AST_GREP_LANGUAGES`: comma-separated list; default `python,javascript,typescript`
  - `AST_GREP_FALLBACK_TO_LEGACY`: if true, on adapter error use legacy parser
  - Existing: `ENABLE_JS_TS_PARSING`, `PARALLEL_INDEXING_ENABLED`, `MAX_WORKERS`, etc.
- Rollout plan:
  1) Land Python adapter + parity tests; ship with flag off.
  2) Turn on in CI for Python-only repos.
  3) Implement JS/TS adapter; run current tests under both paths; default still off.
  4) Enable JS/TS adapter by default after green; keep fallback for one release.
  5) Add basic Java/C++/Rust/Go; gated by `AST_GREP_LANGUAGES`.
- Rollback: Set `USE_AST_GREP=false` to restore full legacy behavior instantly.


## Error handling and edge cases

- Unsupported extensions: coordinator returns empty (skips) with a warning; never crash the pipeline.
- Parse failures: catch exceptions in adapters; if `AST_GREP_FALLBACK_TO_LEGACY=true`, call legacy parser (`ASTParser` for .py, `TypeScriptParser` for .js/.ts). Otherwise, log and skip file.
- Missing dependency: catch `ImportError` for `ast_grep_py`; log clear instruction: `pip install ast-grep-py`.
- Huge files: leave as-is for now; follow current size behavior; add future limit via an env var if needed.
- ID stability: Always generate node IDs exactly like legacy (type:path:name:line). This is critical for parity.


## Risks and mitigations

- ast-grep API mismatch: We verified the latest Python API (SgRoot/SgNode). If methods vary by version, pin `ast-grep-py` in requirements.
- Python parity difficulty: Use the Phase 4 test; iterate until green. Start with classes/functions, then fill variables/imports/calls.
- Performance: If slower than -20%, profile per-language; consider batching files per language to improve cache locality.
- Windows specifics: Keep snippets simple; avoid shell-specific tricks. Confirm wheels exist for your Python version.


## Deliverables checklist per phase

- Phase 1
  - [ ] requirements.txt updated with `ast-grep-py`
  - [ ] Flags parsed and logged in main
- Phase 2
  - [ ] base_adapter.py added
  - [ ] python_adapter.py initial implementation
- Phase 3
  - [ ] multi_parser.py added + language_detector.py
  - [ ] main.py optionally uses MultiLanguageParser when flag is on
- Phase 4
  - [ ] test_python_adapter_compat.py regression test passes
- Phase 5
  - [ ] javascript_adapter.py added
  - [ ] multi_parser routes JS/TS based on flag; tests green
- Phase 6
  - [ ] java/cpp/rust/go adapters added with minimal tests
- Phase 7
  - [ ] end-to-end run verified; performance within target; docs updated


## Notes for implementers
- Focus on correctness first (matching IDs and relations); code snippets can be small and iterative.
- When in doubt, search for how `ASTParser` does it and mirror that shape.
- Keep methods short; prefer small helpers over complex visitors.
- Commit frequently; run tests after each small change.


---
References used for API correctness:
- ast-grep Python API (SgRoot/SgNode): https://ast-grep.github.io/guide/api-usage/py-api.html