"""
Test to verify the fix for parallel processing relationships bug.
This test ensures that relationships are properly preserved in both sequential and parallel modes.
"""
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import CodebaseKnowledgeGraph


def test_parallel_mode_preserves_relationships():
    """Test that parallel processing mode preserves structural relationships"""
    # Create a test codebase with multiple files
    test_dir = tempfile.mkdtemp()
    
    try:
        # Create test files with known structures
        file1 = os.path.join(test_dir, "module1.py")
        with open(file1, "w") as f:
            f.write("""
class TestClass:
    def method1(self):
        pass
    
    def method2(self):
        pass

def standalone_function():
    pass
""")
        
        file2 = os.path.join(test_dir, "module2.py")
        with open(file2, "w") as f:
            f.write("""
from module1 import TestClass

class DerivedClass(TestClass):
    def method3(self):
        pass
""")
        
        # Add more files to trigger parallel processing
        for i in range(3, 50):
            file_n = os.path.join(test_dir, f"module{i}.py")
            with open(file_n, "w") as f:
                f.write(f"""
def function_{i}():
    pass

class Class_{i}:
    def method_{i}(self):
        pass
""")
        
        # Mock Neo4j and embedding services
        with patch('src.main.Neo4jDatabase') as MockNeo4jDatabase, \
             patch('src.main.OpenAIEmbeddings') as MockOpenAIEmbeddings, \
             patch('src.main.CodeEmbedder') as MockCodeEmbedder:
            
            # Configure mocks
            mock_db_instance = MockNeo4jDatabase.return_value
            mock_db_instance.verify_connection.return_value = True
            mock_db_instance.batch_create_nodes.return_value = None
            mock_db_instance.batch_create_relationships.return_value = None
            mock_db_instance.create_schema_constraints.return_value = None
            mock_db_instance.create_vector_index.return_value = None
            mock_db_instance.create_full_text_index.return_value = None
            mock_db_instance.clear_database.return_value = None
            
            mock_embedder_instance = MockOpenAIEmbeddings.return_value
            mock_code_embedder_instance = MockCodeEmbedder.return_value
            default_dim = 1536
            mock_code_embedder_instance.embed_code_nodes_batch.return_value = [[0.0] * default_dim] * 200
            
            # Force parallel processing by setting environment
            os.environ['PARALLEL_INDEXING_ENABLED'] = 'true'
            os.environ['MIN_FILES_FOR_PARALLEL'] = '10'
            
            kg = CodebaseKnowledgeGraph(openai_api_key="mock_key")
            
            try:
                num_nodes, num_relations = kg.process_codebase(test_dir, clear_db=True)
                
                print(f"Parsed {num_nodes} nodes and {num_relations} relationships")
                
                # Verify that relationships were created
                # We should have:
                # - CONTAINS relationships (file -> class, file -> function)
                # - DEFINES relationships (class -> method)
                # - EXTENDS relationships (class inheritance)
                assert num_relations > 0, "No relationships were created!"
                
                # For 50 files with structures, we should have at least:
                # - 50 files
                # - ~50 classes = 50 CONTAINS (file->class)
                # - ~50 functions = 50 CONTAINS (file->function)
                # - ~50 methods = 50 DEFINES (class->method)
                # Total: at least 150 structural relationships
                assert num_relations >= 100, f"Expected at least 100 relationships, got {num_relations}"
                
                print(f"✅ SUCCESS: Parallel mode preserved {num_relations} relationships")
                
            finally:
                kg.close()
                
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def test_sequential_mode_preserves_relationships():
    """Test that sequential processing mode also preserves structural relationships"""
    # Create a small test codebase
    test_dir = tempfile.mkdtemp()
    
    try:
        # Create test files with known structures
        file1 = os.path.join(test_dir, "test.py")
        with open(file1, "w") as f:
            f.write("""
class MyClass:
    def my_method(self):
        pass

def my_function():
    pass
""")
        
        # Mock services
        with patch('src.main.Neo4jDatabase') as MockNeo4jDatabase, \
             patch('src.main.OpenAIEmbeddings') as MockOpenAIEmbeddings, \
             patch('src.main.CodeEmbedder') as MockCodeEmbedder:
            
            # Configure mocks
            mock_db_instance = MockNeo4jDatabase.return_value
            mock_db_instance.verify_connection.return_value = True
            mock_db_instance.batch_create_nodes.return_value = None
            mock_db_instance.batch_create_relationships.return_value = None
            mock_db_instance.create_schema_constraints.return_value = None
            mock_db_instance.create_vector_index.return_value = None
            mock_db_instance.create_full_text_index.return_value = None
            mock_db_instance.clear_database.return_value = None
            
            mock_embedder_instance = MockOpenAIEmbeddings.return_value
            mock_code_embedder_instance = MockCodeEmbedder.return_value
            default_dim = 1536
            mock_code_embedder_instance.embed_code_nodes_batch.return_value = [[0.0] * default_dim] * 10
            
            # Force sequential processing
            os.environ['PARALLEL_INDEXING_ENABLED'] = 'false'
            
            kg = CodebaseKnowledgeGraph(openai_api_key="mock_key")
            
            try:
                num_nodes, num_relations = kg.process_codebase(test_dir, clear_db=True)
                
                print(f"Parsed {num_nodes} nodes and {num_relations} relationships")
                
                # We should have:
                # - 1 file
                # - 1 class -> 1 CONTAINS (file->class)
                # - 1 method -> 1 DEFINES (class->method)
                # - 1 function -> 1 CONTAINS (file->function)
                # Total: at least 3 relationships
                assert num_relations > 0, "No relationships were created!"
                assert num_relations >= 3, f"Expected at least 3 relationships, got {num_relations}"
                
                print(f"✅ SUCCESS: Sequential mode preserved {num_relations} relationships")
                
            finally:
                kg.close()
                
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


if __name__ == "__main__":
    print("Testing relationship preservation fix...")
    print("\n=== Test 1: Sequential Mode ===")
    test_sequential_mode_preserves_relationships()
    print("\n=== Test 2: Parallel Mode ===")
    test_parallel_mode_preserves_relationships()
    print("\n✅ All tests passed!")
