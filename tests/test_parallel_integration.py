"""
Integration tests for parallel processing functionality.

Tests the parallel processing flow with real codebases.
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.parallel.pool_manager import get_processing_pool, ProcessingPoolManager


class TestParallelIntegration:
    """Integration tests for parallel codebase processing."""

    @pytest.fixture
    def small_codebase(self):
        """Create a small test codebase (< MIN_FILES_FOR_PARALLEL)."""
        tmpdir = tempfile.mkdtemp()
        
        # Create 3 Python files (below threshold)
        file1 = Path(tmpdir) / "file1.py"
        file1.write_text("""
def function1():
    pass

class Class1:
    def method1(self):
        pass
""")
        
        file2 = Path(tmpdir) / "file2.py"
        file2.write_text("""
from file1 import function1

def function2():
    function1()
""")
        
        file3 = Path(tmpdir) / "file3.py"
        file3.write_text("""
class Class2:
    pass
""")
        
        yield tmpdir
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def medium_codebase(self):
        """Create a medium test codebase (>= MIN_FILES_FOR_PARALLEL)."""
        tmpdir = tempfile.mkdtemp()
        
        # Create 60 Python files (above threshold of 50)
        for i in range(60):
            filepath = Path(tmpdir) / f"module_{i}.py"
            filepath.write_text(f"""
def function_{i}():
    '''Function {i} documentation'''
    return {i}

class Class_{i}:
    '''Class {i} documentation'''
    
    def method_{i}(self):
        return {i}
    
    @staticmethod
    def static_method_{i}():
        return {i} * 2
""")
        
        yield tmpdir
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def codebase_with_errors(self):
        """Create a codebase with some invalid Python files."""
        tmpdir = tempfile.mkdtemp()
        
        # Valid file
        (Path(tmpdir) / "valid.py").write_text("""
def valid_function():
    return 42
""")
        
        # Invalid syntax
        (Path(tmpdir) / "invalid_syntax.py").write_text("""
def broken_function(
    return 42  # Missing closing paren
""")
        
        # Empty file
        (Path(tmpdir) / "empty.py").write_text("")
        
        # File with ASCII characters only
        (Path(tmpdir) / "ascii.py").write_text("""
def func():
    s = "test"
    return s
""")
        
        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_small_codebase_uses_sequential(self, small_codebase):
        """Test that small codebases trigger sequential mode."""
        python_files = list(Path(small_codebase).rglob("*.py"))
        
        # Should be below threshold
        assert len(python_files) < 50
        
        # Test that small item count triggers sequential mode
        with patch.dict(os.environ, {"MIN_FILES_FOR_PARALLEL": "50"}):
            with get_processing_pool(item_count=len(python_files)) as pool:
                # Sequential mode means executor_type should be "sequential"
                assert pool.executor_type == "sequential"

    def test_medium_codebase_uses_parallel(self, medium_codebase):
        """Test that medium codebases trigger parallel mode."""
        python_files = list(Path(medium_codebase).rglob("*.py"))
        
        # Should be above threshold
        assert len(python_files) >= 50
        
        # Test that large item count triggers parallel mode
        with patch.dict(os.environ, {
            "MIN_FILES_FOR_PARALLEL": "50",
            "MAX_WORKERS": "4"
        }):
            with get_processing_pool(item_count=len(python_files)) as pool:
                # Should use either thread or process executor (not sequential)
                assert pool.executor_type in ("thread", "process")

    def test_error_handling_with_invalid_files(self, codebase_with_errors):
        """Test that ASTParser handles invalid files gracefully."""
        from src.ast_parser.parser import ASTParser
        
        parser = ASTParser()
        python_files = list(Path(codebase_with_errors).rglob("*.py"))
        
        # Parse each file - some will fail but shouldn't crash
        successful = 0
        failed = 0
        
        for py_file in python_files:
            try:
                nodes, _ = parser.parse_file(str(py_file))
                if nodes:
                    successful += 1
            except Exception:
                failed += 1
        
        # At least one file should parse successfully (valid.py and ascii.py)
        assert successful >= 1

    def test_parallel_disabled_via_env(self, medium_codebase):
        """Test that parallel processing can be disabled via environment."""
        python_files = list(Path(medium_codebase).rglob("*.py"))
        
        # Should be above threshold
        assert len(python_files) >= 50
        
        # But with PARALLEL_INDEXING_ENABLED=false, should use sequential
        with patch.dict(os.environ, {"PARALLEL_INDEXING_ENABLED": "false"}):
            with get_processing_pool(item_count=len(python_files)) as pool:
                assert pool.executor_type == "sequential"


class TestPoolManagerIntegration:
    """Integration tests for ProcessingPoolManager with actual work."""

    def test_get_processing_pool_with_small_workload(self):
        """Test pool manager with small workload (sequential mode)."""
        def double(x):
            return x * 2
        
        items = list(range(10))
        
        with patch.dict(os.environ, {"MIN_FILES_FOR_PARALLEL": "50"}):
            with get_processing_pool(item_count=len(items)) as pool:
                results = list(pool.map(double, items))
        
        assert results == [x * 2 for x in items]

    def test_get_processing_pool_with_large_workload(self):
        """Test pool manager with large workload (parallel mode with ThreadPoolExecutor)."""
        def double(x):
            return x * 2
        
        items = list(range(100))
        
        # Force ThreadPoolExecutor to avoid pickling issues with local functions on Windows
        with patch.dict(os.environ, {
            "MIN_FILES_FOR_PARALLEL": "50",
            "MAX_WORKERS": "2"  # Use 2 workers to avoid overhead
        }):
            # Use force_executor_type to ensure we use ThreadPoolExecutor
            with ProcessingPoolManager(max_workers=2, force_executor_type='thread') as pool:
                results = list(pool.map(double, items))
        
        # Results might not be in order with parallel processing
        assert sorted(results) == sorted([x * 2 for x in items])

    def test_pool_manager_exception_handling(self):
        """Test that pool manager handles exceptions in workers (sequential only)."""
        def worker_with_error(x):
            if x == 5:
                raise ValueError(f"Error processing {x}")
            return x * 2
        
        items = list(range(10))
        
        # Use sequential mode to test exception handling without pickling issues
        with patch.dict(os.environ, {"PARALLEL_INDEXING_ENABLED": "false"}):
            with get_processing_pool(item_count=len(items)) as pool:
                results = []
                errors = []
                
                for item in items:
                    future = pool.submit(worker_with_error, item)
                    try:
                        result = future.result()
                        results.append(result)
                    except ValueError as e:
                        errors.append(str(e))
        
        # Should have 9 successful results and 1 error
        assert len(results) == 9
        assert len(errors) == 1
        assert "Error processing 5" in errors[0]


class TestAdaptiveStrategy:
    """Test the adaptive strategy for choosing execution mode."""

    @patch("src.utils.runtime_detection.is_free_threading_available")
    @patch("src.utils.runtime_detection.is_gil_enabled")
    def test_thread_executor_on_free_threaded_build(
        self, mock_gil_enabled, mock_free_threading
    ):
        """Test ThreadPoolExecutor is used on free-threaded Python."""
        mock_free_threading.return_value = True
        mock_gil_enabled.return_value = False
        
        from src.utils.runtime_detection import should_use_threads
        assert should_use_threads() is True

    @patch("src.utils.runtime_detection.is_free_threading_available")
    @patch("src.utils.runtime_detection.is_gil_enabled")
    def test_process_executor_on_gil_enabled(
        self, mock_gil_enabled, mock_free_threading
    ):
        """Test ProcessPoolExecutor is used when GIL is enabled."""
        mock_free_threading.return_value = False
        mock_gil_enabled.return_value = True
        
        from src.utils.runtime_detection import should_use_threads
        assert should_use_threads() is False

    @patch("src.utils.runtime_detection.is_free_threading_available")
    @patch("src.utils.runtime_detection.is_gil_enabled")
    def test_warning_on_gil_reenablement(
        self, mock_gil_enabled, mock_free_threading, caplog
    ):
        """Test warning is logged when GIL is re-enabled on free-threaded build."""
        mock_free_threading.return_value = True
        mock_gil_enabled.return_value = True
        
        from src.utils.runtime_detection import check_gil_reenablement
        
        import logging
        with caplog.at_level(logging.WARNING):
            # check_gil_reenablement returns a tuple (gil_reenabled, current_gil_status)
            result = check_gil_reenablement(initial_gil_status=False)
        
        gil_reenabled, current_gil_status = result
        assert gil_reenabled is True
        assert current_gil_status is True
        # Check that a warning was logged
        assert any("GIL" in record.message and "re-enabled" in record.message for record in caplog.records)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
