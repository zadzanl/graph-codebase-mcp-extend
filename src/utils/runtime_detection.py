"""
Runtime detection utilities for Python free-threading support.

This module provides functions to detect whether the current Python interpreter
supports free-threading (GIL-disabled mode) and whether the GIL is currently
enabled at runtime.
"""

import sys
import sysconfig
import os
import logging
from typing import Optional
from typing import Tuple

logger = logging.getLogger(__name__)


def is_free_threading_available() -> bool:
    """
    Check if the Python build supports free-threading.
    
    This checks the build-time configuration to determine if the interpreter
    was compiled with free-threading support (Py_GIL_DISABLED).
    
    Returns:
        bool: True if the build supports free-threading, False otherwise.
    """
    # Check build-time configuration
    py_gil_disabled = sysconfig.get_config_var("Py_GIL_DISABLED")
    return py_gil_disabled == 1


def is_gil_enabled() -> bool:
    """
    Check if the GIL is currently enabled at runtime.
    
    The GIL can be re-enabled at runtime even in a free-threaded build by:
    - Setting PYTHON_GIL=1 environment variable
    - Using -X gil=1 command-line option
    - Importing incompatible C extension modules (automatic with warning)
    
    Returns:
        bool: True if GIL is enabled, False if disabled.
              Returns True for Python < 3.13 (always has GIL).
    """
    # sys._is_gil_enabled() was added in Python 3.13
    if hasattr(sys, '_is_gil_enabled'):
        return sys._is_gil_enabled()
    
    # Python < 3.13 always has GIL enabled
    return True


def should_use_threads() -> bool:
    """
    Determine if ThreadPoolExecutor should be used for parallel processing.
    
    ThreadPoolExecutor provides true parallelism only when:
    1. The build supports free-threading (Py_GIL_DISABLED == 1)
    2. The GIL is currently disabled at runtime
    
    If either condition is false, ProcessPoolExecutor should be used instead.
    
    Returns:
        bool: True if ThreadPoolExecutor should be used, False otherwise.
    """
    return is_free_threading_available() and not is_gil_enabled()


def get_optimal_worker_count(max_workers: Optional[int] = None) -> int:
    """
    Calculate the optimal number of workers based on CPU cores.
    
    Args:
        max_workers: Optional maximum number of workers. If None, uses
                    environment variable MAX_WORKERS or defaults to
                    min(os.cpu_count(), 8).
    
    Returns:
        int: Optimal worker count (at least 1).
    """
    if max_workers is not None:
        return max(1, max_workers)
    
    # Try to get from environment variable
    env_workers = os.environ.get("MAX_WORKERS")
    if env_workers:
        try:
            return max(1, int(env_workers))
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid MAX_WORKERS value '{env_workers}', using default"
            )
    
    # Default: min(cpu_count, 8)
    cpu_count = os.cpu_count() or 4  # Fallback to 4 if cpu_count() returns None
    return min(cpu_count, 8)


def get_runtime_info() -> dict:
    """
    Get comprehensive runtime information for logging and debugging.
    
    Returns:
        dict: Dictionary containing:
            - python_version: Python version string
            - python_version_info: Tuple of version numbers
            - free_threading_available: Whether build supports free-threading
            - gil_enabled: Whether GIL is currently enabled
            - should_use_threads: Whether ThreadPoolExecutor should be used
            - optimal_worker_count: Recommended worker count
            - cpu_count: Number of CPU cores
    """
    return {
        "python_version": sys.version,
        "python_version_info": sys.version_info[:3],
        "free_threading_available": is_free_threading_available(),
        "gil_enabled": is_gil_enabled(),
        "should_use_threads": should_use_threads(),
        "optimal_worker_count": get_optimal_worker_count(),
        "cpu_count": os.cpu_count(),
    }


def log_runtime_info() -> None:
    """
    Log comprehensive runtime information at INFO level.
    
    This should be called during application initialization to help with
    debugging and understanding the execution environment.
    """
    info = get_runtime_info()
    
    logger.info("=" * 60)
    logger.info("Python Runtime Information")
    logger.info("=" * 60)
    logger.info(f"Python Version: {info['python_version_info']}")
    logger.info(f"Free-threading Available: {info['free_threading_available']}")
    logger.info(f"GIL Enabled: {info['gil_enabled']}")
    logger.info(f"CPU Count: {info['cpu_count']}")
    logger.info(f"Optimal Worker Count: {info['optimal_worker_count']}")
    logger.info(f"Should Use Threads: {info['should_use_threads']}")
    
    if info['free_threading_available'] and not info['gil_enabled']:
        logger.info("✓ Running in free-threaded mode (GIL disabled)")
        logger.info("  ThreadPoolExecutor will provide true parallelism")
    elif info['free_threading_available'] and info['gil_enabled']:
        logger.warning("⚠ Free-threaded build detected, but GIL is enabled")
        logger.warning("  An extension module may have re-enabled the GIL")
        logger.warning("  ThreadPoolExecutor will still be used (with GIL protection)")
    else:
        logger.info("ℹ Running in standard GIL-enabled mode")
        logger.info("  ProcessPoolExecutor will be used for parallelism")
    
    logger.info("=" * 60)


def check_gil_reenablement(initial_gil_status: bool) -> Tuple[bool, bool]:
    """
    Check if the GIL status has changed since initialization.
    
    This is useful for detecting when an imported module has re-enabled
    the GIL in a free-threaded build.
    
    Args:
        initial_gil_status: The GIL status at initialization time
    
    Returns:
        Tuple[bool, bool]: (current_gil_status, gil_was_reenabled)
    """
    current_gil_status = is_gil_enabled()
    gil_was_reenabled = (not initial_gil_status) and current_gil_status
    
    if gil_was_reenabled:
        logger.warning("⚠ GIL was re-enabled during execution!")
        logger.warning("  This typically happens when importing an incompatible C extension")
        logger.warning("  Performance may be impacted, but execution will continue safely")
    
    return current_gil_status, gil_was_reenabled


# Example usage and self-test
if __name__ == "__main__":
    # Configure logging for self-test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Display runtime information
    log_runtime_info()
    
    # Test functions
    print("\nFunction Tests:")
    print(f"is_free_threading_available(): {is_free_threading_available()}")
    print(f"is_gil_enabled(): {is_gil_enabled()}")
    print(f"should_use_threads(): {should_use_threads()}")
    print(f"get_optimal_worker_count(): {get_optimal_worker_count()}")
    
    # Test GIL re-enablement detection
    initial_gil = is_gil_enabled()
    current_gil, reenabled = check_gil_reenablement(initial_gil)
    print("\nGIL Status Check:")
    print(f"Initial GIL enabled: {initial_gil}")
    print(f"Current GIL enabled: {current_gil}")
    print(f"GIL was re-enabled: {reenabled}")
