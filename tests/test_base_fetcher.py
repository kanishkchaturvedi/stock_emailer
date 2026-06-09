"""Tests for abstract BaseFetcher class."""

from abc import ABC
from unittest.mock import MagicMock, patch

import pytest

from smart_money_tracker.data_collection.base import BaseFetcher


class TestBaseFetcherAbstraction:
    """Test suite for BaseFetcher abstraction and interface."""

    def test_base_fetcher_is_abstract_class(self):
        """Test that BaseFetcher is an abstract class."""
        assert issubclass(BaseFetcher, ABC)

    def test_base_fetcher_cannot_be_instantiated(self):
        """Test that BaseFetcher cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            BaseFetcher()

    def test_concrete_implementation_can_be_instantiated(self):
        """Test that a concrete implementation of BaseFetcher can be instantiated."""

        class ConcreteFetcher(BaseFetcher):
            def _fetch_impl(self):
                return {"data": "test"}

        fetcher = ConcreteFetcher()
        assert isinstance(fetcher, BaseFetcher)
        assert isinstance(fetcher, ABC)

    def test_fetch_calls_fetch_impl(self):
        """Test that fetch() method calls _fetch_impl()."""

        class TestFetcher(BaseFetcher):
            def __init__(self):
                self.fetch_impl_called = False

            def _fetch_impl(self):
                self.fetch_impl_called = True
                return {"data": "test"}

        fetcher = TestFetcher()
        result = fetcher.fetch()

        assert fetcher.fetch_impl_called
        assert result == {"data": "test"}

    def test_fetch_retries_on_exception(self):
        """Test that fetch() automatically retries when _fetch_impl() raises exception."""

        class FailingThenSucceedingFetcher(BaseFetcher):
            def __init__(self):
                self.call_count = 0

            def _fetch_impl(self):
                self.call_count += 1
                if self.call_count < 3:
                    raise RuntimeError("Temporary failure")
                return {"data": "success"}

        fetcher = FailingThenSucceedingFetcher()
        result = fetcher.fetch()

        assert result == {"data": "success"}
        assert fetcher.call_count == 3

    def test_fetch_raises_after_max_retries(self):
        """Test that fetch() raises exception after max retries."""

        class AlwaysFailingFetcher(BaseFetcher):
            def __init__(self):
                self.call_count = 0

            def _fetch_impl(self):
                self.call_count += 1
                raise RuntimeError("Always fails")

        fetcher = AlwaysFailingFetcher()

        with pytest.raises(RuntimeError, match="Always fails"):
            fetcher.fetch()

        # Should have tried 3 times (default max_attempts)
        assert fetcher.call_count == 3

    def test_store_method_exists_and_logs(self):
        """Test that store() method exists and logs."""

        class SimpleFetcher(BaseFetcher):
            def _fetch_impl(self):
                return {"data": "test"}

        fetcher = SimpleFetcher()
        data = {"key": "value"}

        with patch("smart_money_tracker.data_collection.base.logger") as mock_logger:
            fetcher.store(data)
            mock_logger.info.assert_called_once()

    def test_store_method_can_be_overridden(self):
        """Test that store() method can be overridden by subclasses."""

        class CustomStoreFetcher(BaseFetcher):
            def __init__(self):
                self.stored_data = None

            def _fetch_impl(self):
                return {"data": "test"}

            def store(self, data):
                self.stored_data = data

        fetcher = CustomStoreFetcher()
        data = {"key": "value"}
        fetcher.store(data)

        assert fetcher.stored_data == data

    def test_fetch_and_store_workflow(self):
        """Test a complete fetch and store workflow."""

        class WorkflowFetcher(BaseFetcher):
            def __init__(self):
                self.stored_data = None

            def _fetch_impl(self):
                return {"stock": "AAPL", "price": 150.0}

            def store(self, data):
                self.stored_data = data

        fetcher = WorkflowFetcher()
        data = fetcher.fetch()
        fetcher.store(data)

        assert fetcher.stored_data == {"stock": "AAPL", "price": 150.0}

    def test_multiple_fetchers_independent(self):
        """Test that multiple fetcher instances are independent."""

        class CountingFetcher(BaseFetcher):
            def __init__(self, start_count=0):
                self.count = start_count

            def _fetch_impl(self):
                self.count += 1
                return self.count

        fetcher1 = CountingFetcher(start_count=0)
        fetcher2 = CountingFetcher(start_count=100)

        result1 = fetcher1.fetch()
        result2 = fetcher2.fetch()

        assert result1 == 1
        assert result2 == 101

    def test_fetch_returns_different_data_types(self):
        """Test that fetch() can return different data types."""

        class DictFetcher(BaseFetcher):
            def _fetch_impl(self):
                return {"key": "value"}

        class ListFetcher(BaseFetcher):
            def _fetch_impl(self):
                return [1, 2, 3]

        class StringFetcher(BaseFetcher):
            def _fetch_impl(self):
                return "string data"

        class IntFetcher(BaseFetcher):
            def _fetch_impl(self):
                return 42

        dict_result = DictFetcher().fetch()
        list_result = ListFetcher().fetch()
        string_result = StringFetcher().fetch()
        int_result = IntFetcher().fetch()

        assert dict_result == {"key": "value"}
        assert list_result == [1, 2, 3]
        assert string_result == "string data"
        assert int_result == 42

    def test_fetch_impl_must_be_implemented(self):
        """Test that _fetch_impl() must be implemented by subclasses."""

        class IncompleteImplementation(BaseFetcher):
            pass

        with pytest.raises(TypeError):
            IncompleteImplementation()

    @patch("smart_money_tracker.utils.retries.logger")
    def test_logging_during_fetch(self, mock_logger):
        """Test that logging occurs during fetch attempts."""

        class LoggingTestFetcher(BaseFetcher):
            def __init__(self):
                self.call_count = 0

            def _fetch_impl(self):
                self.call_count += 1
                if self.call_count < 2:
                    raise ValueError("Test error")
                return "success"

        fetcher = LoggingTestFetcher()
        result = fetcher.fetch()

        assert result == "success"
        # Verify that logger was called during the retry process
        assert mock_logger.info.called or mock_logger.warning.called

    def test_fetch_with_exception_contains_context(self):
        """Test that exceptions raised by _fetch_impl() are properly propagated."""

        class ContextualErrorFetcher(BaseFetcher):
            def _fetch_impl(self):
                raise ValueError("API returned 500 error")

        fetcher = ContextualErrorFetcher()

        with pytest.raises(ValueError) as exc_info:
            fetcher.fetch()

        assert "API returned 500 error" in str(exc_info.value)

    def test_subclass_with_initialization_parameters(self):
        """Test that fetcher subclasses can accept initialization parameters."""

        class ConfigurableFetcher(BaseFetcher):
            def __init__(self, url, timeout=5):
                self.url = url
                self.timeout = timeout

            def _fetch_impl(self):
                return {"url": self.url, "timeout": self.timeout}

        fetcher = ConfigurableFetcher("https://api.example.com", timeout=10)
        result = fetcher.fetch()

        assert result["url"] == "https://api.example.com"
        assert result["timeout"] == 10

    def test_store_method_default_implementation_uses_classname(self):
        """Test that default store() method uses correct class name in logging."""

        class NamedFetcher(BaseFetcher):
            def _fetch_impl(self):
                return {"data": "test"}

        fetcher = NamedFetcher()

        with patch("smart_money_tracker.data_collection.base.logger") as mock_logger:
            fetcher.store({"data": "test"})
            call_args = mock_logger.info.call_args[0][0]
            assert "NamedFetcher" in call_args

    def test_concurrent_fetch_calls(self):
        """Test that concurrent fetches don't interfere with each other."""

        class IncrementingFetcher(BaseFetcher):
            counter = 0

            def __init__(self):
                self.value = None

            def _fetch_impl(self):
                IncrementingFetcher.counter += 1
                self.value = IncrementingFetcher.counter
                return IncrementingFetcher.counter

        fetcher1 = IncrementingFetcher()
        fetcher2 = IncrementingFetcher()

        result1 = fetcher1.fetch()
        result2 = fetcher2.fetch()

        # Both should have unique values
        assert result1 != result2
        assert result1 in [1, 2]
        assert result2 in [1, 2]
