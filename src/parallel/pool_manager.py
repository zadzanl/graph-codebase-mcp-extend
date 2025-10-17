"""
Processing pool manager for parallel codebase indexing.

This module provides a unified interface for parallel processing that automatically
selects between ThreadPoolExecutor (for free-threaded Python) and ProcessPoolExecutor
(for standard GIL-enabled Python) based on runtime detection.
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future
from typing import Callable, Optional
from contextlib import contextmanager

from src.utils.runtime_detection import (
    should_use_threads,
    get_optimal_worker_count,
    is_gil_enabled,
    log_runtime_info,
)

logger = logging.getLogger(__name__)


class ProcessingPoolManager:
    """
    Manager for parallel processing with automatic executor selection.
    
    This class automatically selects between ThreadPoolExecutor (for true
    parallelism on free-threaded Python) and ProcessPoolExecutor (for
    parallelism on standard GIL-enabled Python).
    
    It provides a context manager interface for proper resource cleanup.
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        use_sequential: bool = False,
        force_executor_type: Optional[str] = None,
    ):
        """
        Initialize the processing pool manager.
        
        Args:
            max_workers: Maximum number of worker threads/processes.
                        If None, uses optimal count based on CPU cores.
            use_sequential: If True, forces sequential processing (no parallelism).
            force_executor_type: Force a specific executor type:
                                'thread' for ThreadPoolExecutor,
                                'process' for ProcessPoolExecutor,
                                None for automatic detection.
        """
        self.max_workers = max_workers or get_optimal_worker_count()
        self.use_sequential = use_sequential
        self.force_executor_type = force_executor_type
        self.executor = None
        self.executor_type = None
        self.initial_gil_status = is_gil_enabled()
        
        # Log runtime information on first initialization
        if not hasattr(ProcessingPoolManager, '_runtime_info_logged'):
            log_runtime_info()
            ProcessingPoolManager._runtime_info_logged = True
    
    def __enter__(self):
        """Enter context manager and initialize executor."""
        self._initialize_executor()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and cleanup resources."""
        self._cleanup_executor()
        return False  # Don't suppress exceptions
    
    def _initialize_executor(self):
        """Initialize the appropriate executor based on configuration."""
        # Check if parallel indexing is disabled via environment variable
        parallel_enabled = os.environ.get("PARALLEL_INDEXING_ENABLED", "true").lower()
        if parallel_enabled in ("false", "0", "no"):
            logger.info("Parallel indexing disabled via PARALLEL_INDEXING_ENABLED")
            self.use_sequential = True
        
        if self.use_sequential:
            logger.info("Using sequential processing (no parallelism)")
            self.executor_type = "sequential"
            self.executor = None
            return
        
        # Determine executor type
        if self.force_executor_type:
            use_threads = self.force_executor_type.lower() == 'thread'
            logger.info(f"Executor type forced to: {self.force_executor_type}")
        else:
            use_threads = should_use_threads()
        
        # Create the appropriate executor
        if use_threads:
            self.executor_type = "thread"
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            logger.info(
                f"Using ThreadPoolExecutor with {self.max_workers} workers "
                f"(free-threaded mode)"
            )
        else:
            self.executor_type = "process"
            self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
            logger.info(
                f"Using ProcessPoolExecutor with {self.max_workers} workers "
                f"(GIL-enabled mode)"
            )
    
    def _cleanup_executor(self):
        """Cleanup and shutdown the executor."""
        if self.executor:
            try:
                self.executor.shutdown(wait=True)
                logger.debug(f"Executor ({self.executor_type}) shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down executor: {e}")
            finally:
                self.executor = None
    
    def submit(
        self,
        fn: Callable,
        *args,
        **kwargs
    ) -> Optional[Future]:
        """
        Submit a task for execution.
        
        Args:
            fn: Callable to execute
            *args: Positional arguments for fn
            **kwargs: Keyword arguments for fn
        
        Returns:
            Future object if using parallel execution, None if sequential.
        """
        if self.use_sequential or self.executor is None:
            # Sequential execution - run immediately
            from concurrent.futures import Future as FutureClass
            try:
                result = fn(*args, **kwargs)
                # Create a completed future-like object
                future = FutureClass()
                future.set_result(result)
                return future
            except Exception as e:
                future = FutureClass()
                future.set_exception(e)
                return future
        
        # Parallel execution
        return self.executor.submit(fn, *args, **kwargs)
    
    def map(
        self,
        fn: Callable,
        *iterables,
        timeout: Optional[float] = None,
        chunksize: int = 1,
    ):
        """
        Map a function over iterables with parallel execution.
        
        Args:
            fn: Callable to execute
            *iterables: Iterables to map over
            timeout: Maximum time to wait for results
            chunksize: Size of chunks for ProcessPoolExecutor
        
        Returns:
            Iterator of results
        """
        if self.use_sequential or self.executor is None:
            # Sequential execution
            return map(fn, *iterables)
        
        # Parallel execution
        if self.executor_type == "process":
            return self.executor.map(fn, *iterables, timeout=timeout, chunksize=chunksize)
        else:
            return self.executor.map(fn, *iterables, timeout=timeout)
    
    def get_executor_info(self) -> dict:
        """
        Get information about the current executor configuration.
        
        Returns:
            Dictionary with executor information
        """
        return {
            "executor_type": self.executor_type,
            "max_workers": self.max_workers,
            "use_sequential": self.use_sequential,
            "force_executor_type": self.force_executor_type,
            "initial_gil_status": self.initial_gil_status,
            "current_gil_status": is_gil_enabled(),
        }


@contextmanager
def get_processing_pool(
    max_workers: Optional[int] = None,
    min_items_for_parallel: Optional[int] = None,
    item_count: Optional[int] = None,
):
    """
    Context manager factory for processing pool.
    
    This is a convenience function that automatically decides whether to use
    sequential or parallel processing based on the number of items.
    
    Args:
        max_workers: Maximum number of workers
        min_items_for_parallel: Minimum items needed to use parallel processing
        item_count: Number of items to process
    
    Yields:
        ProcessingPoolManager instance
    
    Example:
        >>> with get_processing_pool(item_count=100) as pool:
        ...     futures = [pool.submit(process_file, f) for f in files]
        ...     results = [f.result() for f in futures]
    """
    # Determine if we should use sequential processing
    if min_items_for_parallel is None:
        min_items_for_parallel = int(
            os.environ.get("MIN_FILES_FOR_PARALLEL", "50")
        )
    
    use_sequential = False
    if item_count is not None and item_count < min_items_for_parallel:
        use_sequential = True
        logger.info(
            f"Using sequential processing ({item_count} items < "
            f"MIN_FILES_FOR_PARALLEL={min_items_for_parallel})"
        )
    
    manager = ProcessingPoolManager(
        max_workers=max_workers,
        use_sequential=use_sequential,
    )
    
    try:
        with manager as pool:
            yield pool
    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user (Ctrl+C)")
        raise
    except Exception as e:
        logger.error(f"Error in processing pool: {e}", exc_info=True)
        raise


# Example usage
if __name__ == "__main__":
    import time
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    def sample_task(x):
        """Sample task for testing."""
        time.sleep(0.1)
        return x * x
    
    # Test with context manager
    print("\nTest 1: Using context manager with auto-detection")
    with ProcessingPoolManager(max_workers=4) as pool:
        print(f"Executor info: {pool.get_executor_info()}")
        
        # Submit tasks
        futures = [pool.submit(sample_task, i) for i in range(10)]
        results = [f.result() for f in futures]
        print(f"Results: {results}")
    
    # Test with convenience function
    print("\nTest 2: Using convenience function with item count")
    with get_processing_pool(max_workers=4, item_count=100) as pool:
        print(f"Executor info: {pool.get_executor_info()}")
        
        # Use map
        results = list(pool.map(sample_task, range(10)))
        print(f"Results: {results}")
    
    # Test sequential processing
    print("\nTest 3: Sequential processing (small item count)")
    with get_processing_pool(max_workers=4, item_count=10) as pool:
        print(f"Executor info: {pool.get_executor_info()}")
        results = list(pool.map(sample_task, range(5)))
        print(f"Results: {results}")
