# parser Specification

## Purpose
TBD - created by archiving change add-js-ts-support. Update Purpose after archive.
## Requirements
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

