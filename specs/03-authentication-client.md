# Step 3: Authentication Client

**Status:** ✅ Completed

## Objective

Implement an OAuth2 client credentials flow authentication client to obtain and manage bearer tokens for the HxAI Ingestion API.

## Requirements

### From seed.md:
- OAuth2 client credentials flow with ClientID and ClientSecret
- Token endpoint: `https://auth.hyland.com/connect/token`
- Bearer token management with caching
- Token refresh before expiration

## Deliverables

### 1. Auth Client (`ingest_cli/api/auth.py`)

OAuth2 client credentials implementation:

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx

@dataclass
class TokenInfo:
    """Stores OAuth2 token information."""
    access_token: str
    token_type: str
    expires_at: datetime
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 60s buffer)."""
        return datetime.utcnow() >= self.expires_at - timedelta(seconds=60)

class AuthClient:
    """OAuth2 client credentials authentication client."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        auth_endpoint: str,
        timeout: float = 30.0,
    ):
        """Initialize the auth client."""
    
    def get_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
    
    def _request_token(self) -> TokenInfo:
        """Request a new token from the auth endpoint."""
    
    def clear_token(self) -> None:
        """Clear cached token (force refresh on next request)."""
```

### 2. Token Request Format

POST to auth endpoint with form data:

```
POST /connect/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&
client_id={client_id}&
client_secret={client_secret}&
scope=hxp-external-integration-api
```

### 3. Token Response Handling

Expected response format:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### 4. Error Handling

Handle common OAuth2 errors:

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `invalid_client` | 401 | Invalid client credentials |
| `invalid_grant` | 400 | Grant type not supported |
| `unauthorized_client` | 401 | Client not authorized for grant |
| Network errors | N/A | Connection timeout, DNS failure |

Custom exceptions:

```python
class AuthenticationError(Exception):
    """Base exception for authentication errors."""

class InvalidCredentialsError(AuthenticationError):
    """Client credentials are invalid."""

class TokenRequestError(AuthenticationError):
    """Token request failed."""
```

### 5. Token Caching Strategy

- Cache token in memory
- Check expiration before each use (60-second buffer)
- Thread-safe token access (if needed)
- Automatic refresh when token expires

### 6. Factory Function

Create auth client from settings:

```python
def create_auth_client(settings: IngestSettings) -> AuthClient:
    """Create an AuthClient from configuration settings."""
    return AuthClient(
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        auth_endpoint=settings.auth_endpoint,
    )
```

## Test Coverage

**Test file:** `tests/test_api/test_auth.py`

| Test | Description |
|------|-------------|
| `test_request_token_success` | Successfully request and parse token |
| `test_token_caching` | Token is cached and reused |
| `test_token_refresh_on_expiry` | Expired token triggers refresh |
| `test_invalid_credentials_error` | 401 response raises InvalidCredentialsError |
| `test_network_error_handling` | Network errors are handled gracefully |
| `test_token_expiration_check` | Token expiration check works correctly |
| `test_clear_token` | Clear token forces refresh |
| `test_factory_function` | Factory creates client from settings |

### Testing Approach

Use `respx` (or `pytest-httpx`) to mock HTTP requests:

```python
import respx
from httpx import Response

@respx.mock
def test_request_token_success():
    # Mock the token endpoint
    respx.post("https://auth.hyland.com/connect/token").mock(
        return_value=Response(200, json={
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        })
    )
    
    client = AuthClient(
        client_id="test-client",
        client_secret="test-secret",
        auth_endpoint="https://auth.hyland.com/connect/token",
    )
    
    token = client.get_token()
    assert token == "test-token"
```

## Files to Create

| File | Purpose |
|------|---------|
| `ingest_cli/api/auth.py` | Authentication client implementation |
| `ingest_cli/api/exceptions.py` | API-specific exceptions |
| `tests/test_api/__init__.py` | Test package init |
| `tests/test_api/test_auth.py` | Authentication tests |

## Files to Modify

| File | Changes |
|------|---------|
| `ingest_cli/api/__init__.py` | Export public API |
| `pyproject.toml` | Add `respx` to dev dependencies |

## Dependencies

Add to `pyproject.toml`:

```toml
[project.dependencies]
httpx = ">=0.27.0"

[project.optional-dependencies]
dev = [
    # ... existing deps
    "respx>=0.21.0",
]
```

## Verification

```bash
# Run auth tests
pytest tests/test_api/test_auth.py -v

# Test with real credentials (manual integration test)
# Create config with real credentials and run:
# ingest -c config.yaml validate  # should work with token request
```

## Usage Example

```python
from ingest_cli.config import load_config
from ingest_cli.api import create_auth_client

# Load configuration
settings = load_config("config.yaml")

# Create auth client
auth = create_auth_client(settings)

# Get token (handles caching/refresh)
token = auth.get_token()

# Use token in API requests
headers = {"Authorization": f"Bearer {token}"}
```

## Next Steps

→ **Step 4: Pluggable Reader Framework** - Implement the reader system for loading documents from different sources.
