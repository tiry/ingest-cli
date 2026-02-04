"""Retry decorator for handling transient failures."""

from __future__ import annotations

import functools
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

# Type variable for decorated function return type
T = TypeVar("T")


def _get_default_retry_on() -> tuple[type[Exception], ...]:
    """Get default exception types to retry on.

    Returns:
        Tuple containing TransientError from api.exceptions.
    """
    # Import here to avoid circular imports
    from ingest_cli.api.exceptions import TransientError

    return (TransientError,)


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 1).
        backoff_seconds: Base delay between retries (default: 2.0).
        backoff_multiplier: Multiplier for exponential backoff (default: 2.0).
        retry_on: Tuple of exception types to retry on.
    """

    max_retries: int = 1
    backoff_seconds: float = 2.0
    backoff_multiplier: float = 2.0
    retry_on: tuple[type[Exception], ...] = field(
        default_factory=_get_default_retry_on
    )

    def should_retry(self, exception: Exception) -> bool:
        """Check if an exception should trigger a retry.

        Args:
            exception: The exception to check.

        Returns:
            True if the exception type is in retry_on.
        """
        return isinstance(exception, self.retry_on)


def retry(
    config: RetryConfig | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to retry functions on transient errors.

    Args:
        config: Retry configuration. Defaults to RetryConfig().

    Returns:
        Decorated function that retries on specified errors.

    Example:
        @retry(RetryConfig(max_retries=3, backoff_seconds=1.0))
        def call_api():
            # may raise TransientError
            pass
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            attempt = 0

            while attempt <= config.max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Don't retry on permanent errors
                    if not config.should_retry(e):
                        logger.debug(
                            "Not retrying %s: %s is not retryable",
                            func.__name__,
                            type(e).__name__,
                        )
                        raise

                    attempt += 1
                    if attempt > config.max_retries:
                        logger.warning(
                            "Retry exhausted for %s after %d attempts: %s",
                            func.__name__,
                            attempt,
                            str(e),
                        )
                        raise

                    # Calculate backoff with exponential increase
                    delay = config.backoff_seconds * (
                        config.backoff_multiplier ** (attempt - 1)
                    )

                    # Check for retry_after hint
                    if hasattr(e, "retry_after") and e.retry_after:
                        delay = max(delay, e.retry_after)

                    logger.warning(
                        "Retry %d/%d for %s after %s: waiting %.1fs",
                        attempt,
                        config.max_retries,
                        func.__name__,
                        type(e).__name__,
                        delay,
                    )
                    time.sleep(delay)

            # This should not be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Unexpected retry loop exit in {func.__name__}")

        return wrapper

    return decorator


def classify_http_error(status_code: int, retry_after: float | None = None) -> Exception:
    """Classify an HTTP error by status code.

    Args:
        status_code: HTTP status code.
        retry_after: Optional retry-after value from headers.

    Returns:
        Appropriate exception instance.
    """
    # Import here to avoid circular imports
    from ingest_cli.api.exceptions import (
        APIError,
        AuthenticationError,
        RateLimitError,
        ServerError,
        ValidationError,
    )

    if status_code == 429:
        return RateLimitError(
            message="Rate limit exceeded",
            status_code=status_code,
            retry_after=retry_after,
        )
    elif status_code in (500, 502, 503, 504):
        return ServerError(
            message=f"Server error (HTTP {status_code})",
            status_code=status_code,
        )
    elif status_code == 401:
        return AuthenticationError(
            message="Authentication failed",
            status_code=status_code,
        )
    elif status_code == 403:
        return AuthenticationError(
            message="Access forbidden",
            status_code=status_code,
        )
    elif status_code == 400 or status_code == 422:
        return ValidationError(
            message="Validation error",
            status_code=status_code,
        )
    else:
        return APIError(
            message=f"HTTP error {status_code}",
            status_code=status_code,
        )


__all__ = [
    "RetryConfig",
    "retry",
    "classify_http_error",
]
