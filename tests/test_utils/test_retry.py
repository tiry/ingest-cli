"""Tests for the retry decorator and error classification."""

from unittest.mock import patch

import pytest

from ingest_cli.api.exceptions import (
    APIError,
    AuthenticationError,
    PermanentError,
    RateLimitError,
    ServerError,
    TransientError,
    ValidationError,
)
from ingest_cli.utils.retry import RetryConfig, classify_http_error, retry


class TestRetryConfig:
    """Test suite for RetryConfig."""

    def test_default_config(self) -> None:
        """Test default retry config values."""
        config = RetryConfig()
        assert config.max_retries == 1
        assert config.backoff_seconds == 2.0
        assert config.backoff_multiplier == 2.0
        assert TransientError in config.retry_on

    def test_custom_config(self) -> None:
        """Test custom retry config."""
        config = RetryConfig(
            max_retries=5,
            backoff_seconds=1.0,
            backoff_multiplier=1.5,
            retry_on=(ValueError, RuntimeError),
        )
        assert config.max_retries == 5
        assert config.backoff_seconds == 1.0
        assert config.backoff_multiplier == 1.5
        assert config.should_retry(ValueError("test"))
        assert config.should_retry(RuntimeError("test"))
        assert not config.should_retry(TransientError("test"))

    def test_should_retry_transient(self) -> None:
        """Test should_retry returns True for transient errors."""
        config = RetryConfig()
        assert config.should_retry(TransientError("test"))
        assert config.should_retry(ServerError("test", 500))
        assert config.should_retry(RateLimitError("test", 429))

    def test_should_not_retry_permanent(self) -> None:
        """Test should_retry returns False for permanent errors."""
        config = RetryConfig()
        assert not config.should_retry(PermanentError("test"))
        assert not config.should_retry(ValidationError("test"))
        assert not config.should_retry(AuthenticationError("test"))


class TestRetryDecorator:
    """Test suite for retry decorator."""

    def test_retry_succeeds_first_try(self) -> None:
        """Test no retry when function succeeds first time."""
        call_count = 0

        @retry(RetryConfig(max_retries=3, backoff_seconds=0.01))
        def always_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = always_succeeds()
        assert result == "success"
        assert call_count == 1

    @patch("ingest_cli.utils.retry.time.sleep")
    def test_retry_succeeds_after_transient(self, mock_sleep) -> None:
        """Test retry succeeds after transient failure."""
        call_count = 0

        @retry(RetryConfig(max_retries=3, backoff_seconds=0.01))
        def fails_then_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TransientError("temporary failure")
            return "success"

        result = fails_then_succeeds()
        assert result == "success"
        assert call_count == 2
        assert mock_sleep.called

    @patch("ingest_cli.utils.retry.time.sleep")
    def test_retry_exhausted(self, mock_sleep) -> None:
        """Test raises after max retries exhausted."""
        call_count = 0

        @retry(RetryConfig(max_retries=2, backoff_seconds=0.01))
        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise TransientError("always fails")

        with pytest.raises(TransientError, match="always fails"):
            always_fails()

        # Initial call + 2 retries = 3 total calls
        assert call_count == 3

    def test_retry_permanent_error(self) -> None:
        """Test no retry on permanent error."""
        call_count = 0

        @retry(RetryConfig(max_retries=3, backoff_seconds=0.01))
        def permanent_failure() -> str:
            nonlocal call_count
            call_count += 1
            raise ValidationError("permanent error")

        with pytest.raises(ValidationError, match="permanent error"):
            permanent_failure()

        # Only one attempt - no retry for permanent errors
        assert call_count == 1

    def test_retry_non_retryable_exception(self) -> None:
        """Test no retry for non-retryable exceptions."""
        call_count = 0

        @retry(RetryConfig(max_retries=3, backoff_seconds=0.01))
        def raises_value_error() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError, match="not retryable"):
            raises_value_error()

        assert call_count == 1

    @patch("ingest_cli.utils.retry.time.sleep")
    def test_retry_backoff_timing(self, mock_sleep) -> None:
        """Test exponential backoff timing."""
        call_count = 0

        @retry(RetryConfig(max_retries=3, backoff_seconds=1.0, backoff_multiplier=2.0))
        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise TransientError("always fails")

        with pytest.raises(TransientError):
            always_fails()

        # Check sleep was called with increasing delays
        # First retry: 1.0s, second: 2.0s, third: 4.0s
        assert mock_sleep.call_count == 3
        calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert calls[0] == 1.0  # First retry: backoff_seconds * 1
        assert calls[1] == 2.0  # Second retry: backoff_seconds * 2
        assert calls[2] == 4.0  # Third retry: backoff_seconds * 4

    @patch("ingest_cli.utils.retry.time.sleep")
    def test_retry_with_retry_after(self, mock_sleep) -> None:
        """Test retry respects retry_after attribute."""
        call_count = 0

        @retry(RetryConfig(max_retries=1, backoff_seconds=1.0))
        def rate_limited() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("rate limited", 429, retry_after=5.0)
            return "success"

        result = rate_limited()
        assert result == "success"

        # Should use max(backoff, retry_after) = 5.0
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == 5.0

    def test_retry_default_config(self) -> None:
        """Test retry with default config when None provided."""
        call_count = 0

        @retry()
        def simple_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = simple_func()
        assert result == "success"
        assert call_count == 1


class TestClassifyHttpError:
    """Test suite for HTTP error classification."""

    def test_classify_429_rate_limit(self) -> None:
        """Test HTTP 429 classified as RateLimitError."""
        error = classify_http_error(429, retry_after=30.0)
        assert isinstance(error, RateLimitError)
        assert error.status_code == 429
        assert error.retry_after == 30.0

    def test_classify_500_server_error(self) -> None:
        """Test HTTP 500 classified as ServerError."""
        error = classify_http_error(500)
        assert isinstance(error, ServerError)
        assert error.status_code == 500

    def test_classify_502_server_error(self) -> None:
        """Test HTTP 502 classified as ServerError."""
        error = classify_http_error(502)
        assert isinstance(error, ServerError)
        assert error.status_code == 502

    def test_classify_503_server_error(self) -> None:
        """Test HTTP 503 classified as ServerError."""
        error = classify_http_error(503)
        assert isinstance(error, ServerError)
        assert error.status_code == 503

    def test_classify_504_server_error(self) -> None:
        """Test HTTP 504 classified as ServerError."""
        error = classify_http_error(504)
        assert isinstance(error, ServerError)
        assert error.status_code == 504

    def test_classify_401_auth_error(self) -> None:
        """Test HTTP 401 classified as AuthenticationError."""
        error = classify_http_error(401)
        assert isinstance(error, AuthenticationError)

    def test_classify_403_auth_error(self) -> None:
        """Test HTTP 403 classified as AuthenticationError."""
        error = classify_http_error(403)
        assert isinstance(error, AuthenticationError)

    def test_classify_400_validation_error(self) -> None:
        """Test HTTP 400 classified as ValidationError."""
        error = classify_http_error(400)
        assert isinstance(error, ValidationError)
        assert error.status_code == 400

    def test_classify_422_validation_error(self) -> None:
        """Test HTTP 422 classified as ValidationError."""
        error = classify_http_error(422)
        assert isinstance(error, ValidationError)

    def test_classify_unknown_error(self) -> None:
        """Test unknown status codes get generic APIError."""
        error = classify_http_error(418)  # I'm a teapot
        assert isinstance(error, APIError)
        assert error.status_code == 418


class TestTransientVsPermanent:
    """Test suite for transient vs permanent error classification."""

    def test_transient_errors_are_retryable(self) -> None:
        """Test TransientError subclasses are retryable."""
        config = RetryConfig()

        # All transient errors should be retryable
        assert config.should_retry(TransientError("test"))
        assert config.should_retry(ServerError("test", 500))
        assert config.should_retry(RateLimitError("test", 429))

    def test_permanent_errors_not_retryable(self) -> None:
        """Test PermanentError subclasses are not retryable by default."""
        config = RetryConfig()

        # Permanent errors should not be retryable by default
        assert not config.should_retry(PermanentError("test"))
        assert not config.should_retry(ValidationError("test"))

    def test_server_error_inherits_transient(self) -> None:
        """Test ServerError is a TransientError."""
        error = ServerError("test", 500)
        assert isinstance(error, TransientError)
        assert isinstance(error, APIError)

    def test_rate_limit_error_inherits_transient(self) -> None:
        """Test RateLimitError is a TransientError."""
        error = RateLimitError("test", 429)
        assert isinstance(error, TransientError)
        assert isinstance(error, APIError)

    def test_validation_error_inherits_permanent(self) -> None:
        """Test ValidationError is a PermanentError."""
        error = ValidationError("test")
        assert isinstance(error, PermanentError)
        assert isinstance(error, APIError)
