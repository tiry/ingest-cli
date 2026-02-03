"""API-specific exceptions."""


class APIError(Exception):
    """Base exception for API errors.

    This is the base class for all API-related exceptions.
    """

    pass


class AuthenticationError(APIError):
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
        self.status_code = status_code
        self.error_code = error_code

        if message is None:
            if error_code:
                message = f"Token request failed: {error_code}"
            elif status_code:
                message = f"Token request failed with status {status_code}"
            else:
                message = "Token request failed"

        super().__init__(message)


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
