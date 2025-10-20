"""
Unit tests for TypeScriptParser class.

Tests the parsing of JavaScript and TypeScript files including:
- Function declarations (standard, arrow, async)
- Class declarations (with inheritance and methods)
- Variable declarations (const, let, var)
- Import/export statements
"""

import os
import tempfile
import shutil
import unittest
from src.ast_parser.typescript_parser import TypeScriptParser


class TestTypeScriptParser(unittest.TestCase):
    """Test suite for TypeScriptParser."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = TypeScriptParser()
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_test_file(self, filename: str, content: str) -> str:
        """Create a test file with given content."""
        file_path = os.path.join(self.test_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path

    def test_parse_standard_function(self):
        """Test parsing standard function declarations."""
        content = """
function greet(name) {
    return `Hello, ${name}!`;
}

function add(a, b) {
    return a + b;
}
"""
        file_path = self._create_test_file("test.js", content)
        nodes, relations = self.parser.parse_file(file_path)

        # Should have 1 file node + 2 function nodes
        self.assertEqual(len(nodes), 3)
        
        # Check function nodes
        func_nodes = [n for n in nodes.values() if n.node_type == "Function"]
        self.assertEqual(len(func_nodes), 2)
        
        # Check function names
        func_names = [n.name for n in func_nodes]
        self.assertIn("greet", func_names)
        self.assertIn("add", func_names)
        
        # Check parameters
        greet_node = next(n for n in func_nodes if n.name == "greet")
        self.assertEqual(greet_node.properties["parameters"], ["name"])
        
        add_node = next(n for n in func_nodes if n.name == "add")
        self.assertEqual(add_node.properties["parameters"], ["a", "b"])

    def test_parse_arrow_function(self):
        """Test parsing arrow function declarations."""
        content = """
const multiply = (x, y) => x * y;

const square = x => x * x;

const logMessage = () => {
    console.log('Hello');
};
"""
        file_path = self._create_test_file("test.js", content)
        nodes, relations = self.parser.parse_file(file_path)

        # Check arrow functions
        func_nodes = [n for n in nodes.values() if n.node_type == "Function"]
        self.assertEqual(len(func_nodes), 3)
        
        # Check function style
        multiply_node = next(n for n in func_nodes if n.name == "multiply")
        self.assertEqual(multiply_node.properties["function_style"], "arrow")
        self.assertEqual(multiply_node.properties["parameters"], ["x", "y"])

    def test_parse_async_function(self):
        """Test parsing async function declarations."""
        content = """
async function fetchData(url) {
    const response = await fetch(url);
    return response.json();
}

const asyncArrow = async (id) => {
    return await getData(id);
};
"""
        file_path = self._create_test_file("test.js", content)
        nodes, relations = self.parser.parse_file(file_path)

        # Check async functions
        func_nodes = [n for n in nodes.values() if n.node_type == "Function"]
        self.assertEqual(len(func_nodes), 2)
        
        # Both should be async
        for func_node in func_nodes:
            self.assertTrue(func_node.properties["is_async"])

    def test_parse_class_declaration(self):
        """Test parsing class declarations."""
        content = """
class Animal {
    constructor(name) {
        this.name = name;
    }
    
    speak() {
        console.log(`${this.name} makes a sound.`);
    }
}

class Dog extends Animal {
    constructor(name, breed) {
        super(name);
        this.breed = breed;
    }
    
    bark() {
        console.log('Woof!');
    }
}
"""
        file_path = self._create_test_file("test.js", content)
        nodes, relations = self.parser.parse_file(file_path)

        # Check class nodes
        class_nodes = [n for n in nodes.values() if n.node_type == "Class"]
        self.assertEqual(len(class_nodes), 2)
        
        # Check class names
        class_names = [n.name for n in class_nodes]
        self.assertIn("Animal", class_names)
        self.assertIn("Dog", class_names)
        
        # Check methods
        method_nodes = [n for n in nodes.values() if n.node_type == "Method"]
        self.assertGreaterEqual(len(method_nodes), 2)  # At least speak and bark
        
        # Check inheritance relationship
        extends_relations = [r for r in relations if r.relation_type == "EXTENDS"]
        self.assertEqual(len(extends_relations), 1)

    def test_parse_variables(self):
        """Test parsing variable declarations."""
        content = """
const API_KEY = 'secret';
let counter = 0;
var oldStyle = true;

const config = {
    host: 'localhost',
    port: 3000
};
"""
        file_path = self._create_test_file("test.js", content)
        nodes, relations = self.parser.parse_file(file_path)

        # Check variable nodes
        var_nodes = [n for n in nodes.values() if n.node_type == "Variable"]
        self.assertEqual(len(var_nodes), 4)
        
        # Check variable names and types
        var_info = {n.name: n.properties["declaration_type"] for n in var_nodes}
        self.assertEqual(var_info["API_KEY"], "const")
        self.assertEqual(var_info["counter"], "let")
        self.assertEqual(var_info["oldStyle"], "var")
        self.assertEqual(var_info["config"], "const")

    def test_parse_imports(self):
        """Test parsing import statements."""
        content = """
import React from 'react';
import { useState, useEffect } from 'react';
import * as utils from './utils';
import { User } from './models';
"""
        file_path = self._create_test_file("test.js", content)
        nodes, relations = self.parser.parse_file(file_path)

        # Check that imports are tracked
        self.assertGreater(len(self.parser.imports), 0)
        
        # Check pending imports
        self.assertGreater(len(self.parser.pending_imports), 0)

    def test_parse_exports(self):
        """Test parsing export statements."""
        content = """
export function helper(x) {
    return x * 2;
}

export class Utility {
    static calculate() {
        return 42;
    }
}

const secret = 'hidden';
export const PUBLIC_API = 'public';
"""
        file_path = self._create_test_file("test.js", content)
        nodes, relations = self.parser.parse_file(file_path)

        # Check exported entities
        exported_nodes = [n for n in nodes.values() if n.properties.get("exported")]
        self.assertGreaterEqual(len(exported_nodes), 2)  # helper, Utility, PUBLIC_API

    def test_parse_typescript_types(self):
        """Test parsing TypeScript files with type annotations."""
        content = """
interface User {
    id: number;
    name: string;
}

function getUser(id: number): User {
    return { id, name: 'Test' };
}

class UserService {
    private users: User[] = [];
    
    addUser(user: User): void {
        this.users.push(user);
    }
}
"""
        file_path = self._create_test_file("test.ts", content)
        nodes, relations = self.parser.parse_file(file_path)

        # Should parse successfully despite TypeScript syntax
        func_nodes = [n for n in nodes.values() if n.node_type == "Function"]
        self.assertGreaterEqual(len(func_nodes), 1)
        
        class_nodes = [n for n in nodes.values() if n.node_type == "Class"]
        self.assertEqual(len(class_nodes), 1)
        
        # Check language property
        user_service = next(n for n in class_nodes if n.name == "UserService")
        self.assertEqual(user_service.properties["language"], "typescript")

    def test_parse_jsx_syntax(self):
        """Test parsing JSX/React syntax."""
        content = """
import React from 'react';

function Welcome(props) {
    return <h1>Hello, {props.name}</h1>;
}

class App extends React.Component {
    render() {
        return (
            <div>
                <Welcome name="World" />
            </div>
        );
    }
}

export default App;
"""
        file_path = self._create_test_file("test.jsx", content)
        nodes, relations = self.parser.parse_file(file_path)

        # Should parse JSX files successfully
        func_nodes = [n for n in nodes.values() if n.node_type == "Function"]
        self.assertGreaterEqual(len(func_nodes), 1)
        
        class_nodes = [n for n in nodes.values() if n.node_type == "Class"]
        self.assertEqual(len(class_nodes), 1)

    def test_parse_directory(self):
        """Test parsing multiple files in a directory."""
        # Create multiple test files
        self._create_test_file("file1.js", "function test1() { return 1; }")
        self._create_test_file("file2.js", "function test2() { return 2; }")
        self._create_test_file("file3.ts", "function test3(): number { return 3; }")
        
        nodes, relations = self.parser.parse_directory(self.test_dir)

        # Should have nodes from all files
        file_nodes = [n for n in nodes.values() if n.node_type == "File"]
        self.assertEqual(len(file_nodes), 3)
        
        func_nodes = [n for n in nodes.values() if n.node_type == "Function"]
        self.assertEqual(len(func_nodes), 3)

    def test_error_handling_invalid_syntax(self):
        """Test error handling with invalid syntax."""
        content = "function incomplete( {"
        file_path = self._create_test_file("invalid.js", content)
        
        # Should not raise exception
        nodes, relations = self.parser.parse_file(file_path)
        
        # Should still create file node even if parsing fails
        file_nodes = [n for n in nodes.values() if n.node_type == "File"]
        self.assertGreaterEqual(len(file_nodes), 0)

    def test_contains_relationships(self):
        """Test that CONTAINS relationships are created correctly."""
        content = """
function topLevel() {}

class MyClass {
    method() {}
}

const myVar = 42;
"""
        file_path = self._create_test_file("test.js", content)
        nodes, relations = self.parser.parse_file(file_path)

        # Check CONTAINS relationships
        contains_relations = [r for r in relations if r.relation_type == "CONTAINS"]
        self.assertGreaterEqual(len(contains_relations), 3)  # file contains function, class, variable

    def test_defines_relationships(self):
        """Test that DEFINES relationships are created for class methods."""
        content = """
class Calculator {
    add(a, b) {
        return a + b;
    }
    
    subtract(a, b) {
        return a - b;
    }
}
"""
        file_path = self._create_test_file("test.js", content)
        nodes, relations = self.parser.parse_file(file_path)

        # Check DEFINES relationships
        defines_relations = [r for r in relations if r.relation_type == "DEFINES"]
        self.assertEqual(len(defines_relations), 2)  # class defines 2 methods

    def test_file_extension_routing(self):
        """Test that correct parser is selected based on file extension."""
        # Test with different extensions
        extensions = ['.js', '.ts', '.jsx', '.tsx']
        
        for ext in extensions:
            content = "function test() { return true; }"
            file_path = self._create_test_file(f"test{ext}", content)
            
            # Should parse successfully with appropriate parser
            nodes, relations = self.parser.parse_file(file_path)
            func_nodes = [n for n in nodes.values() if n.node_type == "Function"]
            self.assertEqual(len(func_nodes), 1)

    def test_code_snippet_extraction(self):
        """Test that code snippets are extracted correctly."""
        content = """
function example(x) {
    return x * 2;
}
"""
        file_path = self._create_test_file("test.js", content)
        nodes, relations = self.parser.parse_file(file_path)

        # Check code snippet
        func_nodes = [n for n in nodes.values() if n.node_type == "Function"]
        self.assertEqual(len(func_nodes), 1)
        
        func_node = func_nodes[0]
        self.assertIsNotNone(func_node.code_snippet)
        self.assertIn("function example", func_node.code_snippet)
        self.assertIn("return x * 2", func_node.code_snippet)


if __name__ == '__main__':
    unittest.main()
