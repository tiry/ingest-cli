# Step 10: Error Handling & Resilience

## Overview

Implement robust error handling with retry logic for transient failures.

## Deliverables

### 1. Retry Decorator (`utils/retry.py`)

Create a retry decorator for handling transient API failures:

```python
@dataclass
class RetryConfig:
    max_retries: int = 1
    backoff_seconds: float = 2.0
    retry_on: tuple[type, ...] = (TransientError,)

def retry(config: RetryConfig | None = None):
    """Decorator to retry functions on transient errors."""
```

### 2. Error Classification

Classify errors as transient (retryable) or permanent:

**Transient Errors (retry):**
- HTTP 429 (Too Many Requests)
- HTTP 500, 502, 503, 504 (Server Errors)
- Connection timeout
- Network unreachable

**Permanent Errors (don't retry):**
- HTTP 400 (Bad Request)
- HTTP 401, 403 (Authentication/Authorization)
- HTTP 404 (Not Found)
- HTTP 422 (Validation Error)

### 3. Enhanced API Exceptions (`api/exceptions.py`)

```python
class TransientError(APIError):
    """Errors that may succeed on retry."""
    pass

class RateLimitError(TransientError):
    """Rate limit exceeded (HTTP 429)."""
    retry_after: Optional[float] = None

class ServerError(TransientError):
    """Server-side error (5xx)."""
    pass

class PermanentError(APIError):
    """Errors that will not succeed on retry."""
    pass

class ValidationError(PermanentError):
    """Request validation failed."""
    pass
```

### 4. Retry Integration in API Client

Update `IngestionClient` to use retry:

```python
class IngestionClient:
    @retry(RetryConfig(max_retries=1, backoff_seconds=2.0))
    def upload_file(self, presigned_url: str, file_data: bytes) -> None:
        ...
    
    @retry(RetryConfig(max_retries=1, backoff_seconds=2.0))
    def send_events(self, events: list[ContentEvent]) -> BatchResponse:
        ...
```

### 5. Pipeline Error Resilience

The pipeline should:
- Continue processing after individual document failures
- Track failed documents in result
- Log errors with document context
- Provide summary at end

## Tests (`tests/test_utils/test_retry.py`)

### Test Cases

1. **test_retry_succeeds_first_try** - No retry when successful
2. **test_retry_succeeds_after_transient** - Succeeds after transient failure
3. **test_retry_exhausted** - Raises after max retries
4. **test_retry_permanent_error** - No retry on permanent error
5. **test_retry_backoff_timing** - Backoff delay applied
6. **test_classify_http_errors** - Correct error classification
7. **test_rate_limit_retry_after** - Respects Retry-After header
8. **test_retry_with_context** - Error includes operation context

## Implementation Notes

- Use tenacity library for retry if available, otherwise custom implementation
- Log retry attempts with warning level
- Include retry count in error messages
- Honor Retry-After header for rate limits
