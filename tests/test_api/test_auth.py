"""Tests for the authentication client."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from ingest_cli.api import (
    AuthClient,
    InvalidCredentialsError,
    NetworkError,
    TokenInfo,
    TokenRequestError,
    create_auth_client,
)
from ingest_cli.config import IngestSettings

# Test constants
AUTH_ENDPOINT = "https://auth.example.com/connect/token"
CLIENT_ID = "test-client"
CLIENT_SECRET = "test-secret"


class TestTokenInfo:
    """Tests for TokenInfo dataclass."""

    def test_token_not_expired(self) -> None:
        """Token is not expired when expiration is in the future."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        token = TokenInfo(
            access_token="test-token",
            token_type="Bearer",
            expires_at=expires_at,
        )
        assert token.is_expired is False

    def test_token_expired(self) -> None:
        """Token is expired when expiration is in the past."""
        expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        token = TokenInfo(
            access_token="test-token",
            token_type="Bearer",
            expires_at=expires_at,
        )
        assert token.is_expired is True

    def test_token_expires_within_buffer(self) -> None:
        """Token is considered expired within 60s buffer."""
        # Token expires in 30 seconds (within 60s buffer)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
        token = TokenInfo(
            access_token="test-token",
            token_type="Bearer",
            expires_at=expires_at,
        )
        assert token.is_expired is True

    def test_token_not_expired_outside_buffer(self) -> None:
        """Token is not expired when expiration is > 60s buffer."""
        # Token expires in 90 seconds (outside 60s buffer)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=90)
        token = TokenInfo(
            access_token="test-token",
            token_type="Bearer",
            expires_at=expires_at,
        )
        assert token.is_expired is False


class TestAuthClient:
    """Tests for AuthClient."""

    @respx.mock
    def test_request_token_success(self) -> None:
        """Successfully request and parse token."""
        respx.post(AUTH_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "test-access-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        )

        client = AuthClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            auth_endpoint=AUTH_ENDPOINT,
        )

        token = client.get_token()
        assert token == "test-access-token"

    @respx.mock
    def test_token_request_includes_correct_data(self) -> None:
        """Token request includes correct form data."""
        route = respx.post(AUTH_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "test-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        )

        client = AuthClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            auth_endpoint=AUTH_ENDPOINT,
            scopes=["custom-scope", "another-scope"],
        )

        client.get_token()

        assert route.called
        request = route.calls.last.request
        content = request.content.decode()
        assert "grant_type=client_credentials" in content
        assert f"client_id={CLIENT_ID}" in content
        assert f"client_secret={CLIENT_SECRET}" in content
        # Scopes are joined with spaces (URL-encoded as +)
        assert "scope=custom-scope" in content or "scope=custom-scope+another-scope" in content

    @respx.mock
    def test_token_caching(self) -> None:
        """Token is cached and reused."""
        route = respx.post(AUTH_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "cached-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        )

        client = AuthClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            auth_endpoint=AUTH_ENDPOINT,
        )

        # First call - should request token
        token1 = client.get_token()
        # Second call - should use cached token
        token2 = client.get_token()

        assert token1 == token2 == "cached-token"
        assert route.call_count == 1  # Only one request

    @respx.mock
    def test_token_refresh_on_expiry(self) -> None:
        """Expired token triggers refresh."""
        route = respx.post(AUTH_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "new-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        )

        client = AuthClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            auth_endpoint=AUTH_ENDPOINT,
        )

        # Set an expired token
        client._token = TokenInfo(
            access_token="old-token",
            token_type="Bearer",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )

        # Should refresh the token
        token = client.get_token()
        assert token == "new-token"
        assert route.call_count == 1

    @respx.mock
    def test_invalid_credentials_error_401(self) -> None:
        """401 response raises InvalidCredentialsError."""
        respx.post(AUTH_ENDPOINT).mock(
            return_value=httpx.Response(401, json={"error": "invalid_client"})
        )

        client = AuthClient(
            client_id="wrong-client",
            client_secret="wrong-secret",
            auth_endpoint=AUTH_ENDPOINT,
        )

        with pytest.raises(InvalidCredentialsError):
            client.get_token()

    @respx.mock
    def test_invalid_credentials_error_400_invalid_client(self) -> None:
        """400 with invalid_client error raises InvalidCredentialsError."""
        respx.post(AUTH_ENDPOINT).mock(
            return_value=httpx.Response(
                400,
                json={
                    "error": "invalid_client",
                    "error_description": "Client not found",
                },
            )
        )

        client = AuthClient(
            client_id="wrong-client",
            client_secret="wrong-secret",
            auth_endpoint=AUTH_ENDPOINT,
        )

        with pytest.raises(InvalidCredentialsError):
            client.get_token()

    @respx.mock
    def test_token_request_error_other_400(self) -> None:
        """400 with other error raises TokenRequestError."""
        respx.post(AUTH_ENDPOINT).mock(
            return_value=httpx.Response(
                400,
                json={
                    "error": "invalid_grant",
                    "error_description": "Grant type not allowed",
                },
            )
        )

        client = AuthClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            auth_endpoint=AUTH_ENDPOINT,
        )

        with pytest.raises(TokenRequestError) as exc:
            client.get_token()
        assert exc.value.error_code == "invalid_grant"
        assert exc.value.status_code == 400

    @respx.mock
    def test_token_request_error_500(self) -> None:
        """500 response raises TokenRequestError."""
        respx.post(AUTH_ENDPOINT).mock(return_value=httpx.Response(500))

        client = AuthClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            auth_endpoint=AUTH_ENDPOINT,
        )

        with pytest.raises(TokenRequestError) as exc:
            client.get_token()
        assert exc.value.status_code == 500

    @respx.mock
    def test_network_error_connection(self) -> None:
        """Connection error raises NetworkError."""
        respx.post(AUTH_ENDPOINT).mock(side_effect=httpx.ConnectError("Connection refused"))

        client = AuthClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            auth_endpoint=AUTH_ENDPOINT,
        )

        with pytest.raises(NetworkError) as exc:
            client.get_token()
        assert exc.value.cause is not None

    @respx.mock
    def test_network_error_timeout(self) -> None:
        """Timeout error raises NetworkError."""
        respx.post(AUTH_ENDPOINT).mock(side_effect=httpx.TimeoutException("Request timed out"))

        client = AuthClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            auth_endpoint=AUTH_ENDPOINT,
        )

        with pytest.raises(NetworkError) as exc:
            client.get_token()
        assert "timed out" in str(exc.value).lower()

    @respx.mock
    def test_invalid_json_response(self) -> None:
        """Invalid JSON response raises TokenRequestError."""
        respx.post(AUTH_ENDPOINT).mock(return_value=httpx.Response(200, content=b"not json"))

        client = AuthClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            auth_endpoint=AUTH_ENDPOINT,
        )

        with pytest.raises(TokenRequestError):
            client.get_token()

    @respx.mock
    def test_missing_access_token_in_response(self) -> None:
        """Missing access_token in response raises TokenRequestError."""
        respx.post(AUTH_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={"token_type": "Bearer", "expires_in": 3600},
            )
        )

        client = AuthClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            auth_endpoint=AUTH_ENDPOINT,
        )

        with pytest.raises(TokenRequestError) as exc:
            client.get_token()
        assert "access_token" in str(exc.value).lower()

    @respx.mock
    def test_clear_token(self) -> None:
        """Clear token forces refresh on next request."""
        route = respx.post(AUTH_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        )

        client = AuthClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            auth_endpoint=AUTH_ENDPOINT,
        )

        # Get token (request 1)
        client.get_token()
        assert route.call_count == 1

        # Clear and get again (request 2)
        client.clear_token()
        client.get_token()
        assert route.call_count == 2

    @respx.mock
    def test_default_expires_in(self) -> None:
        """Default expires_in of 3600 is used if not in response."""
        respx.post(AUTH_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "test-token",
                    "token_type": "Bearer",
                    # No expires_in
                },
            )
        )

        client = AuthClient(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            auth_endpoint=AUTH_ENDPOINT,
        )

        token = client.get_token()
        assert token == "test-token"
        # Token should be valid (default expiry is 1 hour)
        assert client._token is not None
        assert client._token.is_expired is False


class TestCreateAuthClient:
    """Tests for create_auth_client factory function."""

    def test_factory_creates_client_from_settings(self) -> None:
        """Factory function creates AuthClient from settings."""
        settings = IngestSettings(
            environment_id="test-env",
            source_id="12345678-1234-1234-1234-123456789012",
            system_integration_id="test-integration",
            client_id="settings-client-id",
            client_secret="settings-client-secret",
            auth_endpoint="https://custom-auth.example.com/token",
        )

        client = create_auth_client(settings)

        assert client._client_id == "settings-client-id"
        assert client._client_secret == "settings-client-secret"
        assert client._auth_endpoint == "https://custom-auth.example.com/token"
