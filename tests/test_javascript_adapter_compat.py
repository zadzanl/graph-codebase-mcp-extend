"""
Comprehensive parity tests for JavaScript/TypeScript adapter.

Tests that JavaScriptAstGrepAdapter produces identical output to TypeScriptParser.
Similar to test_python_adapter_compat.py from Phase 4.
"""

import os
import pytest
from typing import Dict, List, Tuple
from collections import Counter

from src.ast_parser.typescript_parser import TypeScriptParser
from src.ast_parser.adapters.javascript_adapter import JavaScriptAstGrepAdapter
from src.ast_parser.multi_parser import MultiLanguageParser
from src.ast_parser.parser import CodeNode, CodeRelation


@pytest.fixture
def js_ts_sample_path():
    """Path to JavaScript/TypeScript test fixtures."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", "js_ts_sample"))


class TestJavaScriptAdapterParity:
    """Test parity between JavaScriptAstGrepAdapter and TypeScriptParser at directory level."""
    
    @pytest.fixture
    def legacy_results(self, js_ts_sample_path):
        """Parse with TypeScriptParser (legacy)."""
        parser = TypeScriptParser()
        return parser.parse_directory(js_ts_sample_path)
    
    @pytest.fixture
    def ast_grep_results(self, js_ts_sample_path):
        """Parse with MultiLanguageParser using ast-grep adapters."""
        coordinator = MultiLanguageParser(
            use_ast_grep=True,
            ast_grep_languages=['javascript', 'typescript'],
            ast_grep_fallback=False
        )
        return coordinator.parse_directory(js_ts_sample_path, build_index=True)
    
    def test_node_count_parity(self, legacy_results, ast_grep_results):
        """Verify same total number of nodes."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        assert len(legacy_nodes) == len(ast_grep_nodes), \
            f"Node count mismatch: legacy={len(legacy_nodes)}, ast-grep={len(ast_grep_nodes)}"
    
    def test_node_ids_parity(self, legacy_results, ast_grep_results):
        """Verify exact same set of node IDs."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        
        legacy_ids = set(legacy_nodes.keys())
        ast_grep_ids = set(ast_grep_nodes.keys())
        
        missing_in_ast_grep = legacy_ids - ast_grep_ids
        extra_in_ast_grep = ast_grep_ids - legacy_ids
        
        assert legacy_ids == ast_grep_ids, \
            f"Node IDs mismatch:\n  Missing in ast-grep: {missing_in_ast_grep}\n  Extra in ast-grep: {extra_in_ast_grep}"
    
    def test_node_type_distribution_parity(self, legacy_results, ast_grep_results):
        """Verify same distribution of node types."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        
        legacy_types = Counter(node.node_type for node in legacy_nodes.values())
        ast_grep_types = Counter(node.node_type for node in ast_grep_nodes.values())
        
        assert legacy_types == ast_grep_types, \
            f"Node type distribution mismatch:\n  Legacy: {dict(legacy_types)}\n  ast-grep: {dict(ast_grep_types)}"
    
    def test_relation_count_parity(self, legacy_results, ast_grep_results):
        """Verify same total number of relations."""
        _, legacy_relations = legacy_results
        _, ast_grep_relations = ast_grep_results
        assert len(legacy_relations) == len(ast_grep_relations), \
            f"Relation count mismatch: legacy={len(legacy_relations)}, ast-grep={len(ast_grep_relations)}"
    
    def test_relation_tuples_parity(self, legacy_results, ast_grep_results):
        """Verify exact same set of relation tuples."""
        _, legacy_relations = legacy_results
        _, ast_grep_relations = ast_grep_results
        
        # Convert to tuples for comparison (order-independent, allows duplicates)
        legacy_tuples = Counter((r.source_id, r.relation_type, r.target_id) for r in legacy_relations)
        ast_grep_tuples = Counter((r.source_id, r.relation_type, r.target_id) for r in ast_grep_relations)
        
        assert legacy_tuples == ast_grep_tuples, \
            f"Relation tuples mismatch:\n  Only in legacy: {legacy_tuples - ast_grep_tuples}\n  Only in ast-grep: {ast_grep_tuples - legacy_tuples}"
    
    def test_relation_type_distribution_parity(self, legacy_results, ast_grep_results):
        """Verify same distribution of relation types."""
        _, legacy_relations = legacy_results
        _, ast_grep_relations = ast_grep_results
        
        legacy_types = Counter(r.relation_type for r in legacy_relations)
        ast_grep_types = Counter(r.relation_type for r in ast_grep_relations)
        
        assert legacy_types == ast_grep_types, \
            f"Relation type distribution mismatch:\n  Legacy: {dict(legacy_types)}\n  ast-grep: {dict(ast_grep_types)}"
    
    def test_file_nodes_parity(self, legacy_results, ast_grep_results):
        """Verify file nodes are identical."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        
        legacy_files = {n.name for n in legacy_nodes.values() if n.node_type == "File"}
        ast_grep_files = {n.name for n in ast_grep_nodes.values() if n.node_type == "File"}
        
        assert legacy_files == ast_grep_files, \
            f"File nodes mismatch:\n  Legacy: {legacy_files}\n  ast-grep: {ast_grep_files}"
    
    def test_function_nodes_parity(self, legacy_results, ast_grep_results):
        """Verify function nodes match."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        
        legacy_funcs = {n.name for n in legacy_nodes.values() if n.node_type == "Function"}
        ast_grep_funcs = {n.name for n in ast_grep_nodes.values() if n.node_type == "Function"}
        
        assert legacy_funcs == ast_grep_funcs, \
            f"Function nodes mismatch:\n  Legacy: {legacy_funcs}\n  ast-grep: {ast_grep_funcs}"
    
    def test_class_nodes_parity(self, legacy_results, ast_grep_results):
        """Verify class nodes match."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        
        legacy_classes = {n.name for n in legacy_nodes.values() if n.node_type == "Class"}
        ast_grep_classes = {n.name for n in ast_grep_nodes.values() if n.node_type == "Class"}
        
        assert legacy_classes == ast_grep_classes, \
            f"Class nodes mismatch:\n  Legacy: {legacy_classes}\n  ast-grep: {ast_grep_classes}"
    
    def test_method_nodes_parity(self, legacy_results, ast_grep_results):
        """Verify method nodes match."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        
        legacy_methods = {n.name for n in legacy_nodes.values() if n.node_type == "Method"}
        ast_grep_methods = {n.name for n in ast_grep_nodes.values() if n.node_type == "Method"}
        
        assert legacy_methods == ast_grep_methods, \
            f"Method nodes mismatch:\n  Legacy: {legacy_methods}\n  ast-grep: {ast_grep_methods}"
    
    def test_variable_nodes_parity(self, legacy_results, ast_grep_results):
        """Verify variable nodes match."""
        legacy_nodes, _ = legacy_results
        ast_grep_nodes, _ = ast_grep_results
        
        legacy_vars = {n.name for n in legacy_nodes.values() if n.node_type == "Variable"}
        ast_grep_vars = {n.name for n in ast_grep_nodes.values() if n.node_type == "Variable"}
        
        assert legacy_vars == ast_grep_vars, \
            f"Variable nodes mismatch:\n  Legacy: {legacy_vars}\n  ast-grep: {ast_grep_vars}"
    
    def test_contains_relations_parity(self, legacy_results, ast_grep_results):
        """Verify CONTAINS relations match."""
        _, legacy_relations = legacy_results
        _, ast_grep_relations = ast_grep_results
        
        legacy_contains = Counter((r.source_id, r.target_id) for r in legacy_relations if r.relation_type == "CONTAINS")
        ast_grep_contains = Counter((r.source_id, r.target_id) for r in ast_grep_relations if r.relation_type == "CONTAINS")
        
        assert legacy_contains == ast_grep_contains, \
            f"CONTAINS relations mismatch"
    
    def test_defines_relations_parity(self, legacy_results, ast_grep_results):
        """Verify DEFINES relations match."""
        _, legacy_relations = legacy_results
        _, ast_grep_relations = ast_grep_results
        
        legacy_defines = Counter((r.source_id, r.target_id) for r in legacy_relations if r.relation_type == "DEFINES")
        ast_grep_defines = Counter((r.source_id, r.target_id) for r in ast_grep_relations if r.relation_type == "DEFINES")
        
        assert legacy_defines == ast_grep_defines, \
            f"DEFINES relations mismatch"
    
    def test_extends_relations_parity(self, legacy_results, ast_grep_results):
        """Verify EXTENDS relations match."""
        _, legacy_relations = legacy_results
        _, ast_grep_relations = ast_grep_results
        
        legacy_extends = Counter((r.source_id, r.target_id) for r in legacy_relations if r.relation_type == "EXTENDS")
        ast_grep_extends = Counter((r.source_id, r.target_id) for r in ast_grep_relations if r.relation_type == "EXTENDS")
        
        assert legacy_extends == ast_grep_extends, \
            f"EXTENDS relations mismatch"


class TestIndividualFilesParity:
    """Test parity on individual files."""
    
    @pytest.mark.parametrize("filename", [
        "functions.js",
        "classes.js",
        "imports.js",
        "types.ts"
    ])
    def test_individual_file_parity(self, filename, js_ts_sample_path):
        """Test that each individual file parses identically."""
        file_path = os.path.join(js_ts_sample_path, filename)
        
        # Parse with legacy parser
        legacy_parser = TypeScriptParser()
        legacy_nodes, legacy_relations = legacy_parser.parse_file(file_path)
        
        # Parse with ast-grep adapter
        ast_grep_adapter = JavaScriptAstGrepAdapter()
        ast_grep_nodes, ast_grep_relations = ast_grep_adapter.parse_file(file_path)
        
        # Compare node count
        assert len(legacy_nodes) == len(ast_grep_nodes), \
            f"{filename}: Node count mismatch - legacy={len(legacy_nodes)}, ast-grep={len(ast_grep_nodes)}"
        
        # Compare node IDs
        assert set(legacy_nodes.keys()) == set(ast_grep_nodes.keys()), \
            f"{filename}: Node IDs don't match"
        
        # Compare relation count
        assert len(legacy_relations) == len(ast_grep_relations), \
            f"{filename}: Relation count mismatch - legacy={len(legacy_relations)}, ast-grep={len(ast_grep_relations)}"
        
        # Compare relation tuples
        legacy_tuples = Counter((r.source_id, r.relation_type, r.target_id) for r in legacy_relations)
        ast_grep_tuples = Counter((r.source_id, r.relation_type, r.target_id) for r in ast_grep_relations)
        assert legacy_tuples == ast_grep_tuples, \
            f"{filename}: Relation tuples don't match"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
