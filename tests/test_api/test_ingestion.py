"""Tests for ingestion API client."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from ingest_cli.api import (
    AuthClient,
    EventSendError,
    FileUploadError,
    IngestionClient,
    IngestionResponse,
    NetworkError,
    PresignedUrl,
    PresignedUrlError,
    UploadResult,
)
from ingest_cli.models import CreateOrUpdateEvent

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_auth_client() -> MagicMock:
    """Create a mock auth client that returns a token."""
    mock = MagicMock(spec=AuthClient)
    mock.get_token.return_value = "test-token-123"
    return mock


@pytest.fixture
def ingestion_client(mock_auth_client: MagicMock) -> IngestionClient:
    """Create an ingestion client for testing."""
    return IngestionClient(
        ingest_endpoint="https://api.example.com",
        environment_id="env-123",
        source_id="source-456",
        auth_client=mock_auth_client,
    )


@pytest.fixture
def sample_presigned_response() -> dict:
    """Sample presigned URLs response."""
    return {
        "presignedUrls": [
            {
                "url": "https://s3.amazonaws.com/bucket/key1?signature=abc",
                "objectKey": "uploads/key1",
            },
            {
                "url": "https://s3.amazonaws.com/bucket/key2?signature=def",
                "objectKey": "uploads/key2",
            },
        ]
    }


@pytest.fixture
def temp_file(tmp_path: Path) -> Path:
    """Create a temporary test file."""
    test_file = tmp_path / "test_document.txt"
    test_file.write_text("This is test content for upload.")
    return test_file


# =============================================================================
# IngestionClient Initialization Tests
# =============================================================================


class TestIngestionClientInit:
    """Tests for IngestionClient initialization."""

    def test_init_with_required_params(self, mock_auth_client: MagicMock) -> None:
        """Test client initializes with required parameters."""
        client = IngestionClient(
            ingest_endpoint="https://api.example.com/",
            environment_id="env-123",
            source_id="source-456",
            auth_client=mock_auth_client,
        )

        assert client.environment_id == "env-123"
        assert client.source_id == "source-456"
        # Trailing slash should be removed
        assert client._endpoint == "https://api.example.com"

    def test_properties(self, ingestion_client: IngestionClient) -> None:
        """Test client properties."""
        assert ingestion_client.source_id == "source-456"
        assert ingestion_client.environment_id == "env-123"


# =============================================================================
# Presigned URL Tests
# =============================================================================


class TestGetPresignedUrls:
    """Tests for get_presigned_urls method."""

    def test_request_single_url(
        self,
        ingestion_client: IngestionClient,
        sample_presigned_response: dict,
    ) -> None:
        """Test requesting a single presigned URL."""
        mock_response = httpx.Response(
            200,
            json=sample_presigned_response,
        )

        with patch.object(httpx.Client, "post", return_value=mock_response):
            urls = ingestion_client.get_presigned_urls(1)

        assert len(urls) == 2  # Response has 2 URLs
        assert isinstance(urls[0], PresignedUrl)
        assert urls[0].url.startswith("https://s3.amazonaws.com")
        assert urls[0].object_key == "uploads/key1"

    def test_request_batch_urls(
        self,
        ingestion_client: IngestionClient,
        sample_presigned_response: dict,
    ) -> None:
        """Test requesting batch of presigned URLs."""
        mock_response = httpx.Response(
            200,
            json=sample_presigned_response,
        )

        with patch.object(httpx.Client, "post", return_value=mock_response):
            urls = ingestion_client.get_presigned_urls(50)

        assert len(urls) == 2

    def test_invalid_count_zero(self, ingestion_client: IngestionClient) -> None:
        """Test that count=0 raises ValueError."""
        with pytest.raises(ValueError, match="count must be between 1 and 100"):
            ingestion_client.get_presigned_urls(0)

    def test_invalid_count_over_100(self, ingestion_client: IngestionClient) -> None:
        """Test that count>100 raises ValueError."""
        with pytest.raises(ValueError, match="count must be between 1 and 100"):
            ingestion_client.get_presigned_urls(101)

    def test_api_error_response(self, ingestion_client: IngestionClient) -> None:
        """Test handling of API error response."""
        mock_response = httpx.Response(
            400,
            json={"error": "Bad request"},
        )

        with patch.object(httpx.Client, "post", return_value=mock_response):
            with pytest.raises(PresignedUrlError) as exc_info:
                ingestion_client.get_presigned_urls(10)

        assert exc_info.value.status_code == 400
        assert "400" in str(exc_info.value)

    def test_empty_response(self, ingestion_client: IngestionClient) -> None:
        """Test handling of empty presigned URLs response."""
        mock_response = httpx.Response(
            200,
            json={"presignedUrls": []},
        )

        with patch.object(httpx.Client, "post", return_value=mock_response):
            with pytest.raises(PresignedUrlError, match="No presigned URLs"):
                ingestion_client.get_presigned_urls(10)

    def test_network_error(self, ingestion_client: IngestionClient) -> None:
        """Test handling of network errors."""
        with patch.object(
            httpx.Client, "post", side_effect=httpx.ConnectError("Connection refused")
        ):
            with pytest.raises(NetworkError, match="Failed to connect"):
                ingestion_client.get_presigned_urls(10)


# =============================================================================
# File Upload Tests
# =============================================================================


class TestUploadFile:
    """Tests for upload_file method."""

    def test_successful_upload(
        self,
        ingestion_client: IngestionClient,
        temp_file: Path,
    ) -> None:
        """Test successful file upload."""
        presigned_url = PresignedUrl(
            url="https://s3.amazonaws.com/bucket/key?signature=abc",
            object_key="uploads/key1",
        )

        mock_response = httpx.Response(200)

        with patch.object(httpx.Client, "put", return_value=mock_response):
            result = ingestion_client.upload_file(presigned_url, temp_file)

        assert isinstance(result, UploadResult)
        assert result.object_key == "uploads/key1"
        assert result.file_path == temp_file
        assert result.content_type == "text/plain"
        assert result.size_bytes > 0

    def test_upload_pdf_content_type(
        self,
        ingestion_client: IngestionClient,
        tmp_path: Path,
    ) -> None:
        """Test PDF file gets correct content type."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        presigned_url = PresignedUrl(
            url="https://s3.amazonaws.com/bucket/key",
            object_key="uploads/key1",
        )

        mock_response = httpx.Response(200)

        with patch.object(httpx.Client, "put", return_value=mock_response):
            result = ingestion_client.upload_file(presigned_url, pdf_file)

        assert result.content_type == "application/pdf"

    def test_upload_unknown_content_type(
        self,
        ingestion_client: IngestionClient,
        tmp_path: Path,
    ) -> None:
        """Test unknown file type defaults to octet-stream."""
        unknown_file = tmp_path / "test.xyz123"
        unknown_file.write_bytes(b"unknown content")

        presigned_url = PresignedUrl(
            url="https://s3.amazonaws.com/bucket/key",
            object_key="uploads/key1",
        )

        mock_response = httpx.Response(200)

        with patch.object(httpx.Client, "put", return_value=mock_response):
            result = ingestion_client.upload_file(presigned_url, unknown_file)

        assert result.content_type == "application/octet-stream"

    def test_upload_file_not_found(
        self,
        ingestion_client: IngestionClient,
    ) -> None:
        """Test uploading non-existent file raises error."""
        presigned_url = PresignedUrl(
            url="https://s3.amazonaws.com/bucket/key",
            object_key="uploads/key1",
        )

        with pytest.raises(FileNotFoundError):
            ingestion_client.upload_file(presigned_url, Path("/nonexistent/file.txt"))

    def test_upload_failure(
        self,
        ingestion_client: IngestionClient,
        temp_file: Path,
    ) -> None:
        """Test upload failure handling."""
        presigned_url = PresignedUrl(
            url="https://s3.amazonaws.com/bucket/key",
            object_key="uploads/key1",
        )

        mock_response = httpx.Response(403)

        with patch.object(httpx.Client, "put", return_value=mock_response):
            with pytest.raises(FileUploadError) as exc_info:
                ingestion_client.upload_file(presigned_url, temp_file)

        assert exc_info.value.status_code == 403
        assert str(temp_file) in exc_info.value.file_path


# =============================================================================
# Event Sending Tests
# =============================================================================


class TestSendEvents:
    """Tests for send_events method."""

    @pytest.fixture
    def sample_event(self) -> CreateOrUpdateEvent:
        """Create a sample content event."""
        now = datetime.now(timezone.utc)
        return CreateOrUpdateEvent(
            object_id="doc-123",
            source_id="a52878a6-b459-4a13-bdd9-7d086f591d58",
            source_timestamp=int(now.timestamp() * 1000),
            properties={
                "name": {"annotationType": "name", "value": "Test Document"},
                "type": {"annotationType": "type", "value": "document"},
            },
        )

    def test_send_single_event(
        self,
        ingestion_client: IngestionClient,
        sample_event: CreateOrUpdateEvent,
    ) -> None:
        """Test sending a single event."""
        mock_response = httpx.Response(
            200,
            json={"success": True},
        )

        with patch.object(httpx.Client, "post", return_value=mock_response):
            response = ingestion_client.send_events([sample_event])

        assert isinstance(response, IngestionResponse)
        assert response.success is True
        assert response.events_processed == 1

    def test_send_empty_list(self, ingestion_client: IngestionClient) -> None:
        """Test sending empty event list returns success."""
        response = ingestion_client.send_events([])

        assert response.success is True
        assert response.events_processed == 0
        assert response.errors == []

    def test_send_batch_events(
        self,
        ingestion_client: IngestionClient,
        sample_event: CreateOrUpdateEvent,
    ) -> None:
        """Test sending multiple events."""
        events = [sample_event, sample_event, sample_event]

        mock_response = httpx.Response(
            200,
            json={"success": True},
        )

        with patch.object(httpx.Client, "post", return_value=mock_response):
            response = ingestion_client.send_events(events)

        assert response.events_processed == 3

    def test_send_events_error(
        self,
        ingestion_client: IngestionClient,
        sample_event: CreateOrUpdateEvent,
    ) -> None:
        """Test handling of event send error."""
        mock_response = httpx.Response(
            422,
            json={"error": "Validation error", "details": ["Invalid field"]},
        )

        with patch.object(httpx.Client, "post", return_value=mock_response):
            with pytest.raises(EventSendError) as exc_info:
                ingestion_client.send_events([sample_event])

        assert exc_info.value.status_code == 422
        assert exc_info.value.error_details is not None

    def test_send_events_network_error(
        self,
        ingestion_client: IngestionClient,
        sample_event: CreateOrUpdateEvent,
    ) -> None:
        """Test handling of network error during event send."""
        with patch.object(
            httpx.Client, "post", side_effect=httpx.ConnectError("Connection refused")
        ):
            with pytest.raises(NetworkError):
                ingestion_client.send_events([sample_event])


# =============================================================================
# Batch Sending Tests
# =============================================================================


class TestSendEventsBatch:
    """Tests for send_events_batch method."""

    @pytest.fixture
    def sample_events(self) -> list[CreateOrUpdateEvent]:
        """Create multiple sample events."""
        events = []
        now = datetime.now(timezone.utc)
        timestamp = int(now.timestamp() * 1000)
        for i in range(75):
            events.append(
                CreateOrUpdateEvent(
                    object_id=f"doc-{i}",
                    source_id="a52878a6-b459-4a13-bdd9-7d086f591d58",
                    source_timestamp=timestamp,
                    properties={
                        "name": {"annotationType": "name", "value": f"Document {i}"},
                        "type": {"annotationType": "type", "value": "document"},
                    },
                )
            )
        return events

    def test_batch_splitting(
        self,
        ingestion_client: IngestionClient,
        sample_events: list[CreateOrUpdateEvent],
    ) -> None:
        """Test events are split into batches."""
        mock_response = httpx.Response(200, json={})

        with patch.object(httpx.Client, "post", return_value=mock_response) as mock:
            responses = ingestion_client.send_events_batch(sample_events, batch_size=50)

        # 75 events with batch size 50 = 2 batches
        assert len(responses) == 2
        assert mock.call_count == 2

    def test_batch_size_respected(
        self,
        ingestion_client: IngestionClient,
        sample_events: list[CreateOrUpdateEvent],
    ) -> None:
        """Test custom batch size is respected."""
        mock_response = httpx.Response(200, json={})

        with patch.object(httpx.Client, "post", return_value=mock_response):
            responses = ingestion_client.send_events_batch(sample_events, batch_size=25)

        # 75 events with batch size 25 = 3 batches
        assert len(responses) == 3


# =============================================================================
# Headers Tests
# =============================================================================


class TestHeaders:
    """Tests for request headers."""

    def test_headers_include_auth(
        self,
        ingestion_client: IngestionClient,
        mock_auth_client: MagicMock,
        sample_presigned_response: dict,
    ) -> None:
        """Test headers include authorization."""
        mock_response = httpx.Response(200, json=sample_presigned_response)

        with patch.object(httpx.Client, "post", return_value=mock_response) as mock:
            ingestion_client.get_presigned_urls(1)

        # Verify auth client was called
        mock_auth_client.get_token.assert_called_once()

        # Check headers were passed
        call_kwargs = mock.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token-123"

    def test_headers_include_environment(
        self,
        ingestion_client: IngestionClient,
        sample_presigned_response: dict,
    ) -> None:
        """Test headers include environment ID."""
        mock_response = httpx.Response(200, json=sample_presigned_response)

        with patch.object(httpx.Client, "post", return_value=mock_response) as mock:
            ingestion_client.get_presigned_urls(1)

        call_kwargs = mock.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert headers["hxp-environment"] == "env-123"

    def test_headers_include_user_agent(
        self,
        ingestion_client: IngestionClient,
        sample_presigned_response: dict,
    ) -> None:
        """Test headers include user agent."""
        mock_response = httpx.Response(200, json=sample_presigned_response)

        with patch.object(httpx.Client, "post", return_value=mock_response) as mock:
            ingestion_client.get_presigned_urls(1)

        call_kwargs = mock.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert "User-Agent" in headers
        assert "ingest-cli" in headers["User-Agent"]


# =============================================================================
# Exception Tests
# =============================================================================


class TestIngestionExceptions:
    """Tests for ingestion exceptions."""

    def test_presigned_url_error(self) -> None:
        """Test PresignedUrlError."""
        error = PresignedUrlError(status_code=403)
        assert error.status_code == 403
        assert "presigned" in str(error).lower()

    def test_file_upload_error(self) -> None:
        """Test FileUploadError."""
        error = FileUploadError(file_path="/path/to/file.pdf", status_code=500)
        assert error.status_code == 500
        assert error.file_path == "/path/to/file.pdf"
        assert "/path/to/file.pdf" in str(error)

    def test_event_send_error(self) -> None:
        """Test EventSendError."""
        error = EventSendError(
            status_code=422,
            error_details={"errors": ["Invalid field"]},
        )
        assert error.status_code == 422
        assert error.error_details == {"errors": ["Invalid field"]}
