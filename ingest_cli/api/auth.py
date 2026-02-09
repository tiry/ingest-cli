"""OAuth2 client credentials authentication client."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import httpx

from .exceptions import InvalidCredentialsError, NetworkError, TokenRequestError

if TYPE_CHECKING:
    from ingest_cli.config import IngestSettings


logger = logging.getLogger(__name__)

# Default OAuth2 scopes for HxP external integration API
DEFAULT_SCOPES: list[str] = []

# Buffer time before actual expiration to refresh token (seconds)
TOKEN_EXPIRY_BUFFER = 60


@dataclass
class TokenInfo:
    """Stores OAuth2 token information.

    Attributes:
        access_token: The access token string.
        token_type: Token type (usually "Bearer").
        expires_at: UTC datetime when the token expires.
    """

    access_token: str
    token_type: str
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with buffer).

        Returns:
            True if token is expired or will expire within the buffer period.
        """
        buffer = timedelta(seconds=TOKEN_EXPIRY_BUFFER)
        return datetime.now(timezone.utc) >= self.expires_at - buffer


class AuthClient:
    """OAuth2 client credentials authentication client.

    This client handles obtaining and caching OAuth2 access tokens
    using the client credentials flow.

    Example:
        >>> client = AuthClient(
        ...     client_id="my-client",
        ...     client_secret="my-secret",
        ...     auth_endpoint="https://auth.example.com/token",
        ... )
        >>> token = client.get_token()
        >>> headers = {"Authorization": f"Bearer {token}"}
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        auth_endpoint: str,
        scopes: list[str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the authentication client.

        Args:
            client_id: OAuth2 client ID.
            client_secret: OAuth2 client secret.
            auth_endpoint: Token endpoint URL.
            scopes: List of OAuth2 scopes to request (e.g., ['hxp']).
            timeout: Request timeout in seconds.
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._auth_endpoint = auth_endpoint
        self._scopes = scopes or DEFAULT_SCOPES
        self._timeout = timeout
        self._token: TokenInfo | None = None

    def get_token(self) -> str:
        """Get a valid access token, refreshing if needed.

        Returns:
            The access token string.

        Raises:
            InvalidCredentialsError: If client credentials are invalid.
            TokenRequestError: If token request fails.
            NetworkError: If there's a network connectivity issue.
        """
        if self._token is None or self._token.is_expired:
            logger.debug("Token is missing or expired, requesting new token")
            self._token = self._request_token()

        return self._token.access_token

    def _request_token(self) -> TokenInfo:
        """Request a new token from the auth endpoint.

        Returns:
            TokenInfo with the new token.

        Raises:
            InvalidCredentialsError: If client credentials are invalid.
            TokenRequestError: If token request fails.
            NetworkError: If there's a network connectivity issue.
        """
        logger.info(f"Requesting token from {self._auth_endpoint}")

        # Join scopes with space as per OAuth2 spec
        scope_str = " ".join(self._scopes) if self._scopes else ""

        data: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }

        # Only include scope if provided
        if scope_str:
            data["scope"] = scope_str
            logger.debug(f"Requesting scopes: {scope_str}")

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    self._auth_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except httpx.ConnectError as e:
            logger.error(f"Connection error: {e}")
            raise NetworkError("Failed to connect to auth server", cause=e) from e
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {e}")
            raise NetworkError("Auth request timed out", cause=e) from e
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            raise NetworkError(f"HTTP error: {e}", cause=e) from e

        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> TokenInfo:
        """Handle the token response.

        Args:
            response: The HTTP response from the token endpoint.

        Returns:
            TokenInfo with the new token.

        Raises:
            InvalidCredentialsError: If credentials are invalid.
            TokenRequestError: If the request failed.
        """
        if response.status_code == 401:
            logger.error("Authentication failed: invalid credentials")
            raise InvalidCredentialsError()

        if response.status_code == 400:
            # Try to extract error details
            try:
                error_data = response.json()
                error_code = error_data.get("error", "unknown_error")
                error_desc = error_data.get("error_description", "")
                logger.error(f"Token request error: {error_code} - {error_desc}")

                if error_code in ("invalid_client", "unauthorized_client"):
                    raise InvalidCredentialsError(f"{error_code}: {error_desc}")

                raise TokenRequestError(
                    message=f"{error_code}: {error_desc}",
                    status_code=400,
                    error_code=error_code,
                )
            except ValueError:
                raise TokenRequestError(
                    message="Bad request to token endpoint",
                    status_code=400,
                )

        if not response.is_success:
            logger.error(f"Token request failed with status {response.status_code}")
            raise TokenRequestError(
                message=f"Token request failed with status {response.status_code}",
                status_code=response.status_code,
            )

        # Parse successful response
        try:
            data = response.json()
        except ValueError as e:
            raise TokenRequestError("Invalid JSON response from token endpoint") from e

        access_token = data.get("access_token")
        token_type = data.get("token_type", "Bearer")
        expires_in = data.get("expires_in", 3600)  # Default to 1 hour

        if not access_token:
            raise TokenRequestError("No access_token in response")

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        logger.info(f"Token obtained, expires at {expires_at.isoformat()}")

        return TokenInfo(
            access_token=access_token,
            token_type=token_type,
            expires_at=expires_at,
        )

    def clear_token(self) -> None:
        """Clear cached token (force refresh on next request)."""
        self._token = None
        logger.debug("Token cache cleared")


def create_auth_client(settings: IngestSettings) -> AuthClient:
    """Create an AuthClient from configuration settings.

    Args:
        settings: The application configuration settings.

    Returns:
        Configured AuthClient instance.
    """
    return AuthClient(
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        auth_endpoint=settings.auth_endpoint,
        scopes=settings.auth_scope if settings.auth_scope else None,
    )
