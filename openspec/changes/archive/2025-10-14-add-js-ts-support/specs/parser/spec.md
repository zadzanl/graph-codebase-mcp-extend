# Parser Specification: JavaScript/TypeScript Support

## Overview
This specification defines the requirements for adding JavaScript and TypeScript parsing capabilities to the graph-codebase-mcp system without breaking existing Python functionality.

---

## ADDED Requirements

### Requirement: Multi-Language File Processing
The system SHALL support processing multiple programming languages by routing files to language-specific parsers based on file extension.

#### Scenario: Python file processing (existing behavior)
- **GIVEN** a file with `.py` extension exists in the codebase
- **WHEN** the system processes the file
- **THEN** the file SHALL be routed to the existing `ASTParser` class
- **AND** processing behavior SHALL be identical to previous versions
- **AND** all existing Python features SHALL continue working

#### Scenario: JavaScript file processing (new behavior)
- **GIVEN** a file with `.js` extension exists in the codebase
- **WHEN** the system processes the file
- **THEN** the file SHALL be routed to the new `TypeScriptParser` class
- **AND** the parser SHALL use tree-sitter JavaScript grammar
- **AND** code entities SHALL be extracted and stored in Neo4j

#### Scenario: JSX file processing (new behavior)
- **GIVEN** a file with `.jsx` extension exists in the codebase
- **WHEN** the system processes the file
- **THEN** the file SHALL be routed to the new `TypeScriptParser` class
- **AND** JSX syntax SHALL be parsed correctly
- **AND** React components SHALL be treated as classes or functions

#### Scenario: TypeScript file processing (new behavior)
- **GIVEN** a file with `.ts` extension exists in the codebase
- **WHEN** the system processes the file
- **THEN** the file SHALL be routed to the new `TypeScriptParser` class
- **AND** the parser SHALL use tree-sitter TypeScript grammar
- **AND** type annotations SHALL be preserved in properties

#### Scenario: TSX file processing (new behavior)
- **GIVEN** a file with `.tsx` extension exists in the codebase
- **WHEN** the system processes the file
- **THEN** the file SHALL be routed to the new `TypeScriptParser` class
- **AND** both TypeScript and JSX syntax SHALL be parsed correctly

#### Scenario: Unsupported file extension
- **GIVEN** a file with an unsupported extension (e.g., `.cpp`, `.java`) exists
- **WHEN** the system encounters the file
- **THEN** the system SHALL log a warning message
- **AND** skip the file without stopping overall processing
- **AND** continue processing remaining files

#### Scenario: Mixed codebase processing
- **GIVEN** a codebase contains both `.py` and `.js/.ts` files
- **WHEN** the system processes the codebase
- **THEN** Python files SHALL use `ASTParser`
- **AND** JavaScript/TypeScript files SHALL use `TypeScriptParser`
- **AND** both languages SHALL be processed in parallel
- **AND** results SHALL be unified in the same Neo4j graph

### Requirement: Parse Function Declarations (JS/TS)
The system SHALL identify and extract function declarations in JavaScript and TypeScript files.

#### Scenario: Standard function declaration
- **GIVEN** a JavaScript file contains:
  ```javascript
  function calculateTotal(items, taxRate) {
    return items.reduce((sum, item) => sum + item.price, 0) * (1 + taxRate);
  }
  ```
- **WHEN** the file is parsed
- **THEN** a `Function` node SHALL be created with:
  - `node_type`: "Function"
  - `name`: "calculateTotal"
  - `file_path`: absolute path to the file
  - `line_no`: line where function starts
  - `end_line_no`: line where function ends
  - `properties.parameters`: ["items", "taxRate"]
  - `properties.language`: "javascript"
  - `code_snippet`: full function source code

#### Scenario: Arrow function with const assignment
- **GIVEN** a TypeScript file contains:
  ```typescript
  const formatDate = (date: Date, format: string): string => {
    return date.toLocaleDateString('en-US', { format });
  };
  ```
- **WHEN** the file is parsed
- **THEN** a `Function` node SHALL be created with:
  - `node_type`: "Function"
  - `name`: "formatDate"
  - `properties.parameters`: ["date", "format"]
  - `properties.language`: "typescript"
  - `properties.function_style`: "arrow"

#### Scenario: Method definition in class
- **GIVEN** a JavaScript file contains:
  ```javascript
  class Calculator {
    add(a, b) {
      return a + b;
    }
  }
  ```
- **WHEN** the file is parsed
- **THEN** a `Function` node SHALL be created for the method with:
  - `node_type`: "Function"
  - `name`: "add"
  - `properties.parent_class`: "Calculator"
  - `properties.is_method`: true
- **AND** a `DEFINES` relationship SHALL be created from the `Calculator` class node to the `add` function node

#### Scenario: Async function
- **GIVEN** a TypeScript file contains:
  ```typescript
  async function fetchData(url: string): Promise<Data> {
    const response = await fetch(url);
    return response.json();
  }
  ```
- **WHEN** the file is parsed
- **THEN** a `Function` node SHALL be created with:
  - `name`: "fetchData"
  - `properties.is_async`: true
  - `properties.parameters`: ["url"]

#### Scenario: Anonymous function (skip)
- **GIVEN** a JavaScript file contains an anonymous function: `array.map(function(x) { return x * 2; })`
- **WHEN** the file is parsed
- **THEN** the anonymous function SHALL NOT create a separate node
- **AND** it SHALL be included in the parent function's code snippet

---

### Requirement: Parse Class Declarations (JS/TS)
The system SHALL identify and extract class declarations in JavaScript and TypeScript files.

#### Scenario: Simple class declaration
- **GIVEN** a JavaScript file contains:
  ```javascript
  class User {
    constructor(name, email) {
      this.name = name;
      this.email = email;
    }
  }
  ```
- **WHEN** the file is parsed
- **THEN** a `Class` node SHALL be created with:
  - `node_type`: "Class"
  - `name`: "User"
  - `file_path`: absolute path to the file
  - `line_no`: line where class starts
  - `end_line_no`: line where class ends
  - `properties.language`: "javascript"
  - `code_snippet`: full class source code
- **AND** a `Function` node SHALL be created for the constructor method

#### Scenario: Class with inheritance
- **GIVEN** a TypeScript file contains:
  ```typescript
  class Employee extends Person {
    constructor(name: string, employeeId: number) {
      super(name);
      this.employeeId = employeeId;
    }
  }
  ```
- **WHEN** the file is parsed
- **THEN** a `Class` node SHALL be created for "Employee"
- **AND** an `INHERITS` relationship SHALL be created with:
  - `source_id`: Employee class node ID
  - `target_id`: Person class node ID (or pending if not yet parsed)
  - `relation_type`: "INHERITS"

#### Scenario: Class with multiple methods
- **GIVEN** a JavaScript file contains:
  ```javascript
  class Calculator {
    add(a, b) { return a + b; }
    subtract(a, b) { return a - b; }
    multiply(a, b) { return a * b; }
  }
  ```
- **WHEN** the file is parsed
- **THEN** a `Class` node SHALL be created for "Calculator"
- **AND** three `Function` nodes SHALL be created (add, subtract, multiply)
- **AND** three `DEFINES` relationships SHALL be created from Calculator to each method

#### Scenario: Class with static methods
- **GIVEN** a TypeScript file contains:
  ```typescript
  class MathUtils {
    static PI = 3.14159;
    static circleArea(radius: number): number {
      return this.PI * radius * radius;
    }
  }
  ```
- **WHEN** the file is parsed
- **THEN** a `Class` node SHALL be created for "MathUtils"
- **AND** a `Function` node SHALL be created for "circleArea" with:
  - `properties.is_static`: true

---

### Requirement: Parse Variable Declarations (JS/TS)
The system SHALL identify and extract top-level variable declarations in JavaScript and TypeScript files.

#### Scenario: Const declaration
- **GIVEN** a JavaScript file contains at top level:
  ```javascript
  const API_URL = 'https://api.example.com';
  ```
- **WHEN** the file is parsed
- **THEN** a `Variable` node SHALL be created with:
  - `node_type`: "Variable"
  - `name`: "API_URL"
  - `file_path`: absolute path to the file
  - `line_no`: line where variable is declared
  - `properties.declaration_type`: "const"
  - `properties.language`: "javascript"

#### Scenario: Let declaration
- **GIVEN** a TypeScript file contains at top level:
  ```typescript
  let currentUser: User | null = null;
  ```
- **WHEN** the file is parsed
- **THEN** a `Variable` node SHALL be created with:
  - `name`: "currentUser"
  - `properties.declaration_type`: "let"
  - `properties.language`: "typescript"

#### Scenario: Var declaration
- **GIVEN** a JavaScript file contains at top level:
  ```javascript
  var globalConfig = { debug: true };
  ```
- **WHEN** the file is parsed
- **THEN** a `Variable` node SHALL be created with:
  - `name`: "globalConfig"
  - `properties.declaration_type`: "var"

#### Scenario: Local variable inside function (skip)
- **GIVEN** a JavaScript file contains:
  ```javascript
  function test() {
    const localVar = 10; // Inside function
  }
  ```
- **WHEN** the file is parsed
- **THEN** a separate `Variable` node SHALL NOT be created for "localVar"
- **AND** it SHALL be included in the function's code snippet only

#### Scenario: Multiple declarations in one statement
- **GIVEN** a JavaScript file contains:
  ```javascript
  const x = 1, y = 2, z = 3;
  ```
- **WHEN** the file is parsed
- **THEN** three separate `Variable` nodes SHALL be created (x, y, z)
- **AND** each SHALL have the same line number

---

### Requirement: Parse Import Statements (JS/TS)
The system SHALL identify and extract ES6 import statements to track module dependencies.

#### Scenario: Named imports
- **GIVEN** a JavaScript file "app.js" contains:
  ```javascript
  import { User, validateEmail } from './user-utils';
  ```
- **WHEN** the file is parsed
- **THEN** pending `IMPORTS` relationships SHALL be created for:
  - Entity "User" from module "./user-utils"
  - Entity "validateEmail" from module "./user-utils"
- **AND** relationships SHALL be resolved during import resolution phase
- **AND** if entities exist, relationships SHALL connect to specific nodes
- **AND** if entities don't exist, relationships SHALL connect to file node

#### Scenario: Default import
- **GIVEN** a TypeScript file "main.ts" contains:
  ```typescript
  import App from './App';
  ```
- **WHEN** the file is parsed
- **THEN** a pending `IMPORTS` relationship SHALL be created with:
  - `properties.import_type`: "default"
  - `properties.imported_as`: "App"
  - `properties.module_path`: "./App"

#### Scenario: Namespace import
- **GIVEN** a JavaScript file contains:
  ```javascript
  import * as Utils from './utilities';
  ```
- **WHEN** the file is parsed
- **THEN** a pending `IMPORTS` relationship SHALL be created with:
  - `properties.import_type`: "namespace"
  - `properties.imported_as`: "Utils"
  - `properties.module_path`: "./utilities"

#### Scenario: Mixed import statement
- **GIVEN** a TypeScript file contains:
  ```typescript
  import React, { useState, useEffect } from 'react';
  ```
- **WHEN** the file is parsed
- **THEN** pending `IMPORTS` relationships SHALL be created for:
  - Default import: "React" from "react"
  - Named imports: "useState", "useEffect" from "react"

#### Scenario: Side-effect import
- **GIVEN** a JavaScript file contains:
  ```javascript
  import './styles.css';
  ```
- **WHEN** the file is parsed
- **THEN** an `IMPORTS` relationship SHALL be created to the file node with:
  - `properties.import_type`: "side-effect"
  - `properties.module_path`: "./styles.css"

---

### Requirement: Parse Export Statements (JS/TS)
The system SHALL identify export statements and mark entities as exported.

#### Scenario: Named export with declaration
- **GIVEN** a JavaScript file contains:
  ```javascript
  export class User {
    constructor(name) {
      this.name = name;
    }
  }
  ```
- **WHEN** the file is parsed
- **THEN** a `Class` node SHALL be created for "User" with:
  - `properties.exported`: true
  - `properties.export_type`: "named"

#### Scenario: Default export with declaration
- **GIVEN** a TypeScript file contains:
  ```typescript
  export default class App extends Component {
    render() { return <div>App</div>; }
  }
  ```
- **WHEN** the file is parsed
- **THEN** a `Class` node SHALL be created for "App" with:
  - `properties.exported`: true
  - `properties.export_type`: "default"

#### Scenario: Named export of existing binding
- **GIVEN** a JavaScript file contains:
  ```javascript
  function helper() { }
  export { helper };
  ```
- **WHEN** the file is parsed
- **THEN** the "helper" `Function` node SHALL be marked with:
  - `properties.exported`: true
  - `properties.export_type`: "named"

#### Scenario: Re-export from another module
- **GIVEN** a TypeScript file contains:
  ```typescript
  export { User, validateEmail } from './user-utils';
  ```
- **WHEN** the file is parsed
- **THEN** `IMPORTS` relationships SHALL be created to "./user-utils"
- **AND** the imported entities SHALL be marked as exported from current file

---

### Requirement: Handle Parse Errors Gracefully
The system SHALL continue processing when encountering JavaScript/TypeScript syntax errors.

#### Scenario: Malformed JavaScript file
- **GIVEN** a JavaScript file contains syntax errors:
  ```javascript
  function broken( {  // Missing closing brace, param
    return "broken";
  ```
- **WHEN** the system attempts to parse the file
- **THEN** the parser SHALL catch the exception
- **AND** log an error message with file path and error details
- **AND** return empty nodes and relations for that file
- **AND** continue processing remaining files

#### Scenario: Parse error reporting
- **GIVEN** multiple files have parse errors
- **WHEN** processing completes
- **THEN** the system SHALL display a summary showing:
  - Total files processed per language
  - Number of successful parses
  - Number of failed parses
  - Example: "JavaScript: 25 files (23 success, 2 errors)"

---

## Implementation Constraints

### Performance Requirements

#### Requirement: No Performance Regression for Python
The addition of JavaScript/TypeScript support SHALL NOT degrade Python processing performance.

**Metrics:**
- Python-only codebase processing time: ≤ 105% of baseline (before JS/TS support)
- Memory usage: ≤ 110% of baseline for Python-only projects

#### Requirement: JavaScript/TypeScript Parsing Speed
JavaScript and TypeScript files SHALL be parsed efficiently.

**Metrics:**
- Parsing speed: ≥ 1000 lines of code per second per worker
- Memory overhead: ≤ 50MB per worker process for tree-sitter

---

### Error Tolerance Requirements

#### Requirement: Isolation of Parse Failures
A parse error in one file SHALL NOT prevent processing of other files.

**Behavior:**
- Wrap all parser calls in try-except blocks
- Log detailed error information
- Continue with next file

#### Requirement: Mixed Codebase Resilience
Parse errors in JavaScript/TypeScript files SHALL NOT affect Python file processing.

**Behavior:**
- Python files processed independently by ASTParser
- JS/TS parse errors logged separately
- Final graph contains successfully parsed entities from all languages

---

### Output Format Compatibility

#### Requirement: Consistent Node Structure
All parsers (Python and TypeScript) SHALL produce `CodeNode` objects with identical structure.

**Schema:**
```python
CodeNode(
    node_id: str,           # Unique identifier: "file:path:type:name"
    node_type: str,         # "Function", "Class", "Variable", "File"
    name: str,              # Entity name
    file_path: str,         # Absolute path to source file
    line_no: int,           # Starting line number
    end_line_no: int,       # Ending line number
    properties: dict,       # Language-specific metadata
    code_snippet: str       # Source code excerpt
)
```

**Required properties for JS/TS:**
- `properties.language`: "javascript" or "typescript"
- `properties.parameters`: List of parameter names (for functions)
- `properties.is_async`: Boolean (for async functions)
- `properties.is_static`: Boolean (for static methods)
- `properties.parent_class`: String (for methods)
- `properties.declaration_type`: "const" | "let" | "var" (for variables)
- `properties.exported`: Boolean (for exported entities)
- `properties.export_type`: "named" | "default" (for exports)

#### Requirement: Consistent Relationship Structure
All parsers SHALL produce `CodeRelation` objects with identical structure.

**Schema:**
```python
CodeRelation(
    source_id: str,         # Source node ID
    target_id: str,         # Target node ID
    relation_type: str,     # "CONTAINS", "DEFINES", "CALLS", "IMPORTS", "INHERITS"
    properties: dict        # Additional metadata
)
```

**Supported relation types (reused from Python):**
- `CONTAINS`: File contains entity
- `DEFINES`: Class defines method/attribute
- `CALLS`: Function calls another function
- `IMPORTS`: File imports from module
- `INHERITS`: Class extends parent class

---

## NOT INCLUDED Requirements (Scope Control)

### ❌ TypeScript Interfaces
**Rationale:** Interfaces are compile-time only constructs that don't exist at runtime. They provide no runtime behavior to analyze.

**Future Consideration:** Could be added in Phase 2 if users need type relationship tracking.

### ❌ TypeScript Enums
**Rationale:** Enums can be handled, but they are less common in modern TypeScript (string unions preferred). Not essential for MVP.

**Future Consideration:** Could be added if user feedback indicates need.

### ❌ TypeScript Type Aliases
**Rationale:** Type aliases are compile-time only and provide no runtime behavior.

**Future Consideration:** Similar to interfaces, could be added for type relationship tracking.

### ❌ Decorators (Experimental)
**Rationale:** Decorators are still experimental in JavaScript and complex to parse correctly. Limited usage in most codebases.

**Future Consideration:** Add when decorators reach stable stage.

### ❌ Complex Generic Type Parameters
**Rationale:** Generic type parameters are compile-time only. Tracking them adds complexity without runtime value.

**Future Consideration:** Could be added if users need comprehensive type analysis.

### ❌ JSX/TSX Component Props Analysis
**Rationale:** While JSX components are parsed as classes/functions, detailed prop analysis is beyond Phase 1 scope.

**Future Consideration:** Add React-specific analysis in future iteration.

### ❌ CommonJS require() Statements
**Rationale:** Legacy module system. Most modern codebases use ES6 imports.

**Future Consideration:** Add if user feedback indicates significant CommonJS usage.

---

## Configuration

### New Environment Variables

```bash
# Enable/disable JavaScript/TypeScript parsing
# Default: true
ENABLE_JS_TS_PARSING=true

# Timeout for tree-sitter parsing per file (seconds)
# Default: 30
TREE_SITTER_TIMEOUT=30
```

### No Changes to Existing Configuration

All existing environment variables remain unchanged and functional:
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `OPENAI_API_KEY`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`
- `PARALLEL_INDEXING_ENABLED`, `MAX_WORKERS`, `MIN_FILES_FOR_PARALLEL`
- `NEO4J_MAX_CONNECTION_POOL_SIZE`

---

## Testing Requirements

### Unit Test Coverage
- **Target:** ≥ 90% coverage for `TypeScriptParser` class
- **Scope:** All public methods, error handling paths

### Integration Test Coverage
- **Required Tests:**
  - Mixed Python/JS/TS codebase processing
  - Parallel processing with multiple parser types
  - End-to-end: parse → embed → store → query

### Regression Test Coverage
- **Requirement:** 100% of existing tests SHALL pass without modification
- **Scope:** All tests in `tests/` directory
- **Validation:** Run full test suite before and after implementation

---

## Success Metrics

### Functional Success Metrics
✅ Parse 95%+ of valid JavaScript/TypeScript files successfully  
✅ Extract functions, classes, variables, imports correctly  
✅ Create proper relationships (CALLS, IMPORTS, INHERITS, DEFINES)  
✅ Handle parse errors without crashing  
✅ Support JSX/TSX syntax  

### Performance Success Metrics
✅ Python-only processing time: ≤ 105% of baseline  
✅ JS/TS parsing speed: ≥ 1000 LOC/second  
✅ Memory overhead: ≤ 50MB per worker  
✅ Parallel processing scales linearly  

### Quality Success Metrics
✅ Zero breaking changes to existing API  
✅ Code coverage: ≥ 90% for new code  
✅ All existing tests pass  
✅ Documentation: 100% complete  
✅ Code maintainability: Grade A or B  

---

## Migration Path

### For Existing Users (No Action Required)

1. **Update Installation:**
   ```bash
   git pull
   pip install -r requirements.txt
   ```

2. **Automatic Activation:**
   - JS/TS support enabled by default
   - Existing Python codebases work identically
   - No configuration changes needed

3. **Optional: Disable JS/TS:**
   ```bash
   export ENABLE_JS_TS_PARSING=false
   ```

### For New Users

Standard installation works for all languages:
```bash
git clone <repo>
cd graph-codebase-mcp
pip install -r requirements.txt
python src/main.py --codebase-path /path/to/codebase
```

---

## Appendix: Tree-sitter Query Examples

### Function Declaration Query
```scheme
(function_declaration
  name: (identifier) @name
  parameters: (formal_parameters) @params
  body: (statement_block) @body)
```

### Arrow Function Query
```scheme
(variable_declarator
  name: (identifier) @name
  value: (arrow_function
    parameters: (formal_parameters) @params
    body: (_) @body))
```

### Class Declaration Query
```scheme
(class_declaration
  name: (identifier) @name
  (class_heritage (extends_clause (identifier) @parent))?
  body: (class_body) @body)
```

### Import Statement Query
```scheme
(import_statement
  (import_clause
    (named_imports (import_specifier) @named)
    (identifier) @default)?
  source: (string) @source)
```

---

## Appendix: Example Output

### JavaScript Function
**Input:**
```javascript
export function calculateTotal(items, taxRate) {
  return items.reduce((sum, item) => sum + item.price, 0) * (1 + taxRate);
}
```

**Output:**
```python
CodeNode(
    node_id="file:/path/utils.js:function:calculateTotal",
    node_type="Function",
    name="calculateTotal",
    file_path="/path/utils.js",
    line_no=5,
    end_line_no=7,
    properties={
        "language": "javascript",
        "parameters": ["items", "taxRate"],
        "exported": True,
        "export_type": "named"
    },
    code_snippet="export function calculateTotal(items, taxRate) {\n  return items.reduce((sum, item) => sum + item.price, 0) * (1 + taxRate);\n}"
)
```

### TypeScript Class
**Input:**
```typescript
class Employee extends Person {
  constructor(name: string, employeeId: number) {
    super(name);
    this.employeeId = employeeId;
  }
  
  getId(): number {
    return this.employeeId;
  }
}
```

**Output:**
```python
# Class node
CodeNode(
    node_id="file:/path/employee.ts:class:Employee",
    node_type="Class",
    name="Employee",
    file_path="/path/employee.ts",
    line_no=1,
    end_line_no=10,
    properties={"language": "typescript"},
    code_snippet="class Employee extends Person { ... }"
)

# Inheritance relationship
CodeRelation(
    source_id="file:/path/employee.ts:class:Employee",
    target_id="file:/path/person.ts:class:Person",
    relation_type="INHERITS",
    properties={}
)

# Method node
CodeNode(
    node_id="file:/path/employee.ts:function:getId",
    node_type="Function",
    name="getId",
    file_path="/path/employee.ts",
    line_no=7,
    end_line_no=9,
    properties={
        "language": "typescript",
        "parameters": [],
        "parent_class": "Employee",
        "is_method": True
    },
    code_snippet="getId(): number {\n  return this.employeeId;\n}"
)

# Method definition relationship
CodeRelation(
    source_id="file:/path/employee.ts:class:Employee",
    target_id="file:/path/employee.ts:function:getId",
    relation_type="DEFINES",
    properties={}
)
```
