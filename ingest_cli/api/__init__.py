"""API module for ingest-cli.

This module provides API clients for:
- OAuth2 authentication (client credentials flow)
- HxAI Ingestion API (to be implemented)
"""

from .auth import AuthClient, TokenInfo, create_auth_client
from .exceptions import (
    APIError,
    AuthenticationError,
    InvalidCredentialsError,
    NetworkError,
    TokenExpiredError,
    TokenRequestError,
)

__all__ = [
    # Auth client
    "AuthClient",
    "TokenInfo",
    "create_auth_client",
    # Exceptions
    "APIError",
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenRequestError",
    "TokenExpiredError",
    "NetworkError",
]
