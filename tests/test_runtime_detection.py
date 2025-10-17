"""
Unit tests for runtime detection utilities.
"""

import os
import pytest
from unittest.mock import patch
from src.utils.runtime_detection import (
    is_free_threading_available,
    is_gil_enabled,
    should_use_threads,
    get_optimal_worker_count,
    get_runtime_info,
    check_gil_reenablement,
)


class TestRuntimeDetection:
    """Test suite for runtime detection utilities."""
    
    def test_is_free_threading_available_standard_build(self):
        """Test detection on standard GIL-enabled Python build."""
        # On standard Python builds, Py_GIL_DISABLED should not be 1
        result = is_free_threading_available()
        assert isinstance(result, bool)
        # For most environments, this will be False unless running on Python 3.14t
    
    def test_is_gil_enabled_standard_python(self):
        """Test GIL status detection on standard Python."""
        result = is_gil_enabled()
        assert isinstance(result, bool)
        # Standard Python always has GIL enabled
        assert result is True
    
    def test_should_use_threads_standard_python(self):
        """Test executor selection on standard Python."""
        result = should_use_threads()
        assert isinstance(result, bool)
        # Standard Python should use ProcessPoolExecutor (return False)
        # unless it's a free-threaded build with GIL disabled
    
    def test_get_optimal_worker_count_default(self):
        """Test optimal worker count calculation with defaults."""
        result = get_optimal_worker_count()
        assert isinstance(result, int)
        assert result >= 1
        # Should be min(cpu_count, 8)
        cpu_count = os.cpu_count() or 4
        assert result == min(cpu_count, 8)
    
    def test_get_optimal_worker_count_explicit(self):
        """Test optimal worker count with explicit value."""
        result = get_optimal_worker_count(max_workers=4)
        assert result == 4
        
        result = get_optimal_worker_count(max_workers=16)
        assert result == 16
        
        # Should handle 0 or negative gracefully
        result = get_optimal_worker_count(max_workers=0)
        assert result == 1
        
        result = get_optimal_worker_count(max_workers=-5)
        assert result == 1
    
    @patch.dict(os.environ, {'MAX_WORKERS': '12'})
    def test_get_optimal_worker_count_from_env(self):
        """Test optimal worker count from environment variable."""
        result = get_optimal_worker_count()
        assert result == 12
    
    @patch.dict(os.environ, {'MAX_WORKERS': 'invalid'})
    def test_get_optimal_worker_count_invalid_env(self):
        """Test optimal worker count with invalid environment variable."""
        result = get_optimal_worker_count()
        # Should fall back to default calculation
        assert isinstance(result, int)
        assert result >= 1
    
    def test_get_runtime_info(self):
        """Test comprehensive runtime information gathering."""
        info = get_runtime_info()
        
        # Verify all expected keys are present
        assert 'python_version' in info
        assert 'python_version_info' in info
        assert 'free_threading_available' in info
        assert 'gil_enabled' in info
        assert 'should_use_threads' in info
        assert 'optimal_worker_count' in info
        assert 'cpu_count' in info
        
        # Verify types
        assert isinstance(info['python_version'], str)
        assert isinstance(info['python_version_info'], tuple)
        assert isinstance(info['free_threading_available'], bool)
        assert isinstance(info['gil_enabled'], bool)
        assert isinstance(info['should_use_threads'], bool)
        assert isinstance(info['optimal_worker_count'], int)
        assert info['optimal_worker_count'] >= 1
    
    def test_check_gil_reenablement_no_change(self):
        """Test GIL re-enablement detection when GIL status unchanged."""
        initial_gil = is_gil_enabled()
        current_gil, reenabled = check_gil_reenablement(initial_gil)
        
        assert isinstance(current_gil, bool)
        assert isinstance(reenabled, bool)
        assert current_gil == is_gil_enabled()
        # In most cases, GIL won't change during test
        assert reenabled is False
    
    def test_check_gil_reenablement_detected(self):
        """Test GIL re-enablement detection when GIL is re-enabled."""
        # Simulate initial state with GIL disabled
        initial_gil = False
        
        # On standard Python, GIL is always enabled
        current_gil, reenabled = check_gil_reenablement(initial_gil)
        
        if current_gil:
            # If current GIL is enabled and initial was disabled, should detect
            assert reenabled is True
        else:
            assert reenabled is False


class TestRuntimeDetectionMocked:
    """Test suite with mocked sysconfig and sys for comprehensive coverage."""
    
    @patch('src.utils.runtime_detection.sysconfig.get_config_var')
    def test_is_free_threading_available_mocked_enabled(self, mock_get_config):
        """Test free-threading detection with mocked enabled state."""
        mock_get_config.return_value = 1
        assert is_free_threading_available() is True
        mock_get_config.assert_called_once_with("Py_GIL_DISABLED")
    
    @patch('src.utils.runtime_detection.sysconfig.get_config_var')
    def test_is_free_threading_available_mocked_disabled(self, mock_get_config):
        """Test free-threading detection with mocked disabled state."""
        mock_get_config.return_value = 0
        assert is_free_threading_available() is False
        mock_get_config.assert_called_once_with("Py_GIL_DISABLED")
    
    @patch('src.utils.runtime_detection.sysconfig.get_config_var')
    @patch('src.utils.runtime_detection.is_gil_enabled')
    def test_should_use_threads_free_threaded_gil_disabled(
        self, mock_is_gil, mock_get_config
    ):
        """Test executor selection with free-threading and GIL disabled."""
        mock_get_config.return_value = 1
        mock_is_gil.return_value = False
        assert should_use_threads() is True
    
    @patch('src.utils.runtime_detection.sysconfig.get_config_var')
    @patch('src.utils.runtime_detection.is_gil_enabled')
    def test_should_use_threads_free_threaded_gil_enabled(
        self, mock_is_gil, mock_get_config
    ):
        """Test executor selection with free-threading but GIL re-enabled."""
        mock_get_config.return_value = 1
        mock_is_gil.return_value = True
        # Should still use ProcessPoolExecutor when GIL is enabled
        assert should_use_threads() is False
    
    @patch('src.utils.runtime_detection.os.cpu_count')
    def test_get_optimal_worker_count_none_cpu_count(self, mock_cpu_count):
        """Test worker count calculation when cpu_count returns None."""
        mock_cpu_count.return_value = None
        result = get_optimal_worker_count()
        # Should fall back to 4
        assert result == 4


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
