import os
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Parser, Node, Query, QueryCursor

from src.ast_parser.parser import CodeNode, CodeRelation

logger = logging.getLogger(__name__)


class TypeScriptParser:
    """Parser for JavaScript and TypeScript files using tree-sitter.
    
    This parser extracts code entities (functions, classes, variables, imports)
    from JavaScript and TypeScript files and produces the same output format as
    the Python ASTParser, ensuring compatibility with the rest of the system.
    """

    def __init__(self):
        """Initialize the TypeScript/JavaScript parser."""
        self.nodes: Dict[str, CodeNode] = {}
        self.relations: List[CodeRelation] = []
        self.current_file: str = ""
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        self.imports: Dict[str, str] = {}
        self.module_definitions: Dict[str, Dict[str, str]] = {}
        self.pending_imports: List[Dict[str, Any]] = []
        self.module_to_file: Dict[str, str] = {}
        self.established_relations: Set[str] = set()
        
        # Initialize tree-sitter parsers for JavaScript and TypeScript
        try:
            self.js_language = Language(tree_sitter_javascript.language())
            self.ts_language = Language(tree_sitter_typescript.language_typescript())
            self.tsx_language = Language(tree_sitter_typescript.language_tsx())
            self.js_parser = Parser(self.js_language)
            self.ts_parser = Parser(self.ts_language)
            self.tsx_parser = Parser(self.tsx_language)
            logger.info("TypeScriptParser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TypeScriptParser: {e}")
            raise

    def parse_directory(self, directory_path: str) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """Parse all JavaScript/TypeScript files in the directory.
        
        Args:
            directory_path: Path to the directory to parse
            
        Returns:
            Tuple of (nodes dictionary, relations list)
        """
        self.nodes = {}
        self.relations = []
        self.module_definitions = {}
        self.pending_imports = []
        self.module_to_file = {}
        self.established_relations = set()

        # First pass: create all nodes and build module definition index
        for root, _, files in os.walk(directory_path):
            for file_name in files:
                if file_name.endswith(('.js', '.ts', '.jsx', '.tsx')):
                    file_path = os.path.join(root, file_name)
                    self.parse_file(file_path, build_index=True)

        # Second pass: process all pending import relationships
        self._process_pending_imports()

        return self.nodes, self.relations

    def parse_file(self, file_path: str, build_index: bool = False) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """Parse a single JavaScript/TypeScript file.
        
        Args:
            file_path: Path to the file to parse
            build_index: Whether to build module definition index
            
        Returns:
            Tuple of (nodes dictionary, relations list)
        """
        print(f"Parsing file: {file_path}")
        self.current_file = file_path
        self.imports = {}
        
        # Reset nodes and relations if not building an index (standalone parse)
        if not build_index:
            self.nodes = {}
            self.relations = []

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                file_content = file.read()
                
                # Select appropriate parser based on file extension
                parser = self._get_parser_for_file(file_path)
                tree = parser.parse(bytes(file_content, "utf8"))
                
                file_node_id = self._create_file_node(file_path)
                
                # Generate module name for indexing
                module_name = os.path.splitext(os.path.basename(file_path))[0]
                if build_index:
                    if module_name not in self.module_definitions:
                        self.module_definitions[module_name] = {}
                    # Associate module name with file node
                    self.module_to_file[module_name] = file_node_id
                
                # Parse the syntax tree
                self._parse_tree(tree.root_node, file_content, build_index, module_name)

            return self.nodes, self.relations
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            print(f"Error parsing file {file_path}: {e}")
            return {}, []

    def _get_parser_for_file(self, file_path: str) -> Parser:
        """Select the appropriate parser based on file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tree-sitter parser instance
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.ts':
            return self.ts_parser
        elif ext in ['.tsx']:
            return self.tsx_parser
        else:  # .js, .jsx
            return self.js_parser

    def _create_file_node(self, file_path: str) -> str:
        """Create a file node.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Node ID of the created file node
        """
        file_name = os.path.basename(file_path)
        node_id = f"file:{file_path}"
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="File",
            name=file_name,
            file_path=file_path,
            line_no=0,
        )
        return node_id

    def _get_node_id(self, node_type: str, name: str, file_path: str, line_no: int) -> str:
        """Generate a unique identifier for a node.
        
        Args:
            node_type: Type of the node (Function, Class, Variable, etc.)
            name: Name of the entity
            file_path: Path to the file
            line_no: Line number where the entity is defined
            
        Returns:
            Unique node ID
        """
        return f"{node_type}:{file_path}:{name}:{line_no}"

    def _parse_tree(self, root_node: Node, source_code: str, build_index: bool = False, module_name: str = "") -> None:
        """Parse the tree-sitter syntax tree.
        
        Args:
            root_node: Root node of the syntax tree
            source_code: Source code of the file
            build_index: Whether to build module definition index
            module_name: Name of the module
        """
        # Determine which language to use for queries
        language = self._get_query_language()
        
        # Extract functions (including arrow functions)
        self._extract_functions(root_node, source_code, build_index, module_name, language)
        
        # Extract classes
        self._extract_classes(root_node, source_code, build_index, module_name, language)
        
        # Extract top-level variables
        self._extract_variables(root_node, source_code, language)
        
        # Extract imports
        self._extract_imports(root_node, source_code, language)
        
        # Extract exports
        self._extract_exports(root_node, source_code, language)

    def _extract_functions(self, root_node: Node, source_code: str, build_index: bool = False, module_name: str = "", language: Language = None) -> None:
        """Extract function declarations from the syntax tree.
        
        Args:
            root_node: Root node of the syntax tree
            source_code: Source code of the file
            build_index: Whether to build module definition index
            module_name: Name of the module
            language: Tree-sitter language object for queries
        """
        if language is None:
            language = self.js_language
            
        # Extract standard function declarations
        try:
            query_str = "(function_declaration name: (identifier) @name) @function"
            query = Query(language, query_str)
            cursor = QueryCursor(query)
            capture_dict = cursor.captures(root_node)
            
            if "function" in capture_dict and "name" in capture_dict:
                # Match functions with their names
                for func_node in capture_dict["function"]:
                    # Skip if inside a class
                    if self._is_inside_class(func_node):
                        continue
                    
                    # Find the corresponding name
                    func_name = None
                    for name_node in capture_dict["name"]:
                        if name_node.parent == func_node or func_node == name_node.parent.parent:
                            func_name = self._get_node_text(name_node, source_code)
                            break
                    
                    if func_name:
                        line_no = func_node.start_point[0] + 1
                        end_line_no = func_node.end_point[0] + 1
                        node_id = self._get_node_id("Function", func_name, self.current_file, line_no)
                        
                        params = self._extract_function_params(func_node, source_code)
                        is_async = self._is_async_function(func_node)
                        
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
                        
                        self.nodes[node_id].code_snippet = self._get_node_text(func_node, source_code)
                        
                        file_node_id = f"file:{self.current_file}"
                        self.relations.append(
                            CodeRelation(
                                source_id=file_node_id,
                                target_id=node_id,
                                relation_type="CONTAINS",
                            )
                        )
                        
                        if build_index and module_name:
                            self.module_definitions[module_name][func_name] = node_id
        except Exception as e:
            logger.warning(f"Error extracting standard functions: {e}")
        
        # Extract arrow functions
        try:
            query_str = "(lexical_declaration (variable_declarator name: (identifier) @name value: (arrow_function) @arrow))"
            query = Query(language, query_str)
            cursor = QueryCursor(query)
            capture_dict = cursor.captures(root_node)
            
            if "arrow" in capture_dict and "name" in capture_dict:
                # Match arrow functions with their names
                arrow_nodes = capture_dict["arrow"]
                name_nodes = capture_dict["name"]
                
                for i, arrow_node in enumerate(arrow_nodes):
                    # Skip if inside a class
                    if self._is_inside_class(arrow_node):
                        continue
                    
                    # The name should be at the same index
                    if i < len(name_nodes):
                        func_name = self._get_node_text(name_nodes[i], source_code)
                        line_no = arrow_node.start_point[0] + 1
                        end_line_no = arrow_node.end_point[0] + 1
                        node_id = self._get_node_id("Function", func_name, self.current_file, line_no)
                        
                        params = self._extract_function_params(arrow_node, source_code)
                        
                        # Check if async - the async keyword is a direct child of arrow_function
                        is_async = self._is_async_function(arrow_node)
                        
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
                        
                        self.nodes[node_id].code_snippet = self._get_node_text(arrow_node, source_code)
                        
                        file_node_id = f"file:{self.current_file}"
                        self.relations.append(
                            CodeRelation(
                                source_id=file_node_id,
                                target_id=node_id,
                                relation_type="CONTAINS",
                            )
                        )
                        
                        if build_index and module_name:
                            self.module_definitions[module_name][func_name] = node_id
        except Exception as e:
            logger.warning(f"Error extracting arrow functions: {e}")

    def _extract_classes(self, root_node: Node, source_code: str, build_index: bool = False, module_name: str = "", language: Language = None) -> None:
        """Extract class declarations from the syntax tree.
        
        Args:
            root_node: Root node of the syntax tree
            source_code: Source code of the file
            build_index: Whether to build module definition index
            module_name: Name of the module
            language: Tree-sitter language object for queries
        """
        if language is None:
            language = self.js_language
            
        # Use simpler query and extract name manually to support both JS and TS
        query_str = "(class_declaration) @class"
        
        try:
            query = Query(language, query_str)
            cursor = QueryCursor(query)
            capture_dict = cursor.captures(root_node)
            
            processed_classes = set()
            
            for node in capture_dict.get("class", []):
                # Find the class name - can be identifier (JS) or type_identifier (TS)
                class_name = None
                for child in node.children:
                    if child.type in ["identifier", "type_identifier"]:
                        class_name = self._get_node_text(child, source_code)
                        break
                
                if class_name and class_name not in processed_classes:
                        processed_classes.add(class_name)
                        line_no = node.start_point[0] + 1
                        end_line_no = node.end_point[0] + 1
                        
                        node_id = self._get_node_id("Class", class_name, self.current_file, line_no)
                        
                        # Create class node
                        self.nodes[node_id] = CodeNode(
                            node_id=node_id,
                            node_type="Class",
                            name=class_name,
                            file_path=self.current_file,
                            line_no=line_no,
                            end_line_no=end_line_no,
                            properties={
                                "language": self._get_language_from_file(),
                            },
                        )
                        
                        # Add code snippet
                        self.nodes[node_id].code_snippet = self._get_node_text(node, source_code)
                        
                        # Create relationship: file contains class
                        file_node_id = f"file:{self.current_file}"
                        self.relations.append(
                            CodeRelation(
                                source_id=file_node_id,
                                target_id=node_id,
                                relation_type="CONTAINS",
                            )
                        )
                        
                        # Handle inheritance (extends clause)
                        self._extract_class_inheritance(node, node_id, source_code)
                        
                        # Extract methods
                        self._extract_class_methods(node, node_id, class_name, source_code)
                        
                        # Add to module definitions if building index
                        if build_index and module_name:
                            self.module_definitions[module_name][class_name] = node_id
                            
        except Exception as e:
            logger.warning(f"Error extracting classes: {e}")

    def _extract_class_inheritance(self, class_node: Node, class_node_id: str, source_code: str) -> None:
        """Extract class inheritance relationships.
        
        Args:
            class_node: Tree-sitter node representing the class
            class_node_id: Node ID of the class
            source_code: Source code of the file
        """
        try:
            # Look for class_heritage (extends clause)
            for child in class_node.children:
                if child.type == "class_heritage":
                    # The first child should be 'extends', second is the parent class
                    for heritage_child in child.children:
                        if heritage_child.type == "identifier":
                            parent_name = self._get_node_text(heritage_child, source_code)
                            
                            # Check if parent is imported
                            if parent_name in self.imports:
                                self.pending_imports.append({
                                    "type": "EXTENDS",
                                    "source_id": class_node_id,
                                    "imported_module": self.imports[parent_name].split(".")[0],
                                    "imported_name": self.imports[parent_name].split(".")[-1] 
                                        if "." in self.imports[parent_name] else self.imports[parent_name],
                                    "original_name": parent_name
                                })
                            else:
                                # Create inheritance relationship (assume parent is in same file)
                                parent_node_id = f"Class:{self.current_file}:{parent_name}:0"
                                self.relations.append(
                                    CodeRelation(
                                        source_id=class_node_id,
                                        target_id=parent_node_id,
                                        relation_type="EXTENDS",
                                    )
                                )
        except Exception as e:
            logger.warning(f"Error extracting class inheritance: {e}")

    def _extract_class_methods(self, class_node: Node, class_node_id: str, class_name: str, source_code: str) -> None:
        """Extract methods from a class.
        
        Args:
            class_node: Tree-sitter node representing the class
            class_node_id: Node ID of the class
            class_name: Name of the class
            source_code: Source code of the file
        """
        try:
            # Look for class_body
            for child in class_node.children:
                if child.type == "class_body":
                    # Extract method definitions
                    for method_node in child.children:
                        if method_node.type == "method_definition":
                            # Get method name
                            method_name = None
                            is_async = False
                            
                            for method_child in method_node.children:
                                if method_child.type == "property_identifier":
                                    method_name = self._get_node_text(method_child, source_code)
                                elif method_child.type == "async":
                                    is_async = True
                            
                            if method_name:
                                line_no = method_node.start_point[0] + 1
                                end_line_no = method_node.end_point[0] + 1
                                
                                node_id = self._get_node_id("Method", method_name, self.current_file, line_no)
                                
                                # Extract parameters
                                params = self._extract_function_params(method_node, source_code)
                                
                                # Create method node
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
                                
                                # Add code snippet
                                self.nodes[node_id].code_snippet = self._get_node_text(method_node, source_code)
                                
                                # Create relationship: class defines method
                                self.relations.append(
                                    CodeRelation(
                                        source_id=class_node_id,
                                        target_id=node_id,
                                        relation_type="DEFINES",
                                    )
                                )
        except Exception as e:
            logger.warning(f"Error extracting class methods: {e}")

    def _extract_variables(self, root_node: Node, source_code: str, language: Language = None) -> None:
        """Extract top-level variable declarations from the syntax tree.
        
        Args:
            root_node: Root node of the syntax tree
            source_code: Source code of the file
            language: Tree-sitter language object for queries
        """
        if language is None:
            language = self.js_language
        
        processed_vars = set()
        
        # Query for lexical declarations (const, let)
        query_str_lexical = """
        (lexical_declaration
          (variable_declarator
            name: (identifier) @name)) @declaration
        """
        
        # Query for variable declarations (var)
        query_str_var = """
        (variable_declaration
          (variable_declarator
            name: (identifier) @name)) @declaration
        """
        
        # Process both types of declarations
        for query_str in [query_str_lexical, query_str_var]:
            try:
                query = Query(language, query_str)
                cursor = QueryCursor(query)
                capture_dict = cursor.captures(root_node)
                captures = []
                for capture_name, nodes in capture_dict.items():
                    for node in nodes:
                        captures.append((node, capture_name))
                
                for node, capture_name in captures:
                    if capture_name == "declaration":
                        # Check if this is a top-level declaration (not inside function/class)
                        if self._is_top_level(node):
                            # Find the variable name
                            var_name = None
                            for child_node, child_capture in captures:
                                if child_capture == "name" and self._is_ancestor(node, child_node):
                                    var_name = self._get_node_text(child_node, source_code)
                                    break
                            
                            if var_name and var_name not in processed_vars:
                                # Check if this is an arrow function (already handled)
                                is_function = False
                                for child in node.children:
                                    if child.type == "variable_declarator":
                                        for decl_child in child.children:
                                            if "arrow_function" in decl_child.type:
                                                is_function = True
                                                break
                                
                                if not is_function:
                                    processed_vars.add(var_name)
                                    line_no = node.start_point[0] + 1
                                    
                                    # Determine declaration type (const, let, var)
                                    decl_type = "let"
                                    for child in node.children:
                                        if child.type in ["const", "let", "var"]:
                                            decl_type = child.type
                                            break
                                    
                                    node_id = self._get_node_id("Variable", var_name, self.current_file, line_no)
                                    
                                    # Create variable node
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
                                    
                                    # Create relationship: file contains variable
                                    file_node_id = f"file:{self.current_file}"
                                    self.relations.append(
                                        CodeRelation(
                                            source_id=file_node_id,
                                            target_id=node_id,
                                            relation_type="CONTAINS",
                                        )
                                    )
                                    
            except Exception as e:
                logger.warning(f"Error extracting variables: {e}")

    def _extract_imports(self, root_node: Node, source_code: str, language: Language = None) -> None:
        """Extract import statements from the syntax tree.
        
        Args:
            root_node: Root node of the syntax tree
            source_code: Source code of the file
            language: Tree-sitter language object for queries
        """
        if language is None:
            language = self.js_language
            
        # Query for import statements
        query_str = "(import_statement) @import"
        
        try:
            query = Query(language, query_str)
            cursor = QueryCursor(query)
            capture_dict = cursor.captures(root_node)
            captures = []
            for capture_name, nodes in capture_dict.items():
                for node in nodes:
                    captures.append((node, capture_name))
            
            file_node_id = f"file:{self.current_file}"
            
            for node, capture_name in captures:
                if capture_name == "import":
                    # Extract source module
                    source_module = None
                    imported_names = []
                    
                    for child in node.children:
                        if child.type == "string":
                            # Remove quotes from string
                            source_module = self._get_node_text(child, source_code).strip('"\'')
                        elif child.type == "import_clause":
                            # Extract imported names
                            imported_names = self._extract_import_names(child, source_code)
                    
                    if source_module:
                        # Add to imports mapping
                        for name in imported_names:
                            self.imports[name] = source_module
                        
                        # Add to pending imports for later resolution
                        root_module = source_module.split('/')[0] if '/' in source_module else source_module
                        
                        for name in imported_names:
                            self.pending_imports.append({
                                "type": "IMPORTS",
                                "source_id": file_node_id,
                                "imported_module": root_module,
                                "imported_name": name,
                                "original_name": name,
                            })
                            
        except Exception as e:
            logger.warning(f"Error extracting imports: {e}")

    def _extract_import_names(self, import_clause: Node, source_code: str) -> List[str]:
        """Extract names from an import clause.
        
        Args:
            import_clause: Tree-sitter node representing the import clause
            source_code: Source code of the file
            
        Returns:
            List of imported names
        """
        names = []
        
        try:
            for child in import_clause.children:
                if child.type == "identifier":
                    # Default import
                    names.append(self._get_node_text(child, source_code))
                elif child.type == "named_imports":
                    # Named imports
                    for named_child in child.children:
                        if named_child.type == "import_specifier":
                            for spec_child in named_child.children:
                                if spec_child.type == "identifier":
                                    names.append(self._get_node_text(spec_child, source_code))
                elif child.type == "namespace_import":
                    # Namespace import (import * as name)
                    for ns_child in child.children:
                        if ns_child.type == "identifier":
                            names.append(self._get_node_text(ns_child, source_code))
        except Exception as e:
            logger.warning(f"Error extracting import names: {e}")
        
        return names

    def _extract_exports(self, root_node: Node, source_code: str, language: Language = None) -> None:
        """Extract export statements from the syntax tree.
        
        Args:
            root_node: Root node of the syntax tree
            source_code: Source code of the file
            language: Tree-sitter language object for queries
        """
        if language is None:
            language = self.js_language
            
        # Query for export statements
        query_str = "(export_statement) @export"
        
        try:
            query = Query(language, query_str)
            cursor = QueryCursor(query)
            capture_dict = cursor.captures(root_node)
            captures = []
            for capture_name, nodes in capture_dict.items():
                for node in nodes:
                    captures.append((node, capture_name))
            
            for node, capture_name in captures:
                if capture_name == "export":
                    # Mark exported entities
                    for child in node.children:
                        if child.type in ["function_declaration", "class_declaration", "lexical_declaration"]:
                            # Find the name of the exported entity
                            entity_name = self._extract_entity_name(child, source_code)
                            if entity_name:
                                # Find the corresponding node and mark as exported
                                for node_id, code_node in self.nodes.items():
                                    if code_node.name == entity_name and code_node.file_path == self.current_file:
                                        code_node.properties["exported"] = True
                                        code_node.properties["export_type"] = "named"
                        elif child.type == "export_clause":
                            # Named exports without declaration
                            for export_child in child.children:
                                if export_child.type == "export_specifier":
                                    for spec_child in export_child.children:
                                        if spec_child.type == "identifier":
                                            entity_name = self._get_node_text(spec_child, source_code)
                                            # Mark as exported
                                            for node_id, code_node in self.nodes.items():
                                                if code_node.name == entity_name and code_node.file_path == self.current_file:
                                                    code_node.properties["exported"] = True
                                                    code_node.properties["export_type"] = "named"
                                            
        except Exception as e:
            logger.warning(f"Error extracting exports: {e}")

    def _extract_entity_name(self, node: Node, source_code: str) -> Optional[str]:
        """Extract the name of an entity (function, class, variable).
        
        Args:
            node: Tree-sitter node representing the entity
            source_code: Source code of the file
            
        Returns:
            Name of the entity, or None if not found
        """
        try:
            for child in node.children:
                if child.type == "identifier":
                    return self._get_node_text(child, source_code)
                elif child.type == "variable_declarator":
                    for decl_child in child.children:
                        if decl_child.type == "identifier":
                            return self._get_node_text(decl_child, source_code)
        except Exception as e:
            logger.warning(f"Error extracting entity name: {e}")
        
        return None

    def _extract_function_params(self, func_node: Node, source_code: str) -> List[str]:
        """Extract parameters from a function node.
        
        Args:
            func_node: Tree-sitter node representing the function
            source_code: Source code of the file
            
        Returns:
            List of parameter names
        """
        params = []
        
        try:
            for child in func_node.children:
                if child.type == "formal_parameters":
                    for param_child in child.children:
                        if param_child.type == "identifier":
                            params.append(self._get_node_text(param_child, source_code))
                        elif param_child.type in ["required_parameter", "optional_parameter"]:
                            # TypeScript parameters
                            for ts_param_child in param_child.children:
                                if ts_param_child.type == "identifier":
                                    params.append(self._get_node_text(ts_param_child, source_code))
        except Exception as e:
            logger.warning(f"Error extracting function parameters: {e}")
        
        return params

    def _is_async_function(self, func_node: Node) -> bool:
        """Check if a function is async.
        
        Args:
            func_node: Tree-sitter node representing the function
            
        Returns:
            True if the function is async, False otherwise
        """
        try:
            for child in func_node.children:
                if child.type == "async":
                    return True
        except Exception as e:
            logger.warning(f"Error checking async function: {e}")
        
        return False

    def _is_inside_class(self, node: Node) -> bool:
        """Check if a node is inside a class.
        
        Args:
            node: Tree-sitter node to check
            
        Returns:
            True if the node is inside a class, False otherwise
        """
        current = node.parent
        while current:
            if current.type == "class_declaration":
                return True
            current = current.parent
        return False

    def _is_top_level(self, node: Node) -> bool:
        """Check if a node is at the top level (not inside a function or class).
        
        Args:
            node: Tree-sitter node to check
            
        Returns:
            True if the node is at the top level, False otherwise
        """
        current = node.parent
        while current:
            if current.type in ["function_declaration", "arrow_function", "class_declaration", "method_definition"]:
                return False
            current = current.parent
        return True

    def _is_ancestor(self, ancestor: Node, descendant: Node) -> bool:
        """Check if one node is an ancestor of another.
        
        Args:
            ancestor: Potential ancestor node
            descendant: Potential descendant node
            
        Returns:
            True if ancestor is an ancestor of descendant, False otherwise
        """
        current = descendant.parent
        while current:
            if current == ancestor:
                return True
            current = current.parent
        return False

    def _get_node_text(self, node: Node, source_code: str) -> str:
        """Get the text content of a tree-sitter node.
        
        Args:
            node: Tree-sitter node
            source_code: Source code of the file
            
        Returns:
            Text content of the node
        """
        return source_code[node.start_byte:node.end_byte]

    def _get_language_from_file(self) -> str:
        """Determine the language from the current file extension.
        
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

    def _get_query_language(self) -> Language:
        """Get the tree-sitter language object for queries based on current file.
        
        Returns:
            Tree-sitter Language object for the current file's language
        """
        ext = os.path.splitext(self.current_file)[1].lower()
        if ext == '.ts':
            return self.ts_language
        elif ext == '.tsx':
            return self.tsx_language
        else:
            # Use JS language for .js and .jsx
            return self.js_language

    def _process_pending_imports(self) -> None:
        """Process pending import relationships.
        
        This method is called after all files have been parsed to resolve
        import relationships between modules.
        """
        for import_info in self.pending_imports:
            try:
                import_type = import_info["type"]
                source_id = import_info["source_id"]
                imported_module = import_info["imported_module"]
                imported_name = import_info["imported_name"]
                
                # Look up the target node in module definitions
                if imported_module in self.module_definitions:
                    if imported_name in self.module_definitions[imported_module]:
                        target_id = self.module_definitions[imported_module][imported_name]
                        
                        # Create the relationship
                        relation_key = f"{source_id}:{import_type}:{target_id}"
                        if relation_key not in self.established_relations:
                            self.relations.append(
                                CodeRelation(
                                    source_id=source_id,
                                    target_id=target_id,
                                    relation_type=import_type,
                                )
                            )
                            self.established_relations.add(relation_key)
                    else:
                        # Try to link to the file node if specific entity not found
                        if imported_module in self.module_to_file:
                            target_id = self.module_to_file[imported_module]
                            relation_key = f"{source_id}:{import_type}:{target_id}"
                            if relation_key not in self.established_relations:
                                self.relations.append(
                                    CodeRelation(
                                        source_id=source_id,
                                        target_id=target_id,
                                        relation_type=import_type,
                                        properties={"imported_name": imported_name},
                                    )
                                )
                                self.established_relations.add(relation_key)
            except Exception as e:
                logger.warning(f"Error processing pending import: {e}")
