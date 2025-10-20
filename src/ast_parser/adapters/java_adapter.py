"""Java language adapter using ast-grep for AST parsing."""

import os
from typing import Dict, List, Tuple, Optional

from ast_grep_py import SgRoot, SgNode

from .base_adapter import LanguageAdapter
from ast_parser.parser import CodeNode, CodeRelation


class JavaAdapter(LanguageAdapter):
    """
    Java adapter using ast-grep library.
    
    Extracts minimal Java structures for proof of concept:
    - File, Class, Method nodes
    - Field (Variable) nodes
    - CONTAINS, DEFINES relations
    - Import tracking for cross-file dependency resolution
    
    Supports Java source files (.java).
    """
    
    def __init__(self):
        super().__init__("java")
        self.current_file: str = ""
        self.current_class: Optional[str] = None
    
    def parse_file(self, file_path: str, build_index: bool = False) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """
        Parse a Java file using ast-grep.
        
        Extracts classes, methods, fields, and imports.
        """
        self.current_file = file_path
        self.current_class = None
        
        try:
            # Read source code
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            # Parse with ast-grep (Java language)
            root = SgRoot(source, "java").root()
            
            # Create file node
            file_node_id = self._create_file_node(file_path)
            
            # Generate module name for indexing
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            if build_index:
                if module_name not in self.module_definitions:
                    self.module_definitions[module_name] = {}
                self.module_to_file[module_name] = file_node_id
            
            # Extract Java structures
            self._parse_imports(root, file_node_id)
            self._parse_classes(root, file_node_id, build_index, module_name)
            
            return self.nodes, self.relations
            
        except Exception as e:
            print(f"Error parsing Java file {file_path}: {e}")
            return {}, []
    
    def _parse_imports(self, root: SgNode, file_node_id: str) -> None:
        """Extract import declarations."""
        # Find all import_declaration nodes
        for import_node in root.find_all(kind="import_declaration"):
            # Get the imported name (could be wildcard import or specific class)
            # import_declaration contains either scoped_identifier or identifier
            import_text = import_node.text().strip()
            if import_text.startswith("import "):
                import_text = import_text[7:].strip()
                if import_text.endswith(";"):
                    import_text = import_text[:-1].strip()
                
                # Extract module for tracking
                parts = import_text.split(".")
                if len(parts) > 0:
                    root_module = parts[0]
                    self.pending_imports.append({
                        "type": "IMPORTS_MODULE",
                        "source_id": file_node_id,
                        "imported_module": root_module,
                        "full_module_path": import_text,
                    })
    
    def _parse_classes(self, root: SgNode, file_node_id: str, build_index: bool, module_name: str) -> None:
        """Extract class declarations and their methods/fields."""
        # Find all class_declaration nodes
        for class_node in root.find_all(kind="class_declaration"):
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
            
            # Extract methods and fields from class body
            body = class_node.field("body")
            if body:
                self._parse_methods(body, class_node_id)
                self._parse_fields(body, class_node_id)
            
            # Reset context
            self.current_class = None
    
    def _parse_methods(self, class_body: SgNode, class_node_id: str) -> None:
        """Extract method declarations from class body."""
        # Find all method_declaration nodes within class body
        for method_node in class_body.find_all(kind="method_declaration"):
            # Get method name
            name_field = method_node.field("name")
            if not name_field:
                continue
            
            method_name = name_field.text()
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
    
    def _parse_fields(self, class_body: SgNode, class_node_id: str) -> None:
        """Extract field declarations (class variables) from class body."""
        # Find all field_declaration nodes within class body
        for field_node in class_body.find_all(kind="field_declaration"):
            # Field declarations can have multiple declarators
            # field_declaration has a "declarator" field (can be multiple)
            for child in field_node.children():
                if child.kind() == "variable_declarator":
                    # Get variable name
                    name_field = child.field("name")
                    if name_field:
                        var_name = name_field.text()
                        line_no = child.range().start.line + 1
                        
                        # Create variable node (class field)
                        var_node_id = self._get_node_id("Variable", var_name, self.current_file, line_no)
                        self.nodes[var_node_id] = CodeNode(
                            node_id=var_node_id,
                            node_type="ClassVariable",
                            name=var_name,
                            file_path=self.current_file,
                            line_no=line_no,
                        )
                        
                        # Add DEFINES relation from class to field
                        self._add_relation(CodeRelation(class_node_id, var_node_id, "DEFINES"))
