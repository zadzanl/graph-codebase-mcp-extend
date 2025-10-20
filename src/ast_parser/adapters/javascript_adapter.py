"""
JavaScript/TypeScript adapter using ast-grep.

使用 ast-grep 的 JavaScript/TypeScript 适配器
This adapter extracts code entities from JavaScript and TypeScript files
using the ast-grep-py library and produces output compatible with TypeScriptParser.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from ast_grep_py import SgRoot, SgNode

from src.ast_parser.parser import CodeNode, CodeRelation
from .base_adapter import LanguageAdapter

logger = logging.getLogger(__name__)


class JavaScriptAstGrepAdapter(LanguageAdapter):
    """
    JavaScript/TypeScript adapter using ast-grep for parsing.
    
    Extracts: Functions, Classes, Methods, Variables, Imports, Exports
    Creates relations: CONTAINS, DEFINES, EXTENDS, IMPORTS
    
    Maintains parity with TypeScriptParser output format.
    """

    def __init__(self, use_tsx: bool = False):
        """
        Initialize the JavaScript/TypeScript adapter.
        
        Args:
            use_tsx: Whether to use TSX parser (for React components)
        """
        # Determine language: tsx for .tsx files, typescript for .ts, javascript for .js/.jsx
        # This will be set per file in parse_file
        super().__init__("javascript")
        self.use_tsx = use_tsx
        self.current_file: str = ""
        self.current_class: Optional[str] = None
        self.imports: Dict[str, str] = {}  # {imported_name: module_path}

    def parse_file(self, file_path: str, build_index: bool = False) -> tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """
        Parse a JavaScript/TypeScript file using ast-grep.
        
        Args:
            file_path: Path to the file to parse
            build_index: Whether to build module definition index
            
        Returns:
            Tuple of (nodes dictionary, relations list)
        """
        self.current_file = file_path
        self.imports = {}
        
        try:
            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
            
            # Determine language based on file extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.ts':
                language = 'typescript'
            elif ext == '.tsx':
                language = 'tsx'
            elif ext == '.jsx':
                language = 'javascript'  # ast-grep handles JSX in javascript mode
            else:  # .js
                language = 'javascript'
            
            # Parse with ast-grep
            sg_root = SgRoot(source_code, language)
            root = sg_root.root()
            
            # Create file node
            file_node_id = self._create_file_node(file_path)
            
            # Generate module name for indexing
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            if build_index:
                if module_name not in self.module_definitions:
                    self.module_definitions[module_name] = {}
                self.module_to_file[module_name] = file_node_id
            
            # Extract entities in order
            self._parse_imports(root, file_node_id)
            self._parse_classes(root, file_node_id, build_index, module_name)
            self._parse_functions(root, file_node_id, build_index, module_name)
            self._parse_variables(root, file_node_id)
            self._parse_exports(root)
            
            return self.nodes, self.relations
            
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return {}, []

    def _parse_imports(self, root: SgNode, file_node_id: str) -> None:
        """
        Extract import statements.
        
        Handles:
        - import { a, b } from './module'
        - import Default from './module'
        - import * as ns from './module'
        """
        import_statements = root.find_all(kind="import_statement")
        
        for import_node in import_statements:
            source_module = None
            imported_names = []
            
            # Extract source module from string node
            string_nodes = import_node.find_all(kind="string")
            if string_nodes:
                source_module = string_nodes[0].text().strip('"\'')
            
            # Extract imported names from import_clause
            import_clauses = import_node.find_all(kind="import_clause")
            if import_clauses:
                import_clause = import_clauses[0]
                
                # Default import (identifier directly in clause)
                for child in import_clause.children():
                    if child.kind() == "identifier":
                        name = child.text()
                        imported_names.append(name)
                
                # Named imports
                named_imports = import_clause.find_all(kind="named_imports")
                if named_imports:
                    for named_import in named_imports:
                        # Find import_specifier nodes
                        specifiers = named_import.find_all(kind="import_specifier")
                        for spec in specifiers:
                            # Get identifier from specifier
                            identifiers = [c for c in spec.children() if c.kind() == "identifier"]
                            if identifiers:
                                imported_names.append(identifiers[0].text())
                
                # Namespace import (import * as name)
                namespace_imports = import_clause.find_all(kind="namespace_import")
                if namespace_imports:
                    for ns_import in namespace_imports:
                        identifiers = [c for c in ns_import.children() if c.kind() == "identifier"]
                        if identifiers:
                            imported_names.append(identifiers[0].text())
            
            # Store imports for later resolution
            if source_module:
                root_module = source_module.split('/')[0] if '/' in source_module else source_module
                
                for name in imported_names:
                    self.imports[name] = source_module
                    self.pending_imports.append({
                        "type": "IMPORTS",
                        "source_id": file_node_id,
                        "imported_module": root_module,
                        "imported_name": name,
                        "original_name": name,
                    })

    def _parse_classes(self, root: SgNode, file_node_id: str, build_index: bool, module_name: str) -> None:
        """
        Extract class declarations and their methods.
        
        Handles:
        - class Animal { ... }
        - class Dog extends Animal { ... }
        """
        class_declarations = root.find_all(kind="class_declaration")
        
        for class_node in class_declarations:
            # Get class name
            class_name = None
            for child in class_node.children():
                if child.kind() in ["identifier", "type_identifier"]:
                    class_name = child.text()
                    break
            
            if not class_name:
                continue
            
            line_no = class_node.range().start.line + 1
            end_line_no = class_node.range().end.line + 1
            
            # Create class node
            node_id = self._get_node_id("Class", class_name, self.current_file, line_no)
            self.nodes[node_id] = CodeNode(
                node_id=node_id,
                node_type="Class",
                name=class_name,
                file_path=self.current_file,
                line_no=line_no,
                end_line_no=end_line_no,
                properties={"language": self._get_language_from_file()},
            )
            self.nodes[node_id].code_snippet = class_node.text()
            
            # Create CONTAINS relation (file contains class)
            self._add_relation(CodeRelation(
                source_id=file_node_id,
                target_id=node_id,
                relation_type="CONTAINS"
            ))
            
            # Handle inheritance (extends clause)
            self._extract_class_inheritance(class_node, node_id)
            
            # Extract methods
            self._extract_class_methods(class_node, node_id, class_name)
            
            # Add to module definitions if building index
            if build_index and module_name:
                self.module_definitions[module_name][class_name] = node_id

    def _extract_class_inheritance(self, class_node: SgNode, class_node_id: str) -> None:
        """
        Extract class inheritance relationships (extends clause).
        
        Args:
            class_node: ast-grep node representing the class
            class_node_id: Node ID of the class
        """
        # Find class_heritage node
        heritage_nodes = class_node.find_all(kind="class_heritage")
        if not heritage_nodes:
            return
        
        heritage = heritage_nodes[0]
        # The heritage contains "extends ParentClass"
        # Find the identifier after "extends"
        identifiers = heritage.find_all(kind="identifier")
        if identifiers:
            parent_name = identifiers[0].text()
            
            # Check if parent is imported
            if parent_name in self.imports:
                source_module = self.imports[parent_name]
                root_module = source_module.split('/')[0] if '/' in source_module else source_module
                self.pending_imports.append({
                    "type": "EXTENDS",
                    "source_id": class_node_id,
                    "imported_module": root_module,
                    "imported_name": parent_name,
                    "original_name": parent_name
                })
            else:
                # Assume parent is in same file (though we may not find it)
                # Create inheritance relationship
                parent_node_id = f"Class:{self.current_file}:{parent_name}:0"
                self._add_relation(CodeRelation(
                    source_id=class_node_id,
                    target_id=parent_node_id,
                    relation_type="EXTENDS"
                ))

    def _extract_class_methods(self, class_node: SgNode, class_node_id: str, class_name: str) -> None:
        """
        Extract methods from a class.
        
        Args:
            class_node: ast-grep node representing the class
            class_node_id: Node ID of the class
            class_name: Name of the class
        """
        # Find class_body
        class_bodies = class_node.find_all(kind="class_body")
        if not class_bodies:
            return
        
        class_body = class_bodies[0]
        
        # Extract method definitions
        method_nodes = class_body.find_all(kind="method_definition")
        for method_node in method_nodes:
            # Get method name using field
            name_node = method_node.field("name")
            if not name_node:
                continue
            
            method_name = name_node.text()
            line_no = method_node.range().start.line + 1
            end_line_no = method_node.range().end.line + 1
            
            # Extract parameters
            params = self._extract_function_params(method_node)
            
            # Check if async
            is_async = self._is_async_function(method_node)
            
            # Create method node
            node_id = self._get_node_id("Method", method_name, self.current_file, line_no)
            self.nodes[node_id] = CodeNode(
                node_id=node_id,
                node_type="Method",
                name=method_name,
                file_path=self.current_file,
                line_no=line_no,
                end_line_no=end_line_no,
                properties={
                    "is_method": True,
                    "parent_class": class_name,
                    "parameters": params,
                    "language": self._get_language_from_file(),
                    "is_async": is_async,
                },
            )
            self.nodes[node_id].code_snippet = method_node.text()
            
            # Create DEFINES relation (class defines method)
            self._add_relation(CodeRelation(
                source_id=class_node_id,
                target_id=node_id,
                relation_type="DEFINES"
            ))

    def _parse_functions(self, root: SgNode, file_node_id: str, build_index: bool, module_name: str) -> None:
        """
        Extract function declarations (both standard and arrow functions).
        
        Handles:
        - function name() { ... }
        - const name = () => { ... }
        - const name = async () => { ... }
        """
        # Extract standard function declarations
        function_declarations = root.find_all(kind="function_declaration")
        for func_node in function_declarations:
            # Skip if inside a class (already handled as methods)
            if self._is_inside_class(func_node):
                continue
            
            # Get function name using field
            name_node = func_node.field("name")
            if not name_node:
                continue
            
            func_name = name_node.text()
            line_no = func_node.range().start.line + 1
            end_line_no = func_node.range().end.line + 1
            
            # Extract parameters
            params = self._extract_function_params(func_node)
            
            # Check if async
            is_async = self._is_async_function(func_node)
            
            # Create function node
            node_id = self._get_node_id("Function", func_name, self.current_file, line_no)
            self.nodes[node_id] = CodeNode(
                node_id=node_id,
                node_type="Function",
                name=func_name,
                file_path=self.current_file,
                line_no=line_no,
                end_line_no=end_line_no,
                properties={
                    "is_method": False,
                    "parameters": params,
                    "language": self._get_language_from_file(),
                    "function_style": "standard",
                    "is_async": is_async,
                },
            )
            self.nodes[node_id].code_snippet = func_node.text()
            
            # Create CONTAINS relation (file contains function)
            self._add_relation(CodeRelation(
                source_id=file_node_id,
                target_id=node_id,
                relation_type="CONTAINS"
            ))
            
            # Add to module definitions if building index
            if build_index and module_name:
                self.module_definitions[module_name][func_name] = node_id
        
        # Extract arrow functions (const name = () => ...)
        self._parse_arrow_functions(root, file_node_id, build_index, module_name)

    def _parse_arrow_functions(self, root: SgNode, file_node_id: str, build_index: bool, module_name: str) -> None:
        """
        Extract arrow function declarations.
        
        Handles: const name = (params) => { ... }
        """
        # Find lexical_declaration nodes that contain arrow_function
        lexical_declarations = root.find_all(kind="lexical_declaration")
        
        for lex_decl in lexical_declarations:
            # Skip if inside a class
            if self._is_inside_class(lex_decl):
                continue
            
            # Find variable_declarator with arrow_function
            variable_declarators = lex_decl.find_all(kind="variable_declarator")
            for var_decl in variable_declarators:
                # Check if it contains an arrow_function
                arrow_functions = var_decl.find_all(kind="arrow_function")
                if not arrow_functions:
                    continue
                
                arrow_func = arrow_functions[0]
                
                # Get function name from variable_declarator name field
                name_node = var_decl.field("name")
                if not name_node:
                    continue
                
                func_name = name_node.text()
                line_no = arrow_func.range().start.line + 1
                end_line_no = arrow_func.range().end.line + 1
                
                # Extract parameters
                params = self._extract_function_params(arrow_func)
                
                # Check if async
                is_async = self._is_async_function(arrow_func)
                
                # Create function node
                node_id = self._get_node_id("Function", func_name, self.current_file, line_no)
                self.nodes[node_id] = CodeNode(
                    node_id=node_id,
                    node_type="Function",
                    name=func_name,
                    file_path=self.current_file,
                    line_no=line_no,
                    end_line_no=end_line_no,
                    properties={
                        "is_method": False,
                        "parameters": params,
                        "language": self._get_language_from_file(),
                        "function_style": "arrow",
                        "is_async": is_async,
                    },
                )
                self.nodes[node_id].code_snippet = arrow_func.text()
                
                # Create CONTAINS relation (file contains function)
                self._add_relation(CodeRelation(
                    source_id=file_node_id,
                    target_id=node_id,
                    relation_type="CONTAINS"
                ))
                
                # Add to module definitions if building index
                if build_index and module_name:
                    self.module_definitions[module_name][func_name] = node_id

    def _parse_variables(self, root: SgNode, file_node_id: str) -> None:
        """
        Extract top-level variable declarations.
        
        Handles: const, let, var declarations that are not functions
        """
        # Track processed variables to avoid duplicates
        processed_vars = set()
        
        # Process lexical_declaration (const, let)
        lexical_declarations = root.find_all(kind="lexical_declaration")
        for lex_decl in lexical_declarations:
            # Skip if inside a class or function
            if not self._is_top_level(lex_decl):
                continue
            
            # Get declaration type (const, let)
            decl_type = "let"
            for child in lex_decl.children():
                if child.kind() in ["const", "let"]:
                    decl_type = child.kind()
                    break
            
            # Find variable_declarator nodes - only direct children, not nested ones
            # Using children() instead of find_all() to avoid recursion into nested scopes
            for child in lex_decl.children():
                if child.kind() != "variable_declarator":
                    continue
                
                var_decl = child
                
                # Check if it's an arrow function (already handled)
                # Check only immediate value, not recursively
                has_arrow = False
                for decl_child in var_decl.children():
                    if decl_child.kind() == "arrow_function":
                        has_arrow = True
                        break
                
                if has_arrow:
                    continue
                
                # Get variable name
                name_node = var_decl.field("name")
                if not name_node:
                    continue
                
                var_name = name_node.text()
                if var_name in processed_vars:
                    continue
                
                processed_vars.add(var_name)
                line_no = var_decl.range().start.line + 1
                
                # Create variable node
                node_id = self._get_node_id("Variable", var_name, self.current_file, line_no)
                self.nodes[node_id] = CodeNode(
                    node_id=node_id,
                    node_type="Variable",
                    name=var_name,
                    file_path=self.current_file,
                    line_no=line_no,
                    properties={
                        "declaration_type": decl_type,
                        "language": self._get_language_from_file(),
                    },
                )
                
                # Create CONTAINS relation (file contains variable)
                self._add_relation(CodeRelation(
                    source_id=file_node_id,
                    target_id=node_id,
                    relation_type="CONTAINS"
                ))
        
        # Process variable_declaration (var)
        variable_declarations = root.find_all(kind="variable_declaration")
        for var_decl_stmt in variable_declarations:
            # Skip if inside a class or function
            if not self._is_top_level(var_decl_stmt):
                continue
            
            # Find variable_declarator nodes - only direct children
            for child in var_decl_stmt.children():
                if child.kind() != "variable_declarator":
                    continue
                
                var_decl = child
                
                # Get variable name
                name_node = var_decl.field("name")
                if not name_node:
                    continue
                
                var_name = name_node.text()
                if var_name in processed_vars:
                    continue
                
                processed_vars.add(var_name)
                line_no = var_decl.range().start.line + 1
                
                # Create variable node
                node_id = self._get_node_id("Variable", var_name, self.current_file, line_no)
                self.nodes[node_id] = CodeNode(
                    node_id=node_id,
                    node_type="Variable",
                    name=var_name,
                    file_path=self.current_file,
                    line_no=line_no,
                    properties={
                        "declaration_type": "var",
                        "language": self._get_language_from_file(),
                    },
                )
                
                # Create CONTAINS relation (file contains variable)
                self._add_relation(CodeRelation(
                    source_id=file_node_id,
                    target_id=node_id,
                    relation_type="CONTAINS"
                ))

    def _parse_exports(self, root: SgNode) -> None:
        """
        Extract export statements and mark exported entities.
        
        Handles:
        - export function name() { ... }
        - export class Name { ... }
        - export const name = ...
        - export { name1, name2 }
        """
        export_statements = root.find_all(kind="export_statement")
        
        for export_node in export_statements:
            # Check for directly exported declarations
            for child in export_node.children():
                entity_name = None
                
                if child.kind() == "function_declaration":
                    name_node = child.field("name")
                    if name_node:
                        entity_name = name_node.text()
                
                elif child.kind() == "class_declaration":
                    # Get class name
                    for class_child in child.children():
                        if class_child.kind() in ["identifier", "type_identifier"]:
                            entity_name = class_child.text()
                            break
                
                elif child.kind() == "lexical_declaration":
                    # Get variable name from variable_declarator
                    var_declarators = child.find_all(kind="variable_declarator")
                    if var_declarators:
                        name_node = var_declarators[0].field("name")
                        if name_node:
                            entity_name = name_node.text()
                
                elif child.kind() == "export_clause":
                    # Named exports: export { name1, name2 }
                    export_specifiers = child.find_all(kind="export_specifier")
                    for spec in export_specifiers:
                        identifiers = [c for c in spec.children() if c.kind() == "identifier"]
                        if identifiers:
                            entity_name = identifiers[0].text()
                            # Mark as exported
                            for node_id, code_node in self.nodes.items():
                                if code_node.name == entity_name and code_node.file_path == self.current_file:
                                    code_node.properties["exported"] = True
                                    code_node.properties["export_type"] = "named"
                    continue
                
                # Mark entity as exported
                if entity_name:
                    for node_id, code_node in self.nodes.items():
                        if code_node.name == entity_name and code_node.file_path == self.current_file:
                            code_node.properties["exported"] = True
                            code_node.properties["export_type"] = "named"

    def _extract_function_params(self, func_node: SgNode) -> List[str]:
        """
        Extract parameter names from a function.
        
        Args:
            func_node: ast-grep node representing the function
            
        Returns:
            List of parameter names
        """
        params = []
        
        # Find formal_parameters node
        formal_params = func_node.find_all(kind="formal_parameters")
        if not formal_params:
            return params
        
        formal_param = formal_params[0]
        
        # Extract identifiers (parameter names)
        for child in formal_param.children():
            if child.kind() == "identifier":
                params.append(child.text())
            elif child.kind() in ["required_parameter", "optional_parameter"]:
                # TypeScript parameters - extract identifier
                for param_child in child.children():
                    if param_child.kind() == "identifier":
                        params.append(param_child.text())
                        break
        
        return params

    def _is_async_function(self, func_node: SgNode) -> bool:
        """
        Check if a function is async.
        
        Args:
            func_node: ast-grep node representing the function
            
        Returns:
            True if the function is async, False otherwise
        """
        # Check for 'async' keyword as a child
        for child in func_node.children():
            if child.kind() == "async":
                return True
        return False

    def _is_inside_class(self, node: SgNode) -> bool:
        """
        Check if a node is inside a class declaration.
        
        Args:
            node: ast-grep node to check
            
        Returns:
            True if inside a class, False otherwise
        """
        current = node.parent()
        while current:
            if current.kind() == "class_declaration":
                return True
            current = current.parent()
        return False

    def _is_top_level(self, node: SgNode) -> bool:
        """
        Check if a node is at the top level (not inside a function or class).
        
        Args:
            node: ast-grep node to check
            
        Returns:
            True if at top level, False otherwise
        """
        current = node.parent()
        while current:
            # Check if we're inside a function or class context
            # statement_block indicates we're inside a function/method body
            if current.kind() in ["function_declaration", "arrow_function", "class_declaration", 
                                   "method_definition", "statement_block"]:
                # Exception: statement_block at program level is OK (can happen in some contexts)
                # But if statement_block has arrow_function or function_declaration parent, it's nested
                if current.kind() == "statement_block":
                    # Check if this statement_block is part of a function
                    parent = current.parent()
                    if parent and parent.kind() in ["function_declaration", "arrow_function", "method_definition"]:
                        return False
                else:
                    return False
            current = current.parent()
        return True

    def _get_language_from_file(self) -> str:
        """
        Determine the language from the current file extension.
        
        Returns:
            Language name (javascript, typescript, jsx, tsx)
        """
        ext = os.path.splitext(self.current_file)[1].lower()
        if ext == '.ts':
            return 'typescript'
        elif ext == '.tsx':
            return 'tsx'
        elif ext == '.jsx':
            return 'jsx'
        else:
            return 'javascript'
