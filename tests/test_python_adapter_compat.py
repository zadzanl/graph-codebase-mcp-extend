"""
Phase 4: Python Parity Regression Tests

This test suite ensures 100% parity between the legacy ASTParser
and the new PythonAstGrepAdapter for Python code parsing.

Tests verify that both parsers produce:
- Identical node IDs and counts
- Identical relation types and counts
- Identical graph structure

This is critical for backward compatibility and ensures no regressions
when transitioning to the ast-grep based parsing system.
"""

import os
import sys
import pytest
from collections import Counter
from typing import Dict, List, Tuple, Set

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ast_parser.parser import ASTParser, CodeNode, CodeRelation
from src.ast_parser.adapters.python_adapter import PythonAstGrepAdapter
from src.ast_parser.multi_parser import MultiLanguageParser


class TestPythonAdapterParity:
    """Test suite for Python adapter parity with legacy ASTParser."""
    
    @pytest.fixture
    def example_codebase_path(self):
        """Return path to example_codebase directory."""
        return os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'example_codebase'
        )
    
    @pytest.fixture
    def legacy_results(self, example_codebase_path):
        """Parse example_codebase with legacy ASTParser."""
        parser = ASTParser()
        nodes, relations = parser.parse_directory(example_codebase_path)
        return nodes, relations
    
    @pytest.fixture
    def ast_grep_results(self, example_codebase_path):
        """Parse example_codebase with PythonAstGrepAdapter via MultiLanguageParser."""
        coordinator = MultiLanguageParser(
            use_ast_grep=True,
            ast_grep_languages=['python'],
            ast_grep_fallback=False
        )
        nodes, relations = coordinator.parse_directory(example_codebase_path, build_index=True)
        return nodes, relations
    
    def _get_relation_key(self, rel: CodeRelation) -> Tuple[str, str, str]:
        """Convert relation to comparable tuple."""
        return (rel.source_id, rel.relation_type, rel.target_id)
    
    def _get_node_summary(self, nodes: Dict[str, CodeNode]) -> Dict[str, int]:
        """Get summary statistics of node types."""
        return Counter(node.node_type for node in nodes.values())
    
    def _get_relation_summary(self, relations: List[CodeRelation]) -> Dict[str, int]:
        """Get summary statistics of relation types."""
        return Counter(rel.relation_type for rel in relations)
    
    def test_node_count_parity(self, legacy_results, ast_grep_results):
        """Test that both parsers produce the same number of nodes."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        
        assert len(legacy_nodes) == len(ast_grep_nodes), (
            f"Node count mismatch: legacy={len(legacy_nodes)}, "
            f"ast-grep={len(ast_grep_nodes)}"
        )
    
    def test_node_ids_parity(self, legacy_results, ast_grep_results):
        """Test that both parsers produce identical node IDs."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        
        legacy_ids = set(legacy_nodes.keys())
        ast_grep_ids = set(ast_grep_nodes.keys())
        
        # Check for missing nodes in ast-grep
        missing_in_ast_grep = legacy_ids - ast_grep_ids
        if missing_in_ast_grep:
            print("\nNodes in legacy but missing in ast-grep:")
            for node_id in sorted(missing_in_ast_grep):
                node = legacy_nodes[node_id]
                print(f"  - {node.node_type}: {node.name} at {node.file_path}:{node.line_no}")
        
        # Check for extra nodes in ast-grep
        extra_in_ast_grep = ast_grep_ids - legacy_ids
        if extra_in_ast_grep:
            print("\nNodes in ast-grep but missing in legacy:")
            for node_id in sorted(extra_in_ast_grep):
                node = ast_grep_nodes[node_id]
                print(f"  - {node.node_type}: {node.name} at {node.file_path}:{node.line_no}")
        
        assert legacy_ids == ast_grep_ids, (
            f"Node ID sets differ: "
            f"{len(missing_in_ast_grep)} missing in ast-grep, "
            f"{len(extra_in_ast_grep)} extra in ast-grep"
        )
    
    def test_node_properties_parity(self, legacy_results, ast_grep_results):
        """Test that nodes have identical properties (type, name, path, line)."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        
        mismatches = []
        for node_id in legacy_nodes.keys():
            legacy_node = legacy_nodes[node_id]
            ast_grep_node = ast_grep_nodes.get(node_id)
            
            if not ast_grep_node:
                continue  # Already caught by test_node_ids_parity
            
            # Compare all properties
            if legacy_node.node_type != ast_grep_node.node_type:
                mismatches.append(
                    f"{node_id}: type mismatch "
                    f"(legacy={legacy_node.node_type}, ast-grep={ast_grep_node.node_type})"
                )
            
            if legacy_node.name != ast_grep_node.name:
                mismatches.append(
                    f"{node_id}: name mismatch "
                    f"(legacy={legacy_node.name}, ast-grep={ast_grep_node.name})"
                )
            
            if legacy_node.file_path != ast_grep_node.file_path:
                mismatches.append(
                    f"{node_id}: path mismatch "
                    f"(legacy={legacy_node.file_path}, ast-grep={ast_grep_node.file_path})"
                )
            
            if legacy_node.line_no != ast_grep_node.line_no:
                mismatches.append(
                    f"{node_id}: line mismatch "
                    f"(legacy={legacy_node.line_no}, ast-grep={ast_grep_node.line_no})"
                )
        
        if mismatches:
            print("\nNode property mismatches:")
            for mismatch in mismatches[:10]:  # Show first 10
                print(f"  - {mismatch}")
            if len(mismatches) > 10:
                print(f"  ... and {len(mismatches) - 10} more")
        
        assert not mismatches, f"Found {len(mismatches)} node property mismatches"
    
    def test_node_type_distribution_parity(self, legacy_results, ast_grep_results):
        """Test that both parsers produce the same distribution of node types."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        
        legacy_summary = self._get_node_summary(legacy_nodes)
        ast_grep_summary = self._get_node_summary(ast_grep_nodes)
        
        assert legacy_summary == ast_grep_summary, (
            f"Node type distribution mismatch:\n"
            f"Legacy:   {dict(legacy_summary)}\n"
            f"Ast-grep: {dict(ast_grep_summary)}"
        )
    
    def test_relation_count_parity(self, legacy_results, ast_grep_results):
        """Test that both parsers produce the same number of relations."""
        _, legacy_relations = legacy_results
        _, ast_grep_relations = ast_grep_results
        
        assert len(legacy_relations) == len(ast_grep_relations), (
            f"Relation count mismatch: legacy={len(legacy_relations)}, "
            f"ast-grep={len(ast_grep_relations)}"
        )
    
    def test_relation_tuples_parity(self, legacy_results, ast_grep_results):
        """Test that both parsers produce identical relation tuples."""
        _, legacy_relations = legacy_results
        _, ast_grep_relations = ast_grep_results
        
        # Convert to multisets (allow duplicates, order independent)
        legacy_tuples = sorted([self._get_relation_key(r) for r in legacy_relations])
        ast_grep_tuples = sorted([self._get_relation_key(r) for r in ast_grep_relations])
        
        # Find differences
        legacy_counter = Counter(legacy_tuples)
        ast_grep_counter = Counter(ast_grep_tuples)
        
        missing_in_ast_grep = []
        for rel_tuple, count in legacy_counter.items():
            if ast_grep_counter[rel_tuple] < count:
                diff = count - ast_grep_counter[rel_tuple]
                missing_in_ast_grep.extend([rel_tuple] * diff)
        
        extra_in_ast_grep = []
        for rel_tuple, count in ast_grep_counter.items():
            if legacy_counter[rel_tuple] < count:
                diff = count - legacy_counter[rel_tuple]
                extra_in_ast_grep.extend([rel_tuple] * diff)
        
        if missing_in_ast_grep:
            print("\nRelations in legacy but missing in ast-grep:")
            for src, rel_type, tgt in missing_in_ast_grep[:10]:
                print(f"  - {src} --[{rel_type}]--> {tgt}")
            if len(missing_in_ast_grep) > 10:
                print(f"  ... and {len(missing_in_ast_grep) - 10} more")
        
        if extra_in_ast_grep:
            print("\nRelations in ast-grep but missing in legacy:")
            for src, rel_type, tgt in extra_in_ast_grep[:10]:
                print(f"  - {src} --[{rel_type}]--> {tgt}")
            if len(extra_in_ast_grep) > 10:
                print(f"  ... and {len(extra_in_ast_grep) - 10} more")
        
        assert legacy_tuples == ast_grep_tuples, (
            f"Relation tuple sets differ: "
            f"{len(missing_in_ast_grep)} missing in ast-grep, "
            f"{len(extra_in_ast_grep)} extra in ast-grep"
        )
    
    def test_relation_type_distribution_parity(self, legacy_results, ast_grep_results):
        """Test that both parsers produce the same distribution of relation types."""
        _, legacy_relations = legacy_results
        _, ast_grep_relations = ast_grep_results
        
        legacy_summary = self._get_relation_summary(legacy_relations)
        ast_grep_summary = self._get_relation_summary(ast_grep_relations)
        
        assert legacy_summary == ast_grep_summary, (
            f"Relation type distribution mismatch:\n"
            f"Legacy:   {dict(legacy_summary)}\n"
            f"Ast-grep: {dict(ast_grep_summary)}"
        )
    
    def test_file_nodes_parity(self, legacy_results, ast_grep_results):
        """Test that both parsers create file nodes for all Python files."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        
        # Filter file nodes
        legacy_files = {
            node.name: node_id 
            for node_id, node in legacy_nodes.items() 
            if node.node_type == 'File'
        }
        ast_grep_files = {
            node.name: node_id 
            for node_id, node in ast_grep_nodes.items() 
            if node.node_type == 'File'
        }
        
        assert set(legacy_files.keys()) == set(ast_grep_files.keys()), (
            f"File node mismatch:\n"
            f"Legacy:   {sorted(legacy_files.keys())}\n"
            f"Ast-grep: {sorted(ast_grep_files.keys())}"
        )
    
    def test_import_resolution_parity(self, legacy_results, ast_grep_results):
        """Test that both parsers resolve imports identically."""
        _, legacy_relations = legacy_results
        _, ast_grep_relations = ast_grep_results
        
        # Filter import relations
        legacy_imports = sorted([
            self._get_relation_key(r) 
            for r in legacy_relations 
            if 'IMPORT' in r.relation_type
        ])
        ast_grep_imports = sorted([
            self._get_relation_key(r) 
            for r in ast_grep_relations 
            if 'IMPORT' in r.relation_type
        ])
        
        assert legacy_imports == ast_grep_imports, (
            f"Import resolution differs:\n"
            f"Legacy has {len(legacy_imports)} import relations\n"
            f"Ast-grep has {len(ast_grep_imports)} import relations"
        )
    
    def test_call_relations_parity(self, legacy_results, ast_grep_results):
        """Test that both parsers detect function calls identically."""
        _, legacy_relations = legacy_results
        _, ast_grep_relations = ast_grep_results
        
        # Filter CALLS relations
        legacy_calls = sorted([
            self._get_relation_key(r) 
            for r in legacy_relations 
            if r.relation_type == 'CALLS'
        ])
        ast_grep_calls = sorted([
            self._get_relation_key(r) 
            for r in ast_grep_relations 
            if r.relation_type == 'CALLS'
        ])
        
        assert legacy_calls == ast_grep_calls, (
            f"CALLS relation differs:\n"
            f"Legacy has {len(legacy_calls)} CALLS relations\n"
            f"Ast-grep has {len(ast_grep_calls)} CALLS relations"
        )
    
    def test_containment_relations_parity(self, legacy_results, ast_grep_results):
        """Test that both parsers create identical containment hierarchies."""
        _, legacy_relations = legacy_results
        _, ast_grep_relations = ast_grep_results
        
        # Filter CONTAINS relations
        legacy_contains = sorted([
            self._get_relation_key(r) 
            for r in legacy_relations 
            if r.relation_type == 'CONTAINS'
        ])
        ast_grep_contains = sorted([
            self._get_relation_key(r) 
            for r in ast_grep_relations 
            if r.relation_type == 'CONTAINS'
        ])
        
        assert legacy_contains == ast_grep_contains, (
            f"CONTAINS relation differs:\n"
            f"Legacy has {len(legacy_contains)} CONTAINS relations\n"
            f"Ast-grep has {len(ast_grep_contains)} CONTAINS relations"
        )


class TestIndividualFilesParity:
    """Test parity on individual Python files from example_codebase."""
    
    @pytest.fixture
    def example_codebase_path(self):
        """Return path to example_codebase directory."""
        return os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'example_codebase'
        )
    
    def _parse_with_legacy(self, file_path: str) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """Parse a single file with legacy ASTParser."""
        parser = ASTParser()
        return parser.parse_file(file_path, build_index=True)
    
    def _parse_with_ast_grep(self, file_path: str) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """Parse a single file with PythonAstGrepAdapter."""
        adapter = PythonAstGrepAdapter()
        return adapter.parse_file(file_path, build_index=True)
    
    @pytest.mark.parametrize("filename", [
        "utils.py",
        "models.py",
        "main.py",
        "events.py"
    ])
    def test_individual_file_parity(self, example_codebase_path, filename):
        """Test that individual files parse identically."""
        file_path = os.path.join(example_codebase_path, filename)
        
        # Parse with both parsers
        legacy_nodes, legacy_relations = self._parse_with_legacy(file_path)
        ast_grep_nodes, ast_grep_relations = self._parse_with_ast_grep(file_path)
        
        # Compare node counts
        assert len(legacy_nodes) == len(ast_grep_nodes), (
            f"{filename}: Node count mismatch "
            f"(legacy={len(legacy_nodes)}, ast-grep={len(ast_grep_nodes)})"
        )
        
        # Compare node IDs
        assert set(legacy_nodes.keys()) == set(ast_grep_nodes.keys()), (
            f"{filename}: Node ID sets differ"
        )
        
        # Compare relation counts
        assert len(legacy_relations) == len(ast_grep_relations), (
            f"{filename}: Relation count mismatch "
            f"(legacy={len(legacy_relations)}, ast-grep={len(ast_grep_relations)})"
        )
        
        # Compare relation tuples
        legacy_tuples = sorted([
            (r.source_id, r.relation_type, r.target_id) 
            for r in legacy_relations
        ])
        ast_grep_tuples = sorted([
            (r.source_id, r.relation_type, r.target_id) 
            for r in ast_grep_relations
        ])
        
        assert legacy_tuples == ast_grep_tuples, (
            f"{filename}: Relation tuples differ"
        )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
