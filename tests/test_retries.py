"""Tests for retry decorator with exponential backoff."""

import time
from unittest.mock import MagicMock, patch

import pytest

from smart_money_tracker.utils.retries import retry


class TestRetryDecorator:
    """Test suite for the retry decorator."""

    def test_successful_call_no_retries(self):
        """Test that successful call returns immediately without retries."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, backoff=2.0)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()

        assert result == "success"
        assert call_count == 1

    def test_retry_on_exception(self):
        """Test that retry decorator retries on exception."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, backoff=2.0)
        def failing_then_succeeding():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = failing_then_succeeding()

        assert result == "success"
        assert call_count == 3

    def test_raises_exception_after_max_attempts(self):
        """Test that exception is raised after all attempts are exhausted."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, backoff=2.0)
        def always_failing():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_failing()

        assert call_count == 3

    def test_exponential_backoff_delays(self):
        """Test that exponential backoff increases delay correctly."""
        call_count = 0
        call_times = []

        @retry(max_attempts=4, base_delay=0.05, backoff=2.0)
        def failing_function():
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            if call_count < 4:
                raise ValueError("Failure")
            return "success"

        result = failing_function()

        assert result == "success"
        assert call_count == 4
        assert len(call_times) == 4

        # Calculate actual delays between attempts
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        delay3 = call_times[3] - call_times[2]

        # With base_delay=0.05 and backoff=2.0:
        # delay1 should be ~0.05
        # delay2 should be ~0.1 (0.05 * 2)
        # delay3 should be ~0.2 (0.1 * 2)
        # Allow some tolerance for timing variations
        assert 0.03 < delay1 < 0.15  # ~0.05
        assert 0.08 < delay2 < 0.25  # ~0.1
        assert 0.15 < delay3 < 0.35  # ~0.2

    def test_retry_with_custom_max_attempts(self):
        """Test retry decorator with custom max_attempts."""
        call_count = 0

        @retry(max_attempts=5, base_delay=0.01, backoff=2.0)
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Failure")

        with pytest.raises(ValueError):
            failing_function()

        assert call_count == 5

    def test_retry_with_custom_base_delay(self):
        """Test retry decorator with custom base_delay."""
        call_count = 0
        start_time = time.time()

        @retry(max_attempts=2, base_delay=0.05, backoff=2.0)
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Failure")

        with pytest.raises(ValueError):
            failing_function()

        elapsed = time.time() - start_time

        # Should have at least base_delay seconds passed
        assert elapsed >= 0.04  # Allow some tolerance
        assert call_count == 2

    def test_retry_with_custom_backoff(self):
        """Test retry decorator with custom backoff multiplier."""
        call_count = 0
        call_times = []

        @retry(max_attempts=3, base_delay=0.02, backoff=3.0)
        def failing_function():
            nonlocal call_count
            call_times.append(time.time())
            call_count += 1
            if call_count < 3:
                raise ValueError("Failure")
            return "success"

        result = failing_function()

        assert result == "success"
        assert call_count == 3

        # Calculate delays
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # With base_delay=0.02 and backoff=3.0:
        # delay1 should be ~0.02
        # delay2 should be ~0.06 (0.02 * 3)
        assert 0.01 < delay1 < 0.1
        assert 0.04 < delay2 < 0.15

    def test_function_metadata_preserved(self):
        """Test that functools.wraps preserves function metadata."""

        @retry(max_attempts=3, base_delay=0.01, backoff=2.0)
        def documented_function():
            """This is a documented function."""
            return "result"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a documented function."

    def test_retry_with_different_exception_types(self):
        """Test that retry works with different exception types."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, backoff=2.0)
        def raising_different_exceptions():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First error")
            elif call_count == 2:
                raise RuntimeError("Second error")
            return "success"

        result = raising_different_exceptions()

        assert result == "success"
        assert call_count == 3

    @patch("smart_money_tracker.utils.retries.logger")
    def test_logging_on_retry(self, mock_logger):
        """Test that retry decorator logs attempts and failures."""
        call_count = 0

        @retry(max_attempts=2, base_delay=0.01, backoff=2.0)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = failing_function()

        assert result == "success"
        # Verify logging was called
        assert mock_logger.info.called
        assert mock_logger.warning.called

    def test_retry_with_function_arguments(self):
        """Test that retry decorator works with function arguments."""
        call_count = 0

        @retry(max_attempts=3, base_delay=0.01, backoff=2.0)
        def function_with_args(a, b, c=None):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Failure")
            return a + b + (c if c else 0)

        result = function_with_args(1, 2, c=3)

        assert result == 6
        assert call_count == 3

    def test_retry_preserves_exception_type(self):
        """Test that the original exception type is preserved and re-raised."""

        @retry(max_attempts=2, base_delay=0.01, backoff=2.0)
        def always_failing():
            raise RuntimeError("Original error message")

        with pytest.raises(RuntimeError) as exc_info:
            always_failing()

        assert str(exc_info.value) == "Original error message"

    def test_single_attempt_success(self):
        """Test with max_attempts=1 that succeeds immediately."""
        call_count = 0

        @retry(max_attempts=1, base_delay=0.01, backoff=2.0)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()

        assert result == "success"
        assert call_count == 1

    def test_single_attempt_failure(self):
        """Test with max_attempts=1 that fails immediately."""
        call_count = 0

        @retry(max_attempts=1, base_delay=0.01, backoff=2.0)
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Failure")

        with pytest.raises(ValueError):
            failing_function()

        assert call_count == 1
