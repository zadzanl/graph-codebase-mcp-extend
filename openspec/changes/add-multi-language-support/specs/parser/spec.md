## MODIFIED Requirements

### Requirement: Language-Agnostic Parsing
The system SHALL support multiple programming languages by using a parser factory that selects the appropriate parser based on file extension.

#### Scenario: Python file
- **WHEN** a `.py` file is processed
- **THEN** the system SHALL use the Python AST parser.

#### Scenario: TypeScript file
- **WHEN** a `.ts` file is processed
- **THEN** the system SHALL use the Tree-sitter TypeScript parser.

#### Scenario: JavaScript file
- **WHEN** a `.js` file is processed
- **THEN** the system SHALL use the Tree-sitter JavaScript parser.

## ADDED Requirements

### Requirement: Parse Function Declarations
The system SHALL identify function declarations in JavaScript and TypeScript files.

#### Scenario: Standard function
- **WHEN** a file contains `function myFunction() {}`
- **THEN** a `Function` node with the name `myFunction` SHALL be created.

### Requirement: Parse Arrow Functions
The system SHALL identify arrow functions assigned to variables in JavaScript and TypeScript files.

#### Scenario: Arrow function
- **WHEN** a file contains `const myArrowFunction = () => {}`
- **THEN** a `Function` node with the name `myArrowFunction` SHALL be created.

### Requirement: Parse Class Declarations
The system SHALL identify class declarations in JavaScript and TypeScript files.

#### Scenario: Class declaration
- **WHEN** a file contains `class MyClass {}`
- **THEN** a `Class` node with the name `MyClass` SHALL be created.

### Requirement: Parse Import Statements
The system SHALL identify import statements in JavaScript and TypeScript files.

#### Scenario: Import statement
- **WHEN** a file contains `import { MyClass } from './my-class';`
- **THEN** an `IMPORTS` relationship SHALL be created from the file to the imported module.

### Requirement: Parse Export Statements
The system SHALL identify export statements in JavaScript and TypeScript files.

#### Scenario: Export statement
- **WHEN** a file contains `export class MyClass {}`
- **THEN** the `MyClass` node SHALL be marked as exported.

### Requirement: Parse Interface Declarations
The system SHALL identify interface declarations in TypeScript files.

#### Scenario: Interface declaration
- **WHEN** a file contains `interface MyInterface {}`
- **THEN** an `Interface` node with the name `MyInterface` SHALL be created.

### Requirement: Parse Enum Declarations
The system SHALL identify enum declarations in TypeScript files.

#### Scenario: Enum declaration
- **WHEN** a file contains `enum MyEnum {}`
- **THEN** an `Enum` node with the name `MyEnum` SHALL be created.

### Requirement: Parse Type Alias Declarations
The system SHALL identify type alias declarations in TypeScript files.

#### Scenario: Type alias declaration
- **WHEN** a file contains `type MyType = string;`
- **THEN** a `TypeAlias` node with the name `MyType` SHALL be created.
