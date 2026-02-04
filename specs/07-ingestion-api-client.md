# Step 7: Ingestion API Client

## Overview

Implement the HxAI Ingestion API client for uploading files and sending document events.

## API Endpoints

### 1. POST /v1/presigned-urls
Get presigned S3 URLs for file uploads.

**Query Parameters:**
- `count` (1-100): Number of URLs to request

**Response:**
```json
{
  "presignedUrls": [
    {
      "url": "https://s3.amazonaws.com/bucket/...",
      "objectKey": "abc123..."
    }
  ]
}
```

### 2. POST /v2/ingestion-events
Send document ingestion events (createOrUpdate, delete).

**Request Body:**
```json
{
  "sourceId": "uuid",
  "contentEvents": [
    {
      "createOrUpdate": {
        "objectId": "doc-123",
        "properties": { ... }
      }
    }
  ]
}
```

## Required Headers

All API requests require:
- `Authorization`: Bearer {token}
- `Content-Type`: application/json
- `hxp-environment`: Environment ID
- `User-Agent`: Client identifier

## Implementation

### Files

- `ingest_cli/api/ingestion.py` - Ingestion API client class

### IngestionClient Class

```python
class IngestionClient:
    def __init__(
        self,
        settings: Settings,
        auth_client: AuthClient,
    ) -> None:
        ...
    
    def get_presigned_urls(self, count: int) -> list[PresignedUrl]:
        """Request presigned URLs for file uploads (1-100)."""
        ...
    
    def upload_file(self, url: str, file_path: Path) -> str:
        """Upload file to presigned URL, return object key."""
        ...
    
    def send_events(self, events: list[ContentEvent]) -> IngestionResponse:
        """Send batch of content events to v2/ingestion-events."""
        ...
```

### Error Handling

- `IngestionError` - Base exception for API errors
- `PresignedUrlError` - Failed to get presigned URLs
- `FileUploadError` - Failed to upload file
- `EventSendError` - Failed to send events

## Tests

1. **Presigned URL Tests:**
   - Request single URL
   - Request batch of URLs (up to 100)
   - Invalid count raises error
   - API error handling

2. **File Upload Tests:**
   - Successful upload returns object key
   - Upload failure handling
   - Content-type detection

3. **Event Sending Tests:**
   - Send single event
   - Send batch of events
   - Response parsing
   - Error response handling

4. **Integration Tests:**
   - Full flow: get URL → upload → send event

## Dependencies

Uses `httpx` for async-capable HTTP client (already in project).

## Validation

- [x] Unit tests pass
- [x] Ruff linting passes
- [x] Presigned URL request formats correctly
- [x] File upload to presigned URL works
- [x] Event batch serialization matches schema
