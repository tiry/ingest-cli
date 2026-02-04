"""API-specific exceptions."""

from __future__ import annotations


class APIError(Exception):
    """Base exception for API errors.

    This is the base class for all API-related exceptions.
    """

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            status_code: HTTP status code if available.
        """
        self.status_code = status_code
        super().__init__(message or "API error occurred")


# ============================================================================
# Transient Errors (may succeed on retry)
# ============================================================================


class TransientError(APIError):
    """Base class for errors that may succeed on retry.

    These are temporary failures that might resolve if retried.
    """

    pass


class RateLimitError(TransientError):
    """Rate limit exceeded (HTTP 429).

    Server has rate-limited the request. Check retry_after for
    recommended wait time.
    """

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            status_code: HTTP status code.
            retry_after: Recommended wait time before retry.
        """
        self.retry_after = retry_after

        if message is None:
            message = "Rate limit exceeded"
            if retry_after:
                message += f" (retry after {retry_after}s)"

        super().__init__(message, status_code or 429)


class ServerError(TransientError):
    """Server-side error (HTTP 5xx).

    The server encountered an error processing the request.
    May succeed on retry.
    """

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
    ) -> None:
        if message is None:
            message = f"Server error (HTTP {status_code or 500})"
        super().__init__(message, status_code or 500)


class ConnectionError(TransientError):
    """Connection error (network issue).

    Could not establish connection to the server.
    May succeed on retry.
    """

    def __init__(
        self,
        message: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        self.cause = cause

        if message is None:
            if cause:
                message = f"Connection error: {cause}"
            else:
                message = "Connection error occurred"

        super().__init__(message, None)


# ============================================================================
# Permanent Errors (will not succeed on retry)
# ============================================================================


class PermanentError(APIError):
    """Base class for errors that will not succeed on retry.

    These are failures due to invalid requests, authentication,
    or other issues that won't be resolved by retrying.
    """

    pass


class ValidationError(PermanentError):
    """Request validation failed (HTTP 400, 422).

    The request is malformed or invalid.
    """

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        validation_errors: list[dict] | None = None,
    ) -> None:
        self.validation_errors = validation_errors

        if message is None:
            message = "Validation error"

        super().__init__(message, status_code or 400)


class AuthenticationError(PermanentError):
    """Base exception for authentication errors.

    Raised when there is any issue with authentication.
    """

    pass


class InvalidCredentialsError(AuthenticationError):
    """Client credentials are invalid.

    Raised when the OAuth2 token request fails due to
    invalid client_id or client_secret.
    """

    def __init__(self, message: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Optional custom message.
        """
        if message is None:
            message = "Invalid client credentials"
        super().__init__(message)


class TokenRequestError(AuthenticationError):
    """Token request failed.

    Raised when the token request fails for reasons
    other than invalid credentials (network errors, etc.).
    """

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            status_code: HTTP status code if available.
            error_code: OAuth2 error code if available.
        """
        self.error_code = error_code

        if message is None:
            if error_code:
                message = f"Token request failed: {error_code}"
            elif status_code:
                message = f"Token request failed with status {status_code}"
            else:
                message = "Token request failed"

        super().__init__(message, status_code)


class TokenExpiredError(AuthenticationError):
    """Access token has expired.

    Raised when attempting to use an expired token.
    """

    def __init__(self, message: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Optional custom message.
        """
        if message is None:
            message = "Access token has expired"
        super().__init__(message)


class NetworkError(APIError):
    """Network-related error.

    Raised when there is a network connectivity issue.
    """

    def __init__(self, message: str | None = None, cause: Exception | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            cause: The underlying exception that caused this error.
        """
        self.cause = cause

        if message is None:
            if cause:
                message = f"Network error: {cause}"
            else:
                message = "Network error occurred"

        super().__init__(message)


# ============================================================================
# Ingestion API Exceptions
# ============================================================================


class IngestionError(APIError):
    """Base exception for ingestion API errors."""

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            status_code: HTTP status code if available.
        """
        super().__init__(message or "Ingestion error occurred", status_code)


class PresignedUrlError(IngestionError):
    """Failed to obtain presigned URLs for file upload.

    Raised when the /v1/presigned-urls endpoint fails.
    """

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
    ) -> None:
        if message is None:
            message = "Failed to obtain presigned URLs"
        super().__init__(message, status_code)


class FileUploadError(IngestionError):
    """Failed to upload file to presigned URL.

    Raised when file upload to S3 fails.
    """

    def __init__(
        self,
        message: str | None = None,
        file_path: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.file_path = file_path

        if message is None:
            if file_path:
                message = f"Failed to upload file: {file_path}"
            else:
                message = "Failed to upload file"

        super().__init__(message, status_code)


class EventSendError(IngestionError):
    """Failed to send ingestion events.

    Raised when the /v2/ingestion-events endpoint fails.
    """

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        error_details: dict | None = None,
    ) -> None:
        self.error_details = error_details

        if message is None:
            message = "Failed to send ingestion events"

        super().__init__(message, status_code)
