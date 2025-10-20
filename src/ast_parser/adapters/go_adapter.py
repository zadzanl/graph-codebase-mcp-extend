"""Go language adapter using ast-grep for AST parsing."""

import os
from typing import Dict, List, Tuple, Optional

from ast_grep_py import SgRoot, SgNode

from .base_adapter import LanguageAdapter
from ast_parser.parser import CodeNode, CodeRelation


class GoAdapter(LanguageAdapter):
    """
    Go adapter using ast-grep library.
    
    Extracts minimal Go structures for proof of concept:
    - File, Struct, Function, Method nodes
    - CONTAINS, DEFINES relations
    - Import tracking (import declarations)
    
    Supports Go source files (.go).
    """
    
    def __init__(self):
        super().__init__("go")
        self.current_file: str = ""
    
    def parse_file(self, file_path: str, build_index: bool = False) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """
        Parse a Go file using ast-grep.
        
        Extracts type declarations (structs), functions, methods, and imports.
        """
        self.current_file = file_path
        
        try:
            # Read source code
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            # Parse with ast-grep (Go language)
            root = SgRoot(source, "go").root()
            
            # Create file node
            file_node_id = self._create_file_node(file_path)
            
            # Generate module name for indexing
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            if build_index:
                if module_name not in self.module_definitions:
                    self.module_definitions[module_name] = {}
                self.module_to_file[module_name] = file_node_id
            
            # Extract Go structures
            self._parse_imports(root, file_node_id)
            self._parse_type_declarations(root, file_node_id, build_index, module_name)
            self._parse_functions(root, file_node_id)
            self._parse_methods(root)
            
            return self.nodes, self.relations
            
        except Exception as e:
            print(f"Error parsing Go file {file_path}: {e}")
            return {}, []
    
    def _parse_imports(self, root: SgNode, file_node_id: str) -> None:
        """Extract import declarations."""
        # Find all import_declaration nodes
        for import_node in root.find_all(kind="import_declaration"):
            # Import can have import_spec or import_spec_list
            # Extract all import paths
            for child in import_node.children():
                if child.kind() == "import_spec":
                    # Get the import path (string literal)
                    path_node = child.field("path")
                    if path_node:
                        import_path = path_node.text().strip('"')
                        # Extract last part as module name
                        parts = import_path.split("/")
                        module_name = parts[-1] if parts else import_path
                        
                        self.pending_imports.append({
                            "type": "IMPORTS_MODULE",
                            "source_id": file_node_id,
                            "imported_module": module_name,
                            "full_module_path": import_path,
                        })
                elif child.kind() == "import_spec_list":
                    # Multiple imports in parentheses
                    for spec in child.children():
                        if spec.kind() == "import_spec":
                            path_node = spec.field("path")
                            if path_node:
                                import_path = path_node.text().strip('"')
                                parts = import_path.split("/")
                                module_name = parts[-1] if parts else import_path
                                
                                self.pending_imports.append({
                                    "type": "IMPORTS_MODULE",
                                    "source_id": file_node_id,
                                    "imported_module": module_name,
                                    "full_module_path": import_path,
                                })
    
    def _parse_type_declarations(self, root: SgNode, file_node_id: str, build_index: bool, module_name: str) -> None:
        """Extract type declarations (primarily structs)."""
        # Find all type_declaration nodes
        for type_node in root.find_all(kind="type_declaration"):
            # Type declaration has a type_spec
            type_spec = type_node.field("type_spec")
            if not type_spec:
                # Try to find type_spec in children
                for child in type_node.children():
                    if child.kind() == "type_spec":
                        type_spec = child
                        break
            
            if not type_spec:
                continue
            
            # Get type name
            name_field = type_spec.field("name")
            if not name_field:
                continue
            
            type_name = name_field.text()
            
            # Get the type definition
            type_def = type_spec.field("type")
            if type_def and type_def.kind() == "struct_type":
                # This is a struct declaration
                line_no = type_node.range().start.line + 1
                
                # Create struct node (using "Class" type for consistency)
                struct_node_id = self._get_node_id("Class", type_name, self.current_file, line_no)
                self.nodes[struct_node_id] = CodeNode(
                    node_id=struct_node_id,
                    node_type="Class",
                    name=type_name,
                    file_path=self.current_file,
                    line_no=line_no,
                )
                
                # Add CONTAINS relation from file to struct
                self._add_relation(CodeRelation(file_node_id, struct_node_id, "CONTAINS"))
                
                # Index the struct for cross-file resolution
                if build_index:
                    self.module_definitions[module_name][type_name] = struct_node_id
    
    def _parse_functions(self, root: SgNode, file_node_id: str) -> None:
        """Extract top-level function declarations."""
        # Find all function_declaration nodes
        for func_node in root.find_all(kind="function_declaration"):
            # Get function name
            name_field = func_node.field("name")
            if not name_field:
                continue
            
            func_name = name_field.text()
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
    
    def _parse_methods(self, root: SgNode) -> None:
        """Extract method declarations (functions with receivers)."""
        # Find all method_declaration nodes
        for method_node in root.find_all(kind="method_declaration"):
            # Get method name
            name_field = method_node.field("name")
            if not name_field:
                continue
            
            method_name = name_field.text()
            line_no = method_node.range().start.line + 1
            
            # Get receiver type
            receiver = method_node.field("receiver")
            if not receiver:
                continue
            
            # Extract receiver type name
            receiver_type = self._extract_receiver_type(receiver)
            if not receiver_type:
                continue
            
            # Find the corresponding struct node
            struct_node_id = None
            for node_id, node in self.nodes.items():
                if node.node_type == "Class" and node.name == receiver_type:
                    struct_node_id = node_id
                    break
            
            # If struct not found, skip (might be external type or pointer receiver)
            if not struct_node_id:
                continue
            
            # Create method node
            method_node_id = self._get_node_id("Method", method_name, self.current_file, line_no)
            self.nodes[method_node_id] = CodeNode(
                node_id=method_node_id,
                node_type="Method",
                name=method_name,
                file_path=self.current_file,
                line_no=line_no,
            )
            
            # Add DEFINES relation from struct to method
            self._add_relation(CodeRelation(struct_node_id, method_node_id, "DEFINES"))
    
    def _extract_receiver_type(self, receiver: SgNode) -> Optional[str]:
        """
        Extract the receiver type name from a method receiver.
        
        Receivers can be (Type) or (*Type).
        """
        # Look for parameter_declaration in receiver
        for child in receiver.children():
            if child.kind() == "parameter_declaration":
                # Get the type
                type_node = child.field("type")
                if type_node:
                    # Handle pointer types
                    if type_node.kind() == "pointer_type":
                        # Get the pointee type
                        for type_child in type_node.children():
                            if type_child.kind() == "type_identifier":
                                return type_child.text()
                    elif type_node.kind() == "type_identifier":
                        return type_node.text()
        
        return None
