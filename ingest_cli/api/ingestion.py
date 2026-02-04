"""HxAI Ingestion API client.

This module provides the IngestionClient for interacting with the
HxAI Ingestion REST API to upload files and send document events.
"""

from __future__ import annotations

import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from .auth import AuthClient
from .exceptions import (
    EventSendError,
    FileUploadError,
    NetworkError,
    PresignedUrlError,
)

if TYPE_CHECKING:
    from ingest_cli.config import IngestSettings
    from ingest_cli.models import ContentEvent

logger = logging.getLogger(__name__)

# API version paths
PRESIGNED_URLS_PATH = "/v1/presigned-urls"
INGESTION_EVENTS_PATH = "/v2/ingestion-events"

# User agent string
USER_AGENT = "ingest-cli/0.1.0 (Python httpx)"

# Default timeout for API requests (seconds)
DEFAULT_TIMEOUT = 60.0

# File upload timeout (longer for large files)
UPLOAD_TIMEOUT = 300.0


@dataclass
class PresignedUrl:
    """Represents a presigned URL for file upload.

    Attributes:
        url: The presigned S3 URL for uploading.
        object_key: The S3 object key for referencing in events.
    """

    url: str
    object_key: str


@dataclass
class UploadResult:
    """Result of a file upload operation.

    Attributes:
        object_key: S3 object key of uploaded file.
        file_path: Local path of the uploaded file.
        content_type: MIME type of the file.
        size_bytes: File size in bytes.
    """

    object_key: str
    file_path: Path
    content_type: str
    size_bytes: int


@dataclass
class IngestionResponse:
    """Response from ingestion events API.

    Attributes:
        success: Whether the request was successful.
        events_processed: Number of events processed.
        errors: List of any error details.
    """

    success: bool
    events_processed: int
    errors: list[dict[str, Any]]


class IngestionClient:
    """Client for HxAI Ingestion API.

    This client handles:
    - Obtaining presigned URLs for file uploads
    - Uploading files to S3 via presigned URLs
    - Sending document events to the ingestion API

    Example:
        >>> auth = AuthClient(...)
        >>> client = IngestionClient(
        ...     ingest_endpoint="https://ingestion.example.com",
        ...     environment_id="env-123",
        ...     source_id="source-456",
        ...     auth_client=auth,
        ... )
        >>> urls = client.get_presigned_urls(10)
        >>> result = client.upload_file(urls[0], Path("document.pdf"))
        >>> client.send_events([event])
    """

    def __init__(
        self,
        ingest_endpoint: str,
        environment_id: str,
        source_id: str,
        auth_client: AuthClient,
        user_agent: str = USER_AGENT,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the ingestion client.

        Args:
            ingest_endpoint: Base URL for ingestion API.
            environment_id: HxP environment ID (hxp-environment header).
            source_id: Content source ID.
            auth_client: AuthClient for obtaining tokens.
            user_agent: User agent string for requests.
            timeout: Request timeout in seconds.
        """
        # Remove trailing slash from endpoint
        self._endpoint = ingest_endpoint.rstrip("/")
        self._environment_id = environment_id
        self._source_id = source_id
        self._auth_client = auth_client
        self._user_agent = user_agent
        self._timeout = timeout

    @property
    def source_id(self) -> str:
        """Get the source ID."""
        return self._source_id

    @property
    def environment_id(self) -> str:
        """Get the environment ID."""
        return self._environment_id

    def _get_headers(self) -> dict[str, str]:
        """Get common headers for API requests.

        Returns:
            Dictionary of headers including authorization.
        """
        token = self._auth_client.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "hxp-environment": self._environment_id,
            "User-Agent": self._user_agent,
        }

    def get_presigned_urls(self, count: int = 1) -> list[PresignedUrl]:
        """Request presigned URLs for file uploads.

        Args:
            count: Number of URLs to request (1-100).

        Returns:
            List of PresignedUrl objects.

        Raises:
            ValueError: If count is not between 1 and 100.
            PresignedUrlError: If the request fails.
            NetworkError: If there's a network issue.
        """
        if not 1 <= count <= 100:
            raise ValueError("count must be between 1 and 100")

        url = f"{self._endpoint}{PRESIGNED_URLS_PATH}"
        headers = self._get_headers()

        logger.info(f"Requesting {count} presigned URL(s)")

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    url,
                    headers=headers,
                    params={"count": count},
                )
        except httpx.ConnectError as e:
            logger.error(f"Connection error: {e}")
            raise NetworkError("Failed to connect to ingestion API", cause=e) from e
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {e}")
            raise NetworkError("Presigned URL request timed out", cause=e) from e
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            raise NetworkError(f"HTTP error: {e}", cause=e) from e

        return self._handle_presigned_response(response)

    def _handle_presigned_response(self, response: httpx.Response) -> list[PresignedUrl]:
        """Handle presigned URL response.

        Args:
            response: HTTP response from presigned-urls endpoint.

        Returns:
            List of PresignedUrl objects.

        Raises:
            PresignedUrlError: If response indicates error.
        """
        if not response.is_success:
            logger.error(f"Presigned URL request failed: {response.status_code}")
            raise PresignedUrlError(
                message=f"Failed with status {response.status_code}",
                status_code=response.status_code,
            )

        try:
            data = response.json()
        except ValueError as e:
            raise PresignedUrlError("Invalid JSON response") from e

        presigned_urls = data.get("presignedUrls", [])

        if not presigned_urls:
            raise PresignedUrlError("No presigned URLs in response")

        result = []
        for url_data in presigned_urls:
            result.append(
                PresignedUrl(
                    url=url_data["url"],
                    object_key=url_data["objectKey"],
                )
            )

        logger.info(f"Received {len(result)} presigned URL(s)")
        return result

    def upload_file(
        self,
        presigned_url: PresignedUrl,
        file_path: Path,
    ) -> UploadResult:
        """Upload a file to S3 using a presigned URL.

        Args:
            presigned_url: PresignedUrl object with upload URL.
            file_path: Path to the local file.

        Returns:
            UploadResult with object key and metadata.

        Raises:
            FileUploadError: If upload fails.
            NetworkError: If there's a network issue.
            FileNotFoundError: If file doesn't exist.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Detect content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"

        file_size = file_path.stat().st_size

        logger.info(f"Uploading {file_path} ({file_size} bytes) to S3")

        try:
            with (
                httpx.Client(timeout=UPLOAD_TIMEOUT) as client,
                open(file_path, "rb") as f,
            ):
                response = client.put(
                    presigned_url.url,
                    content=f,
                    headers={"Content-Type": content_type},
                )
        except httpx.ConnectError as e:
            logger.error(f"Upload connection error: {e}")
            raise NetworkError("Failed to connect for upload", cause=e) from e
        except httpx.TimeoutException as e:
            logger.error(f"Upload timeout: {e}")
            raise NetworkError("File upload timed out", cause=e) from e
        except httpx.HTTPError as e:
            logger.error(f"Upload HTTP error: {e}")
            raise NetworkError(f"Upload HTTP error: {e}", cause=e) from e

        if not response.is_success:
            logger.error(f"Upload failed: {response.status_code}")
            raise FileUploadError(
                message=f"Upload failed with status {response.status_code}",
                file_path=str(file_path),
                status_code=response.status_code,
            )

        logger.info(f"Successfully uploaded {file_path}")

        return UploadResult(
            object_key=presigned_url.object_key,
            file_path=file_path,
            content_type=content_type,
            size_bytes=file_size,
        )

    def send_events(
        self,
        events: list[ContentEvent],
    ) -> IngestionResponse:
        """Send content events to the ingestion API.

        Args:
            events: List of ContentEvent objects to send.

        Returns:
            IngestionResponse with results.

        Raises:
            EventSendError: If the request fails.
            NetworkError: If there's a network issue.
        """
        if not events:
            return IngestionResponse(success=True, events_processed=0, errors=[])

        url = f"{self._endpoint}{INGESTION_EVENTS_PATH}"
        headers = self._get_headers()

        # Build request body
        content_events = [event.model_dump(by_alias=True, exclude_none=True) for event in events]
        request_body = {
            "sourceId": self._source_id,
            "contentEvents": content_events,
        }

        logger.info(f"Sending {len(events)} event(s) to ingestion API")

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    url,
                    headers=headers,
                    json=request_body,
                )
        except httpx.ConnectError as e:
            logger.error(f"Connection error: {e}")
            raise NetworkError("Failed to connect to ingestion API", cause=e) from e
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {e}")
            raise NetworkError("Event send request timed out", cause=e) from e
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            raise NetworkError(f"HTTP error: {e}", cause=e) from e

        return self._handle_events_response(response, len(events))

    def _handle_events_response(
        self,
        response: httpx.Response,
        event_count: int,
    ) -> IngestionResponse:
        """Handle events response.

        Args:
            response: HTTP response from events endpoint.
            event_count: Number of events sent.

        Returns:
            IngestionResponse.

        Raises:
            EventSendError: If response indicates error.
        """
        try:
            data = response.json() if response.content else {}
        except ValueError:
            data = {}

        if not response.is_success:
            logger.error(f"Event send failed: {response.status_code}")
            raise EventSendError(
                message=f"Failed with status {response.status_code}",
                status_code=response.status_code,
                error_details=data,
            )

        logger.info(f"Successfully sent {event_count} event(s)")

        return IngestionResponse(
            success=True,
            events_processed=event_count,
            errors=data.get("errors", []),
        )

    def send_events_batch(
        self,
        events: list[ContentEvent],
        batch_size: int = 50,
    ) -> list[IngestionResponse]:
        """Send events in batches.

        Args:
            events: List of ContentEvent objects.
            batch_size: Maximum events per batch.

        Returns:
            List of IngestionResponse for each batch.
        """
        responses = []

        for i in range(0, len(events), batch_size):
            batch = events[i : i + batch_size]
            response = self.send_events(batch)
            responses.append(response)

        return responses


def create_ingestion_client(
    settings: IngestSettings,
    auth_client: AuthClient,
) -> IngestionClient:
    """Create an IngestionClient from configuration settings.

    Args:
        settings: The application configuration settings.
        auth_client: AuthClient for authentication.

    Returns:
        Configured IngestionClient instance.
    """
    return IngestionClient(
        ingest_endpoint=settings.ingest_endpoint,
        environment_id=settings.environment_id,
        source_id=settings.source_id,
        auth_client=auth_client,
    )
