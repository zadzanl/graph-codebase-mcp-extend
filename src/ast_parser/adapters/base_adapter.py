"""Base adapter interface for multi-language AST parsing using ast-grep."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple, Set
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ast_parser.parser import CodeNode, CodeRelation


class LanguageAdapter(ABC):
    """
    Abstract base class for language-specific AST adapters.
    
    Each adapter uses ast-grep to parse source code and extract:
    - CodeNodes (classes, functions, variables, etc.)
    - CodeRelations (CONTAINS, DEFINES, EXTENDS, CALLS, etc.)
    
    Adapters maintain indices for cross-file dependency resolution:
    - module_definitions: maps module names to their exported symbols
    - pending_imports: tracks imports to be resolved in second pass
    - module_to_file: maps module names to file node IDs
    - established_relations: prevents duplicate relations
    """
    
    def __init__(self, language: str):
        self.language = language
        # Core data structures
        self.nodes: Dict[str, CodeNode] = {}
        self.relations: List[CodeRelation] = []
        
        # Indices for cross-file resolution (two-pass parsing)
        self.module_definitions: Dict[str, Dict[str, str]] = {}
        self.pending_imports: List[Dict[str, Any]] = []
        self.module_to_file: Dict[str, str] = {}
        self.established_relations: Set[str] = set()
    
    @abstractmethod
    def parse_file(self, file_path: str, build_index: bool = False) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """
        Parse a single source file and extract nodes and relations.
        
        Args:
            file_path: Absolute path to the source file
            build_index: If True, populate module_definitions for cross-file resolution
        
        Returns:
            Tuple of (nodes dict, relations list)
        """
        pass
    
    def _get_node_id(self, node_type: str, name: str, file_path: str, line_no: int) -> str:
        """
        Generate unique node ID matching legacy parser format.
        
        Format: "{node_type}:{file_path}:{name}:{line_no}"
        This ensures compatibility with existing code and tests.
        """
        return f"{node_type}:{file_path}:{name}:{line_no}"
    
    def _create_file_node(self, file_path: str) -> str:
        """
        Create a file node for the given path.
        
        Returns the file node ID.
        """
        import os
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
    
    def _add_relation(self, relation: CodeRelation) -> None:
        """
        Add a relation, preventing duplicates.
        
        Creates a unique key based on source, type, target, and relevant properties.
        """
        # Create unique relation key
        relation_key = f"{relation.source_id}|{relation.relation_type}|{relation.target_id}"
        
        # For certain relation types, include properties in the key
        if relation.relation_type == "IMPORTS_FROM":
            # File-to-module import: one relation per file-module pair
            relation_key = f"{relation.source_id}|{relation.relation_type}|{relation.target_id}"
        elif relation.relation_type == "IMPORTS_DEFINITION":
            # Symbol import: include symbol name in key
            symbol = relation.properties.get("symbol", "")
            relation_key = f"{relation.source_id}|{relation.relation_type}|{relation.target_id}|{symbol}"
        
        # Only add if not already present
        if relation_key not in self.established_relations:
            self.relations.append(relation)
            self.established_relations.add(relation_key)
