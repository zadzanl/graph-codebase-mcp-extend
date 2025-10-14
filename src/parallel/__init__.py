"""Parallel processing utilities package."""

from src.parallel.pool_manager import (
    ProcessingPoolManager,
    get_processing_pool,
)

__all__ = [
    'ProcessingPoolManager',
    'get_processing_pool',
]
