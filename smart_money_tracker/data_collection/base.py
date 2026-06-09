"""Abstract base class for data fetchers with automatic retry logic."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from smart_money_tracker.utils.logger import get_logger
from smart_money_tracker.utils.retries import retry

logger = get_logger(__name__)


class BaseFetcher(ABC):
    """
    Abstract base class for all data sources.

    This class provides a template for implementing data fetchers with automatic
    retry logic and error handling. Subclasses must implement the _fetch_impl()
    method which contains the actual data fetching logic.

    Pattern:
        1. fetch() is called (public interface)
        2. fetch() calls _fetch_impl() with retry decorator
        3. _fetch_impl() contains the actual fetching logic
        4. On success, data is returned
        5. On failure, retry decorator handles retries with exponential backoff
        6. After all retries exhausted, exception is raised

    Example:
        class StockDataFetcher(BaseFetcher):
            def _fetch_impl(self) -> Dict[str, Any]:
                response = requests.get("https://api.example.com/stocks")
                response.raise_for_status()
                return response.json()

            @BaseFetcher.store()
            def store(self, data: Dict[str, Any]) -> None:
                # Custom storage logic
                pass

        fetcher = StockDataFetcher()
        data = fetcher.fetch()  # Automatically retries on failure
    """

    @retry(max_attempts=3, base_delay=1.0, backoff=2.0)
    def fetch(self) -> Any:
        """
        Fetch data with automatic retry logic.

        This method wraps _fetch_impl() with exponential backoff retry logic.
        On success, it returns the result immediately. On failure, it retries
        automatically according to the retry configuration.

        Returns:
            Data from _fetch_impl()

        Raises:
            Exception: After all retry attempts are exhausted
        """
        return self._fetch_impl()

    @abstractmethod
    def _fetch_impl(self) -> Any:
        """
        Implement the actual data fetching logic.

        This method must be implemented by subclasses. It contains the actual
        logic for fetching data from the data source (API, database, file, etc).

        Returns:
            Fetched data (type depends on implementation)

        Raises:
            Exception: Any exception raised here will trigger retry logic
        """
        pass

    def store(self, data: Any) -> None:
        """
        Store fetched data (optional).

        This method can be overridden by subclasses to implement custom storage
        logic. The base implementation just logs that data was stored.

        Args:
            data: The data to store
        """
        logger.info(
            f"Storing data from {self.__class__.__name__}: "
            f"{type(data).__name__} object"
        )
