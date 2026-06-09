"""Retry decorator with exponential backoff for resilient API calls."""

import functools
import time
from typing import Any, Callable, TypeVar

from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    backoff: float = 2.0,
) -> Callable[[F], F]:
    """
    Decorator that retries a function with exponential backoff on exception.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Initial delay in seconds between retries (default: 1.0)
        backoff: Multiplier for delay after each failed attempt (default: 2.0)

    Returns:
        Decorated function that retries on exception

    Example:
        @retry(max_attempts=3, base_delay=1.0, backoff=2.0)
        def fetch_data():
            return api.get_data()

        # First attempt: immediate
        # Second attempt: after 1.0s delay
        # Third attempt: after 2.0s delay
        # Raises exception if all attempts fail
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = base_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info(
                        f"Attempt {attempt}/{max_attempts} for {func.__name__}"
                    )
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        logger.info(
                            f"{func.__name__} succeeded on attempt {attempt}"
                        )
                    return result
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"Attempt {attempt} failed for {func.__name__}: "
                            f"{type(e).__name__}: {str(e)}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )

            # Re-raise the last exception if all attempts failed
            if last_exception:
                raise last_exception

        return wrapper  # type: ignore

    return decorator
