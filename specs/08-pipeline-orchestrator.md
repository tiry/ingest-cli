# Step 8: Ingestion Pipeline Orchestrator

## Objective
Implement the end-to-end ingestion pipeline that orchestrates reading documents, mapping them, uploading files, and sending events to the API.

## Components

### 1. Pipeline Orchestrator (`pipeline/orchestrator.py`)

Main class that coordinates all pipeline stages:
- **Read Stage**: Use reader to iterate through documents
- **Map Stage**: Transform documents using mapper
- **Upload Stage**: Upload files to S3 via presigned URLs
- **Event Stage**: Send document events to ingestion API

### 2. Pipeline Configuration

```python
@dataclass
class PipelineConfig:
    batch_size: int = 50
    dry_run: bool = False
    offset: int = 0
    limit: int | None = None  # None = process all
```

### 3. Pipeline Result

```python
@dataclass
class PipelineResult:
    total_read: int
    total_mapped: int
    total_uploaded: int
    total_sent: int
    failed: int
    skipped: int
    duration_seconds: float
    errors: list[PipelineError]
```

### 4. Error Tracking

```python
@dataclass
class PipelineError:
    document_index: int
    stage: str  # "read", "map", "upload", "send"
    message: str
    details: dict | None = None
```

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Pipeline Orchestrator                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────┐│
│  │  Reader  │──▶│  Mapper  │──▶│ Uploader │──▶│ Sender ││
│  └──────────┘   └──────────┘   └──────────┘   └────────┘│
│       │              │              │             │      │
│       ▼              ▼              ▼             ▼      │
│   raw dict    mapped dict    upload result   response   │
│                                                          │
│  ─────────────────────────────────────────────────────  │
│                    Batch Processing                      │
│  ─────────────────────────────────────────────────────  │
│                                                          │
│  Documents are processed in batches:                     │
│  1. Read batch_size documents                            │
│  2. Map all documents in batch                           │
│  3. Upload files for batch (if any)                      │
│  4. Send events for batch                                │
│  5. Repeat until all documents processed                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Key Features

### Batch Processing
- Process documents in configurable batch sizes (default: 50)
- API limit is 100 events per request

### Offset/Resume Support
- Skip first N documents with `offset` parameter
- Useful for resuming failed imports

### Dry-Run Mode
- Validate pipeline without making API calls
- Preview what would be sent

### Progress Tracking
- Log progress after each batch
- Track success/failure counts

### Error Handling
- Continue processing after individual failures
- Collect all errors for final report
- Track which stage failed

## API

### IngestionPipeline Class

```python
class IngestionPipeline:
    def __init__(
        self,
        reader: BaseReader,
        mapper: BaseMapper,
        ingestion_client: IngestionClient,
        config: PipelineConfig | None = None,
    ) -> None:
        ...
    
    def run(self) -> PipelineResult:
        """Execute the full pipeline."""
        ...
    
    def run_batch(
        self, 
        documents: list[dict],
    ) -> BatchResult:
        """Process a single batch of documents."""
        ...
```

### Factory Function

```python
def create_pipeline(
    settings: IngestSettings,
    reader: BaseReader,
    mapper: BaseMapper | None = None,
    dry_run: bool = False,
    batch_size: int | None = None,
    offset: int = 0,
) -> IngestionPipeline:
    """Create a configured pipeline from settings."""
    ...
```

## Test Cases

### Unit Tests
1. **Pipeline initialization**: Verify configuration defaults
2. **Batch processing**: Process documents in correct batch sizes
3. **Offset handling**: Skip correct number of documents
4. **Dry-run mode**: No API calls made
5. **Error collection**: Errors from all stages collected
6. **Progress tracking**: Counts updated correctly
7. **Pipeline result**: Final result has correct totals

### Integration Tests (Mocked)
1. **Full pipeline**: Reader → Mapper → Upload → Send
2. **File upload flow**: Presigned URL → Upload → Event
3. **Batch boundary**: Events sent at batch boundaries

## Files to Create/Modify

### New Files
- `ingest_cli/pipeline/orchestrator.py` - Pipeline implementation

### Modify
- `ingest_cli/pipeline/__init__.py` - Export pipeline

### Test Files
- `tests/test_pipeline/__init__.py`
- `tests/test_pipeline/test_orchestrator.py`
