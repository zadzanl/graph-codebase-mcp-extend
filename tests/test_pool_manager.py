"""
Unit tests for ProcessingPoolManager.
"""

import os
import pytest
from unittest.mock import patch
from src.parallel.pool_manager import (
    ProcessingPoolManager,
    get_processing_pool,
)


def sample_worker_function(x):
    """Sample function for testing parallel execution."""
    return x * x


class TestProcessingPoolManager:
    """Test suite for ProcessingPoolManager."""
    
    def test_initialization_defaults(self):
        """Test default initialization."""
        manager = ProcessingPoolManager()
        assert manager.max_workers >= 1
        assert manager.use_sequential is False
        assert manager.force_executor_type is None
        assert manager.executor is None  # Not initialized until __enter__
    
    def test_initialization_explicit_workers(self):
        """Test initialization with explicit worker count."""
        manager = ProcessingPoolManager(max_workers=4)
        assert manager.max_workers == 4
    
    def test_initialization_sequential_mode(self):
        """Test initialization in sequential mode."""
        manager = ProcessingPoolManager(use_sequential=True)
        assert manager.use_sequential is True
    
    @patch.dict(os.environ, {'PARALLEL_INDEXING_ENABLED': 'false'})
    def test_parallel_indexing_disabled_via_env(self):
        """Test that parallel indexing can be disabled via environment variable."""
        with ProcessingPoolManager() as manager:
            assert manager.use_sequential is True
            assert manager.executor_type == "sequential"
    
    def test_sequential_submit(self):
        """Test task submission in sequential mode."""
        with ProcessingPoolManager(use_sequential=True) as manager:
            future = manager.submit(sample_worker_function, 5)
            result = future.result()
            assert result == 25
    
    def test_sequential_map(self):
        """Test map operation in sequential mode."""
        with ProcessingPoolManager(use_sequential=True) as manager:
            results = list(manager.map(sample_worker_function, [1, 2, 3, 4]))
            assert results == [1, 4, 9, 16]
    
    @patch('src.parallel.pool_manager.should_use_threads')
    def test_thread_executor_selection(self, mock_should_use_threads):
        """Test ThreadPoolExecutor selection when free-threading available."""
        mock_should_use_threads.return_value = True
        
        with ProcessingPoolManager(max_workers=2) as manager:
            assert manager.executor_type == "thread"
            assert manager.executor is not None
    
    @patch('src.parallel.pool_manager.should_use_threads')
    def test_process_executor_selection(self, mock_should_use_threads):
        """Test ProcessPoolExecutor selection on standard Python."""
        mock_should_use_threads.return_value = False
        
        with ProcessingPoolManager(max_workers=2) as manager:
            assert manager.executor_type == "process"
            assert manager.executor is not None
    
    def test_force_thread_executor(self):
        """Test forcing ThreadPoolExecutor."""
        with ProcessingPoolManager(max_workers=2, force_executor_type='thread') as manager:
            assert manager.executor_type == "thread"
    
    def test_force_process_executor(self):
        """Test forcing ProcessPoolExecutor."""
        with ProcessingPoolManager(max_workers=2, force_executor_type='process') as manager:
            assert manager.executor_type == "process"
    
    def test_get_executor_info(self):
        """Test executor information retrieval."""
        with ProcessingPoolManager(max_workers=4, use_sequential=True) as manager:
            info = manager.get_executor_info()
            
            assert 'executor_type' in info
            assert 'max_workers' in info
            assert 'use_sequential' in info
            assert 'initial_gil_status' in info
            assert 'current_gil_status' in info
            
            assert info['executor_type'] == 'sequential'
            assert info['max_workers'] == 4
            assert info['use_sequential'] is True
    
    def test_context_manager_cleanup(self):
        """Test that context manager properly cleans up resources."""
        manager = ProcessingPoolManager(max_workers=2)
        
        with manager:
            pass  # Executor is initialized here
        
        # After exiting context, executor should be shut down
        assert manager.executor is None


class TestGetProcessingPool:
    """Test suite for get_processing_pool convenience function."""
    
    def test_small_item_count_uses_sequential(self):
        """Test that small item counts trigger sequential processing."""
        with get_processing_pool(item_count=10, min_items_for_parallel=50) as pool:
            assert pool.use_sequential is True
            assert pool.executor_type == "sequential"
    
    def test_large_item_count_uses_parallel(self):
        """Test that large item counts trigger parallel processing."""
        with get_processing_pool(item_count=100, min_items_for_parallel=50) as pool:
            # Should use parallel (not sequential)
            assert pool.use_sequential is False
            assert pool.executor_type in ["thread", "process"]
    
    @patch.dict(os.environ, {'MIN_FILES_FOR_PARALLEL': '30'})
    def test_min_files_from_environment(self):
        """Test reading MIN_FILES_FOR_PARALLEL from environment."""
        with get_processing_pool(item_count=25) as pool:
            # 25 < 30, should be sequential
            assert pool.use_sequential is True
    
    def test_no_item_count_uses_parallel(self):
        """Test that None item_count triggers parallel processing."""
        with get_processing_pool(item_count=None) as pool:
            # Should use parallel when item count is not specified
            assert pool.use_sequential is False
    
    def test_context_manager_exception_handling(self):
        """Test that exceptions are properly propagated."""
        with pytest.raises(ValueError):
            with get_processing_pool(item_count=10):
                raise ValueError("Test exception")
    
    def test_keyboard_interrupt_handling(self):
        """Test that KeyboardInterrupt is properly handled."""
        with pytest.raises(KeyboardInterrupt):
            with get_processing_pool(item_count=10):
                raise KeyboardInterrupt()


class TestParallelExecution:
    """Test suite for actual parallel execution (ThreadPoolExecutor only)."""
    
    def test_thread_executor_submit_and_result(self):
        """Test submitting tasks with ThreadPoolExecutor."""
        with ProcessingPoolManager(max_workers=2, force_executor_type='thread') as manager:
            futures = [manager.submit(sample_worker_function, i) for i in range(5)]
            results = [f.result() for f in futures]
            assert results == [0, 1, 4, 9, 16]
    
    def test_thread_executor_map(self):
        """Test map with ThreadPoolExecutor."""
        with ProcessingPoolManager(max_workers=2, force_executor_type='thread') as manager:
            results = list(manager.map(sample_worker_function, range(5)))
            assert results == [0, 1, 4, 9, 16]
    
    def test_exception_handling_in_worker(self):
        """Test that exceptions in workers are properly handled."""
        def failing_task(x):
            if x == 3:
                raise ValueError("Test error")
            return x * x
        
        with ProcessingPoolManager(max_workers=2, force_executor_type='thread') as manager:
            futures = [manager.submit(failing_task, i) for i in range(5)]
            
            # First three should succeed
            assert futures[0].result() == 0
            assert futures[1].result() == 1
            assert futures[2].result() == 4
            
            # Fourth should raise exception
            with pytest.raises(ValueError, match="Test error"):
                futures[3].result()
            
            # Fifth should succeed
            assert futures[4].result() == 16


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
