"""C++ language adapter using ast-grep for AST parsing."""

import os
from typing import Dict, List, Tuple, Optional

from ast_grep_py import SgRoot, SgNode

from .base_adapter import LanguageAdapter
from ast_parser.parser import CodeNode, CodeRelation


class CppAdapter(LanguageAdapter):
    """
    C++ adapter using ast-grep library.
    
    Extracts minimal C++ structures for proof of concept:
    - File, Class, Function nodes
    - Field (Variable) nodes
    - CONTAINS, DEFINES relations
    - Include tracking (#include directives)
    
    Supports C++ source files (.cpp, .cc, .cxx, .hpp, .h).
    """
    
    def __init__(self):
        super().__init__("cpp")
        self.current_file: str = ""
        self.current_class: Optional[str] = None
    
    def parse_file(self, file_path: str, build_index: bool = False) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """
        Parse a C++ file using ast-grep.
        
        Extracts classes, functions, fields, and includes.
        """
        self.current_file = file_path
        self.current_class = None
        
        try:
            # Read source code
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            # Parse with ast-grep (C++ language)
            root = SgRoot(source, "cpp").root()
            
            # Create file node
            file_node_id = self._create_file_node(file_path)
            
            # Generate module name for indexing
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            if build_index:
                if module_name not in self.module_definitions:
                    self.module_definitions[module_name] = {}
                self.module_to_file[module_name] = file_node_id
            
            # Extract C++ structures
            self._parse_includes(root, file_node_id)
            self._parse_classes(root, file_node_id, build_index, module_name)
            self._parse_functions(root, file_node_id)
            
            return self.nodes, self.relations
            
        except Exception as e:
            print(f"Error parsing C++ file {file_path}: {e}")
            return {}, []
    
    def _parse_includes(self, root: SgNode, file_node_id: str) -> None:
        """Extract #include directives."""
        # Find all preproc_include nodes
        for include_node in root.find_all(kind="preproc_include"):
            # Get the included file path
            include_text = include_node.text().strip()
            if include_text.startswith("#include"):
                include_text = include_text[8:].strip()
                # Remove quotes or angle brackets
                include_text = include_text.strip('<>"')
                
                # Extract module name (filename without extension)
                if "/" in include_text:
                    include_text = include_text.split("/")[-1]
                module_name = os.path.splitext(include_text)[0]
                
                self.pending_imports.append({
                    "type": "IMPORTS_MODULE",
                    "source_id": file_node_id,
                    "imported_module": module_name,
                    "full_module_path": include_text,
                })
    
    def _parse_classes(self, root: SgNode, file_node_id: str, build_index: bool, module_name: str) -> None:
        """Extract class declarations and their methods/fields."""
        # Find all class_specifier nodes (class or struct)
        for class_node in root.find_all(kind="class_specifier"):
            # Get class name from field
            name_field = class_node.field("name")
            if not name_field:
                continue
            
            class_name = name_field.text()
            line_no = class_node.range().start.line + 1
            
            # Create class node
            class_node_id = self._get_node_id("Class", class_name, self.current_file, line_no)
            self.nodes[class_node_id] = CodeNode(
                node_id=class_node_id,
                node_type="Class",
                name=class_name,
                file_path=self.current_file,
                line_no=line_no,
            )
            
            # Add CONTAINS relation from file to class
            self._add_relation(CodeRelation(file_node_id, class_node_id, "CONTAINS"))
            
            # Index the class for cross-file resolution
            if build_index:
                self.module_definitions[module_name][class_name] = class_node_id
            
            # Set current class context
            self.current_class = class_node_id
            
            # Extract methods from class body
            body = class_node.field("body")
            if body:
                self._parse_class_methods(body, class_node_id)
            
            # Reset context
            self.current_class = None
    
    def _parse_class_methods(self, class_body: SgNode, class_node_id: str) -> None:
        """Extract method definitions from class body."""
        # Find all function_definition nodes within class body
        for method_node in class_body.find_all(kind="function_definition"):
            # Extract function name from declarator
            declarator = method_node.field("declarator")
            if not declarator:
                continue
            
            # Function name can be in different declarator types
            method_name = self._extract_function_name(declarator)
            if not method_name:
                continue
            
            line_no = method_node.range().start.line + 1
            
            # Create method node
            method_node_id = self._get_node_id("Method", method_name, self.current_file, line_no)
            self.nodes[method_node_id] = CodeNode(
                node_id=method_node_id,
                node_type="Method",
                name=method_name,
                file_path=self.current_file,
                line_no=line_no,
            )
            
            # Add DEFINES relation from class to method
            self._add_relation(CodeRelation(class_node_id, method_node_id, "DEFINES"))
    
    def _parse_functions(self, root: SgNode, file_node_id: str) -> None:
        """Extract top-level function definitions."""
        # Find all function_definition nodes at top level
        for func_node in root.children():
            if func_node.kind() == "function_definition":
                # Extract function name from declarator
                declarator = func_node.field("declarator")
                if not declarator:
                    continue
                
                func_name = self._extract_function_name(declarator)
                if not func_name:
                    continue
                
                line_no = func_node.range().start.line + 1
                
                # Create function node
                func_node_id = self._get_node_id("Function", func_name, self.current_file, line_no)
                self.nodes[func_node_id] = CodeNode(
                    node_id=func_node_id,
                    node_type="Function",
                    name=func_name,
                    file_path=self.current_file,
                    line_no=line_no,
                )
                
                # Add CONTAINS relation from file to function
                self._add_relation(CodeRelation(file_node_id, func_node_id, "CONTAINS"))
    
    def _extract_function_name(self, declarator: SgNode) -> Optional[str]:
        """
        Extract function name from a declarator node.
        
        C++ declarators can be complex (pointers, references, function pointers).
        We try to find the identifier that represents the function name.
        """
        # Try direct field access first
        name_field = declarator.field("declarator")
        if name_field and name_field.kind() == "identifier":
            return name_field.text()
        
        # Look for identifier in children
        for child in declarator.children():
            if child.kind() == "identifier":
                return child.text()
            # Recursively check nested declarators
            if "declarator" in child.kind():
                name = self._extract_function_name(child)
                if name:
                    return name
        
        return None
