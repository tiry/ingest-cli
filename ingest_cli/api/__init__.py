"""API module for ingest-cli.

This module provides API clients for:
- OAuth2 authentication (client credentials flow)
- HxAI Ingestion API (file uploads and document events)
"""

from .auth import AuthClient, TokenInfo, create_auth_client
from .exceptions import (
    APIError,
    AuthenticationError,
    EventSendError,
    FileUploadError,
    IngestionError,
    InvalidCredentialsError,
    NetworkError,
    PresignedUrlError,
    TokenExpiredError,
    TokenRequestError,
)
from .ingestion import (
    IngestionClient,
    IngestionResponse,
    PresignedUrl,
    UploadResult,
    create_ingestion_client,
)

__all__ = [
    # Auth client
    "AuthClient",
    "TokenInfo",
    "create_auth_client",
    # Ingestion client
    "IngestionClient",
    "IngestionResponse",
    "PresignedUrl",
    "UploadResult",
    "create_ingestion_client",
    # Base exceptions
    "APIError",
    # Auth exceptions
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenRequestError",
    "TokenExpiredError",
    # Ingestion exceptions
    "IngestionError",
    "PresignedUrlError",
    "FileUploadError",
    "EventSendError",
    # Network
    "NetworkError",
]
