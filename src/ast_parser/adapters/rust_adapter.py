"""Rust language adapter using ast-grep for AST parsing."""

import os
from typing import Dict, List, Tuple, Optional

from ast_grep_py import SgRoot, SgNode

from .base_adapter import LanguageAdapter
from ast_parser.parser import CodeNode, CodeRelation


class RustAdapter(LanguageAdapter):
    """
    Rust adapter using ast-grep library.
    
    Extracts minimal Rust structures for proof of concept:
    - File, Struct, Function, Method nodes
    - CONTAINS, DEFINES relations
    - Use declaration tracking (imports)
    
    Supports Rust source files (.rs).
    """
    
    def __init__(self):
        super().__init__("rust")
        self.current_file: str = ""
        self.current_struct: Optional[str] = None
    
    def parse_file(self, file_path: str, build_index: bool = False) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """
        Parse a Rust file using ast-grep.
        
        Extracts structs, functions, impl blocks, and use declarations.
        """
        self.current_file = file_path
        self.current_struct = None
        
        try:
            # Read source code
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            # Parse with ast-grep (Rust language)
            root = SgRoot(source, "rust").root()
            
            # Create file node
            file_node_id = self._create_file_node(file_path)
            
            # Generate module name for indexing
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            if build_index:
                if module_name not in self.module_definitions:
                    self.module_definitions[module_name] = {}
                self.module_to_file[module_name] = file_node_id
            
            # Extract Rust structures
            self._parse_use_declarations(root, file_node_id)
            self._parse_structs(root, file_node_id, build_index, module_name)
            self._parse_functions(root, file_node_id)
            self._parse_impl_blocks(root, build_index, module_name)
            
            return self.nodes, self.relations
            
        except Exception as e:
            print(f"Error parsing Rust file {file_path}: {e}")
            return {}, []
    
    def _parse_use_declarations(self, root: SgNode, file_node_id: str) -> None:
        """Extract use declarations (imports)."""
        # Find all use_declaration nodes
        for use_node in root.find_all(kind="use_declaration"):
            # Get the use path
            use_text = use_node.text().strip()
            if use_text.startswith("use "):
                use_text = use_text[4:].strip()
                if use_text.endswith(";"):
                    use_text = use_text[:-1].strip()
                
                # Extract root module
                parts = use_text.split("::")
                if len(parts) > 0:
                    root_module = parts[0]
                    self.pending_imports.append({
                        "type": "IMPORTS_MODULE",
                        "source_id": file_node_id,
                        "imported_module": root_module,
                        "full_module_path": use_text,
                    })
    
    def _parse_structs(self, root: SgNode, file_node_id: str, build_index: bool, module_name: str) -> None:
        """Extract struct declarations."""
        # Find all struct_item nodes
        for struct_node in root.find_all(kind="struct_item"):
            # Get struct name
            name_field = struct_node.field("name")
            if not name_field:
                continue
            
            struct_name = name_field.text()
            line_no = struct_node.range().start.line + 1
            
            # Create struct node (using "Class" type for consistency)
            struct_node_id = self._get_node_id("Class", struct_name, self.current_file, line_no)
            self.nodes[struct_node_id] = CodeNode(
                node_id=struct_node_id,
                node_type="Class",
                name=struct_name,
                file_path=self.current_file,
                line_no=line_no,
            )
            
            # Add CONTAINS relation from file to struct
            self._add_relation(CodeRelation(file_node_id, struct_node_id, "CONTAINS"))
            
            # Index the struct for cross-file resolution
            if build_index:
                self.module_definitions[module_name][struct_name] = struct_node_id
    
    def _parse_functions(self, root: SgNode, file_node_id: str) -> None:
        """Extract top-level function declarations."""
        # Find all function_item nodes at top level (not in impl blocks)
        for func_node in root.children():
            if func_node.kind() == "function_item":
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
    
    def _parse_impl_blocks(self, root: SgNode, build_index: bool, module_name: str) -> None:
        """Extract impl blocks and their methods."""
        # Find all impl_item nodes
        for impl_node in root.find_all(kind="impl_item"):
            # Get the type this impl is for
            type_field = impl_node.field("type")
            if not type_field:
                continue
            
            type_name = type_field.text()
            
            # Find the corresponding struct node
            struct_node_id = None
            for node_id, node in self.nodes.items():
                if node.node_type == "Class" and node.name == type_name:
                    struct_node_id = node_id
                    break
            
            # If struct not found, skip (might be external type)
            if not struct_node_id:
                continue
            
            # Extract methods from impl block body
            body = impl_node.field("body")
            if body:
                for child in body.children():
                    if child.kind() == "function_item":
                        # Get method name
                        name_field = child.field("name")
                        if not name_field:
                            continue
                        
                        method_name = name_field.text()
                        line_no = child.range().start.line + 1
                        
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
