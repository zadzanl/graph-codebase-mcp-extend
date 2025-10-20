"""
Integration tests for mixed Python/JavaScript/TypeScript codebases.

Tests that the system can handle projects with multiple languages:
- Python + JavaScript
- Python + TypeScript
- All three languages together
- Parser routing works correctly
- No breaking changes to Python processing
"""

import os
import tempfile
import shutil
import unittest
from src.main import CodebaseKnowledgeGraph


class TestMixedCodebase(unittest.TestCase):
    """Test suite for mixed language codebases."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        
        # Mock embedder and graph_db for testing
        self.mock_embedder = None
        self.mock_graph_db = None

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_test_file(self, filename: str, content: str) -> str:
        """Create a test file with given content."""
        file_path = os.path.join(self.test_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path

    def test_collect_mixed_source_files(self):
        """Test that file collection includes all supported extensions."""
        # Create test files
        self._create_test_file("script.py", "def test(): pass")
        self._create_test_file("app.js", "function test() {}")
        self._create_test_file("types.ts", "function test(): void {}")
        self._create_test_file("component.jsx", "function Test() { return null; }")
        self._create_test_file("component.tsx", "function Test(): JSX.Element { return null; }")
        self._create_test_file("README.md", "# Documentation")  # Should be ignored
        
        # Create processor instance
        processor = CodebaseKnowledgeGraph(self.mock_embedder, self.mock_graph_db)
        
        # Collect files
        files = processor._collect_source_files(self.test_dir)
        
        # Should include Python, JS, TS, JSX, TSX files
        self.assertEqual(len(files), 5)
        
        # Check file extensions
        extensions = [os.path.splitext(f)[1] for f in files]
        self.assertIn('.py', extensions)
        self.assertIn('.js', extensions)
        self.assertIn('.ts', extensions)
        self.assertIn('.jsx', extensions)
        self.assertIn('.tsx', extensions)
        self.assertNotIn('.md', extensions)

    def test_parser_routing_python(self):
        """Test that Python files are routed to ASTParser."""
        self._create_test_file("test.py", """
def greet(name):
    return f"Hello, {name}!"

class Person:
    def __init__(self, name):
        self.name = name
""")
        
        processor = CodebaseKnowledgeGraph(self.mock_embedder, self.mock_graph_db)
        parser = processor._get_parser_for_file(os.path.join(self.test_dir, "test.py"))
        
        # Should be ASTParser
        self.assertEqual(type(parser).__name__, 'ASTParser')

    def test_parser_routing_javascript(self):
        """Test that JavaScript files are routed to TypeScriptParser."""
        self._create_test_file("test.js", "function test() {}")
        
        processor = CodebaseKnowledgeGraph(self.mock_embedder, self.mock_graph_db)
        parser = processor._get_parser_for_file(os.path.join(self.test_dir, "test.js"))
        
        # Should be TypeScriptParser
        self.assertEqual(type(parser).__name__, 'TypeScriptParser')

    def test_parser_routing_typescript(self):
        """Test that TypeScript files are routed to TypeScriptParser."""
        self._create_test_file("test.ts", "function test(): void {}")
        
        processor = CodebaseKnowledgeGraph(self.mock_embedder, self.mock_graph_db)
        parser = processor._get_parser_for_file(os.path.join(self.test_dir, "test.ts"))
        
        # Should be TypeScriptParser
        self.assertEqual(type(parser).__name__, 'TypeScriptParser')

    def test_mixed_codebase_python_and_js(self):
        """Test processing a codebase with both Python and JavaScript."""
        # Create Python file
        self._create_test_file("backend/server.py", """
def start_server(port):
    print(f"Starting server on port {port}")

class Server:
    def __init__(self, port):
        self.port = port
""")
        
        # Create JavaScript file
        self._create_test_file("frontend/app.js", """
function initApp() {
    console.log('App initialized');
}

class App {
    constructor() {
        this.initialized = false;
    }
}
""")
        
        # Process both files
        from src.ast_parser.parser import ASTParser
        from src.ast_parser.typescript_parser import TypeScriptParser
        
        py_parser = ASTParser()
        js_parser = TypeScriptParser()
        
        py_nodes, py_relations = py_parser.parse_file(os.path.join(self.test_dir, "backend/server.py"))
        js_nodes, js_relations = js_parser.parse_file(os.path.join(self.test_dir, "frontend/app.js"))
        
        # Both should parse successfully
        self.assertGreater(len(py_nodes), 0)
        self.assertGreater(len(js_nodes), 0)
        
        # Check that Python nodes have Python entities
        py_func_nodes = [n for n in py_nodes.values() if n.node_type == "Function"]
        self.assertGreater(len(py_func_nodes), 0)
        
        # Check that JS nodes have JS entities
        js_func_nodes = [n for n in js_nodes.values() if n.node_type == "Function"]
        self.assertGreater(len(js_func_nodes), 0)

    def test_mixed_codebase_all_languages(self):
        """Test processing a codebase with Python, JavaScript, and TypeScript."""
        # Create files in different languages
        self._create_test_file("backend/api.py", """
def get_users():
    return []

class UserAPI:
    def fetch(self):
        pass
""")
        
        self._create_test_file("frontend/utils.js", """
function formatDate(date) {
    return date.toISOString();
}
""")
        
        self._create_test_file("frontend/types.ts", """
interface User {
    id: number;
    name: string;
}

function getUser(id: number): User {
    return { id, name: 'Test' };
}
""")
        
        # Parse each file
        from src.ast_parser.parser import ASTParser
        from src.ast_parser.typescript_parser import TypeScriptParser
        
        py_parser = ASTParser()
        ts_parser = TypeScriptParser()
        
        py_nodes, _ = py_parser.parse_file(os.path.join(self.test_dir, "backend/api.py"))
        js_nodes, _ = ts_parser.parse_file(os.path.join(self.test_dir, "frontend/utils.js"))
        ts_nodes, _ = ts_parser.parse_file(os.path.join(self.test_dir, "frontend/types.ts"))
        
        # All should parse successfully
        self.assertGreater(len(py_nodes), 0)
        self.assertGreater(len(js_nodes), 0)
        self.assertGreater(len(ts_nodes), 0)

    def test_python_processing_unchanged(self):
        """Test that Python processing is not affected by JS/TS support."""
        # Create Python-only codebase
        self._create_test_file("main.py", """
def main():
    print("Hello, World!")

class Application:
    def __init__(self):
        self.name = "TestApp"
    
    def run(self):
        main()
""")
        
        # Parse with ASTParser
        from src.ast_parser.parser import ASTParser
        parser = ASTParser()
        nodes, relations = parser.parse_file(os.path.join(self.test_dir, "main.py"))
        
        # Should have expected Python nodes
        func_nodes = [n for n in nodes.values() if n.node_type == "Function"]
        class_nodes = [n for n in nodes.values() if n.node_type == "Class"]
        
        self.assertEqual(len(func_nodes), 1)  # main function
        self.assertEqual(len(class_nodes), 1)  # Application class
        
        # Check relationships
        contains_relations = [r for r in relations if r.relation_type == "CONTAINS"]
        self.assertGreater(len(contains_relations), 0)

    def test_node_structure_compatibility(self):
        """Test that TypeScriptParser produces compatible node structures."""
        # Create test files
        py_file = self._create_test_file("test.py", """
def calculate(x, y):
    return x + y
""")
        
        js_file = self._create_test_file("test.js", """
function calculate(x, y) {
    return x + y;
}
""")
        
        # Parse both
        from src.ast_parser.parser import ASTParser
        from src.ast_parser.typescript_parser import TypeScriptParser
        
        py_parser = ASTParser()
        js_parser = TypeScriptParser()
        
        py_nodes, py_relations = py_parser.parse_file(py_file)
        js_nodes, js_relations = js_parser.parse_file(js_file)
        
        # Get function nodes
        py_func = next(n for n in py_nodes.values() if n.node_type == "Function")
        js_func = next(n for n in js_nodes.values() if n.node_type == "Function")
        
        # Both should have same structure
        self.assertEqual(py_func.node_type, js_func.node_type)
        self.assertIsNotNone(py_func.file_path)
        self.assertIsNotNone(js_func.file_path)
        self.assertIsNotNone(py_func.line_no)
        self.assertIsNotNone(js_func.line_no)
        self.assertIsInstance(py_func.properties, dict)
        self.assertIsInstance(js_func.properties, dict)

    def test_relation_structure_compatibility(self):
        """Test that TypeScriptParser produces compatible relation structures."""
        # Create test file
        js_file = self._create_test_file("test.js", """
class Parent {}
class Child extends Parent {}
""")
        
        from src.ast_parser.typescript_parser import TypeScriptParser
        parser = TypeScriptParser()
        nodes, relations = parser.parse_file(js_file)
        
        # Check relations have correct structure
        for relation in relations:
            self.assertIsNotNone(relation.source_id)
            self.assertIsNotNone(relation.target_id)
            self.assertIsNotNone(relation.relation_type)
            self.assertIn(relation.relation_type, ["CONTAINS", "DEFINES", "EXTENDS", "IMPORTS"])


if __name__ == '__main__':
    unittest.main()
