"""Python language adapter using ast-grep for AST parsing."""

import os
import json
from typing import Dict, List, Optional, Tuple, Any, Union, Set

from ast_grep_py import SgRoot, SgNode

from .base_adapter import LanguageAdapter
from ast_parser.parser import CodeNode, CodeRelation


class PythonAstGrepAdapter(LanguageAdapter):
    """
    Python adapter using ast-grep library.
    
    Extracts identical information to ASTParser for parity:
    - File, Class, Method, Function nodes
    - ClassVariable, LocalVariable, GlobalVariable nodes
    - CONTAINS, DEFINES, EXTENDS, CALLS relations
    - Import tracking for cross-file dependency resolution
    """
    
    def __init__(self):
        super().__init__("python")
        # Context tracking during parsing
        self.current_file: str = ""
        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None
        # Import tracking: maps alias -> full module path
        self.imports: Dict[str, str] = {}
    
    def parse_file(self, file_path: str, build_index: bool = False) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """
        Parse a Python file using ast-grep.
        
        Matches ASTParser behavior exactly for compatibility.
        """
        print(f"Parsing file: {file_path}")
        self.current_file = file_path
        self.imports = {}
        
        try:
            # Read source code
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            # Parse with ast-grep
            root = SgRoot(source, "python").root()
            
            # Create file node
            file_node_id = self._create_file_node(file_path)
            
            # Generate module name for indexing
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            if build_index:
                if module_name not in self.module_definitions:
                    self.module_definitions[module_name] = {}
                # Associate module name with file node
                self.module_to_file[module_name] = file_node_id
            
            # Extract all top-level entities
            self._parse_imports(root)
            self._parse_classes(root, build_index, module_name)
            self._parse_top_level_functions(root, build_index, module_name)
            self._parse_global_variables(root, file_node_id)
            
            return self.nodes, self.relations
            
        except Exception as e:
            print(f"Error parsing file {file_path}: {e}")
            return {}, []
    
    def _parse_imports(self, root: SgNode) -> None:
        """Extract import statements (import and from...import)."""
        file_node_id = f"file:{self.current_file}"
        
        # Handle "import module" statements
        for import_node in root.find_all(kind="import_statement"):
            # import_statement contains dotted_name or aliased_import
            for child in import_node.children():
                if child.kind() == "dotted_name":
                    # Simple import: import module
                    import_name = child.text()
                    self.imports[import_name] = import_name
                    
                    root_module = import_name.split('.')[0]
                    self.pending_imports.append({
                        "type": "IMPORTS_MODULE",
                        "source_id": file_node_id,
                        "imported_module": root_module,
                        "full_module_path": import_name,
                        "alias": import_name
                    })
                    
                elif child.kind() == "aliased_import":
                    # Aliased import: import module as alias
                    name_node = child.field("name")
                    alias_node = child.field("alias")
                    if name_node and alias_node:
                        import_name = name_node.text()
                        alias_name = alias_node.text()
                        self.imports[alias_name] = import_name
                        
                        root_module = import_name.split('.')[0]
                        self.pending_imports.append({
                            "type": "IMPORTS_MODULE",
                            "source_id": file_node_id,
                            "imported_module": root_module,
                            "full_module_path": import_name,
                            "alias": alias_name
                        })
        
        # Handle "from module import symbol" statements
        for import_from in root.find_all(kind="import_from_statement"):
            module_name_node = import_from.field("module_name")
            module_name = module_name_node.text() if module_name_node else None
            
            # Find imported names (can be dotted_name, aliased_import, or wildcard_import)
            for child in import_from.children():
                if child.kind() == "dotted_name":
                    # from module import symbol
                    symbol_name = child.text()
                    if module_name:
                        full_name = f"{module_name}.{symbol_name}"
                        self.imports[symbol_name] = full_name
                    else:
                        self.imports[symbol_name] = symbol_name
                    
                    self.pending_imports.append({
                        "type": "IMPORTS_SYMBOL",
                        "source_id": file_node_id,
                        "imported_module": module_name,
                        "imported_name": symbol_name,
                        "alias": symbol_name
                    })
                    
                elif child.kind() == "aliased_import":
                    # from module import symbol as alias
                    name_node = child.field("name")
                    alias_node = child.field("alias")
                    if name_node and alias_node:
                        symbol_name = name_node.text()
                        alias_name = alias_node.text()
                        if module_name:
                            full_name = f"{module_name}.{symbol_name}"
                            self.imports[alias_name] = full_name
                        else:
                            self.imports[alias_name] = symbol_name
                        
                        self.pending_imports.append({
                            "type": "IMPORTS_SYMBOL",
                            "source_id": file_node_id,
                            "imported_module": module_name,
                            "imported_name": symbol_name,
                            "alias": alias_name
                        })
    
    def _parse_classes(self, root: SgNode, build_index: bool, module_name: str) -> None:
        """Extract all class definitions."""
        for class_node in root.find_all(kind="class_definition"):
            # Only process top-level classes (not nested classes)
            # Check if parent is module (root)
            parent = class_node.parent()
            if parent and parent.kind() != "module":
                continue
            
            self._parse_class(class_node, build_index, module_name)
    
    def _parse_class(self, class_node: SgNode, build_index: bool, module_name: str) -> str:
        """Parse a class definition node."""
        # Get class name
        name_node = class_node.field("name")
        if not name_node:
            return ""
        
        class_name = name_node.text()
        line_no = class_node.range().start.line + 1  # ast-grep uses 0-indexed lines
        end_line_no = class_node.range().end.line + 1
        
        # Create class node ID
        node_id = self._get_node_id("Class", class_name, self.current_file, line_no)
        
        # Create class node
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="Class",
            name=class_name,
            file_path=self.current_file,
            line_no=line_no,
            end_line_no=end_line_no,
        )
        
        # Create file CONTAINS class relation
        file_node_id = f"file:{self.current_file}"
        self.relations.append(
            CodeRelation(
                source_id=file_node_id,
                target_id=node_id,
                relation_type="CONTAINS",
            )
        )
        
        # Index the class for cross-file resolution
        if build_index and module_name:
            self.module_definitions[module_name][class_name] = node_id
        
        # Handle inheritance (base classes)
        superclasses = class_node.field("superclasses")
        if superclasses:
            for child in superclasses.children():
                if child.kind() == "identifier":
                    base_name = child.text()
                    
                    if base_name in self.imports:
                        # Imported base class - add to pending for second pass
                        imported_class = self.imports[base_name]
                        self.pending_imports.append({
                            "type": "EXTENDS",
                            "source_id": node_id,
                            "imported_module": imported_class.split(".")[0] if "." in imported_class else imported_class,
                            "imported_name": imported_class.split(".")[-1] if "." in imported_class else imported_class,
                            "original_name": base_name
                        })
                    else:
                        # Local base class
                        self.relations.append(
                            CodeRelation(
                                source_id=node_id,
                                target_id=f"Class:{self.current_file}:{base_name}:0",
                                relation_type="EXTENDS",
                            )
                        )
        
        # Parse class body (methods and attributes)
        prev_class = self.current_class
        self.current_class = node_id
        
        body = class_node.field("body")
        if body:
            # Find methods and class attributes
            for child in body.children():
                if child.kind() == "function_definition":
                    self._parse_method(child)
                elif child.kind() == "decorated_definition":
                    # Decorated methods (@staticmethod, @classmethod, etc.)
                    definition = child.field("definition")
                    if definition and definition.kind() == "function_definition":
                        self._parse_method(definition)
                elif child.kind() == "expression_statement":
                    # May contain assignments (class attributes)
                    for expr_child in child.children():
                        if expr_child.kind() == "assignment":
                            self._parse_class_attribute(expr_child)
        
        self.current_class = prev_class
        return node_id
    
    def _parse_method(self, method_node: SgNode) -> None:
        """Parse a method definition inside a class."""
        name_node = method_node.field("name")
        if not name_node:
            return
        
        method_name = name_node.text()
        line_no = method_node.range().start.line + 1
        end_line_no = method_node.range().end.line + 1
        
        node_id = self._get_node_id("Method", method_name, self.current_file, line_no)
        
        # Create method node
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="Method",
            name=method_name,
            file_path=self.current_file,
            line_no=line_no,
            end_line_no=end_line_no,
            properties={"is_method": True},
        )
        
        # Create class DEFINES method relation
        if self.current_class:
            self.relations.append(
                CodeRelation(
                    source_id=self.current_class,
                    target_id=node_id,
                    relation_type="DEFINES",
                )
            )
        
        # Parse method arguments
        self._parse_function_args(method_node, node_id)
        
        # Parse method body for calls
        prev_function = self.current_function
        self.current_function = node_id
        
        body = method_node.field("body")
        if body:
            self._find_function_calls(body)
        
        self.current_function = prev_function
    
    def _parse_top_level_functions(self, root: SgNode, build_index: bool, module_name: str) -> None:
        """Extract top-level function definitions."""
        for func_node in root.find_all(kind="function_definition"):
            # Only process top-level functions (not methods or nested functions)
            parent = func_node.parent()
            if parent and parent.kind() != "module":
                # Check if it's a decorated definition at module level
                if parent.kind() == "decorated_definition":
                    grandparent = parent.parent()
                    if grandparent and grandparent.kind() == "module":
                        # This is a top-level decorated function
                        self._parse_function(func_node, build_index, module_name)
                continue
            
            self._parse_function(func_node, build_index, module_name)
    
    def _parse_function(self, func_node: SgNode, build_index: bool, module_name: str) -> str:
        """Parse a top-level function definition."""
        name_node = func_node.field("name")
        if not name_node:
            return ""
        
        func_name = name_node.text()
        line_no = func_node.range().start.line + 1
        end_line_no = func_node.range().end.line + 1
        
        node_id = self._get_node_id("Function", func_name, self.current_file, line_no)
        
        # Create function node
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="Function",
            name=func_name,
            file_path=self.current_file,
            line_no=line_no,
            end_line_no=end_line_no,
            properties={"is_method": False},
        )
        
        # Create file CONTAINS function relation
        file_node_id = f"file:{self.current_file}"
        self.relations.append(
            CodeRelation(
                source_id=file_node_id,
                target_id=node_id,
                relation_type="CONTAINS",
            )
        )
        
        # Index function for cross-file resolution
        if build_index and module_name:
            self.module_definitions[module_name][func_name] = node_id
        
        # Parse function arguments
        self._parse_function_args(func_node, node_id)
        
        # Parse function body for calls
        prev_function = self.current_function
        self.current_function = node_id
        
        body = func_node.field("body")
        if body:
            self._find_function_calls(body)
        
        self.current_function = prev_function
        return node_id
    
    def _parse_function_args(self, func_node: SgNode, node_id: str) -> None:
        """Extract function/method parameters."""
        params_node = func_node.field("parameters")
        if not params_node:
            return
        
        args = []
        for child in params_node.children():
            if child.kind() == "identifier":
                # Simple parameter
                arg_info = {"name": child.text()}
                args.append(arg_info)
            elif child.kind() == "typed_parameter":
                # Typed parameter: name: type
                name_field = child.field("name") or child.child(0)
                type_field = child.field("type")
                if name_field:
                    arg_info = {"name": name_field.text()}
                    if type_field:
                        arg_info["type"] = type_field.text()
                    args.append(arg_info)
            elif child.kind() == "default_parameter":
                # Parameter with default value
                name_field = child.field("name") or child.child(0)
                if name_field:
                    arg_info = {"name": name_field.text(), "has_default": True}
                    args.append(arg_info)
        
        # Store args as JSON string (matching ASTParser behavior)
        if args:
            self.nodes[node_id].properties["args"] = json.dumps(args)
    
    def _parse_global_variables(self, root: SgNode, file_node_id: str) -> None:
        """Extract global-level variable assignments."""
        # Find all assignments at module level (including in if __name__ == "__main__" blocks)
        for assign_node in root.find_all(kind="assignment"):
            # Check if this assignment is at global scope (not inside a function or class)
            parent = assign_node.parent()
            while parent:
                parent_kind = parent.kind()
                # Skip if inside a function or class definition
                if parent_kind in ["function_definition", "class_definition"]:
                    break
                # If we reach module level, it's a global variable
                if parent_kind == "module":
                    self._parse_assignment(assign_node, file_node_id, is_global=True)
                    break
                parent = parent.parent()
    
    def _parse_assignment(self, assign_node: SgNode, file_node_id: str, is_global: bool = False) -> None:
        """Parse an assignment to extract variable nodes."""
        # Get left-hand side (target)
        left = assign_node.field("left")
        if not left:
            return
        
        # Extract variable name(s)
        var_names = []
        if left.kind() == "identifier":
            var_names.append(left.text())
        elif left.kind() == "pattern_list":
            # Multiple assignment: a, b = ...
            for child in left.children():
                if child.kind() == "identifier":
                    var_names.append(child.text())
        
        line_no = assign_node.range().start.line + 1
        end_line_no = assign_node.range().end.line + 1
        
        for var_name in var_names:
            if self.current_class and not self.current_function:
                # Class attribute
                node_id = self._get_node_id("ClassVariable", var_name, self.current_file, line_no)
                self.nodes[node_id] = CodeNode(
                    node_id=node_id,
                    node_type="ClassVariable",
                    name=var_name,
                    file_path=self.current_file,
                    line_no=line_no,
                    end_line_no=end_line_no,
                )
                self.relations.append(
                    CodeRelation(
                        source_id=self.current_class,
                        target_id=node_id,
                        relation_type="DEFINES",
                    )
                )
            elif self.current_function:
                # Local variable
                node_id = self._get_node_id("LocalVariable", var_name, self.current_file, line_no)
                self.nodes[node_id] = CodeNode(
                    node_id=node_id,
                    node_type="LocalVariable",
                    name=var_name,
                    file_path=self.current_file,
                    line_no=line_no,
                    end_line_no=end_line_no,
                )
                self.relations.append(
                    CodeRelation(
                        source_id=self.current_function,
                        target_id=node_id,
                        relation_type="DEFINES",
                    )
                )
            elif is_global:
                # Global variable (use "Variable" prefix for ID to match legacy parser)
                node_id = self._get_node_id("Variable", var_name, self.current_file, line_no)
                self.nodes[node_id] = CodeNode(
                    node_id=node_id,
                    node_type="GlobalVariable",
                    name=var_name,
                    file_path=self.current_file,
                    line_no=line_no,
                    end_line_no=end_line_no,
                )
                self.relations.append(
                    CodeRelation(
                        source_id=file_node_id,
                        target_id=node_id,
                        relation_type="DEFINES",
                    )
                )
    
    def _parse_class_attribute(self, assign_node: SgNode) -> None:
        """Parse class-level attribute assignments."""
        left = assign_node.field("left")
        if not left or left.kind() != "identifier":
            return
        
        var_name = left.text()
        line_no = assign_node.range().start.line + 1
        end_line_no = assign_node.range().end.line + 1
        
        node_id = self._get_node_id("ClassVariable", var_name, self.current_file, line_no)
        
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="ClassVariable",
            name=var_name,
            file_path=self.current_file,
            line_no=line_no,
            end_line_no=end_line_no,
        )
        
        if self.current_class:
            self.relations.append(
                CodeRelation(
                    source_id=self.current_class,
                    target_id=node_id,
                    relation_type="DEFINES",
                )
            )
    
    def _find_function_calls(self, node: SgNode) -> None:
        """Recursively find all function/method calls in a node."""
        # Find all call expressions in this subtree
        for call_node in node.find_all(kind="call"):
            self._process_call(call_node)
    
    def _process_call(self, call_node: SgNode) -> None:
        """Process a single call node."""
        if not self.current_function:
            return
        
        func_node = call_node.field("function")
        if not func_node:
            return
        
        if func_node.kind() == "identifier":
            # Direct function call: func()
            func_name = func_node.text()
            
            if func_name in self.imports:
                # Call to imported function
                imported_func = self.imports[func_name]
                self.pending_imports.append({
                    "type": "CALLS",
                    "source_id": self.current_function,
                    "imported_module": imported_func.split(".")[0] if "." in imported_func else imported_func,
                    "imported_name": imported_func.split(".")[-1] if "." in imported_func else imported_func,
                    "original_name": func_name
                })
            else:
                # Call to local function
                self.relations.append(
                    CodeRelation(
                        source_id=self.current_function,
                        target_id=f"Function:{self.current_file}:{func_name}:0",
                        relation_type="CALLS",
                    )
                )
        
        elif func_node.kind() == "attribute":
            # Method call: obj.method()
            object_node = func_node.field("object")
            attr_node = func_node.field("attribute")
            
            if object_node and attr_node and object_node.kind() == "identifier":
                obj_name = object_node.text()
                method_name = attr_node.text()
                
                if obj_name in self.imports:
                    # Method call on imported class/module
                    imported_obj = self.imports[obj_name]
                    self.pending_imports.append({
                        "type": "CALLS_METHOD",
                        "source_id": self.current_function,
                        "imported_module": imported_obj.split(".")[0] if "." in imported_obj else imported_obj,
                        "imported_class": imported_obj.split(".")[-1] if "." in imported_obj else imported_obj,
                        "method_name": method_name,
                        "original_obj_name": obj_name
                    })
                else:
                    # Method call on local object
                    self.relations.append(
                        CodeRelation(
                            source_id=self.current_function,
                            target_id=f"Method:{self.current_file}:{method_name}:0",
                            relation_type="CALLS",
                            properties={"object": obj_name},
                        )
                    )
