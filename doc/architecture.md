# Ingest-CLI Architecture

## Overview

The ingest-cli is a modular, extensible command-line tool for ingesting documents into a content management system. It follows a plugin-based architecture that allows easy extension of input sources and transformation logic.

## Core Principles

1. **Pluggability**: Readers and Mappers are pluggable components registered via a registry pattern
2. **Pipeline Architecture**: Documents flow through a clear, linear pipeline with distinct stages
3. **Separation of Concerns**: Each component has a single, well-defined responsibility
4. **Configuration-Driven**: Behavior is controlled via YAML configuration files
5. **Testability**: Each component can be tested independently

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLI Layer                               │
│  (main.py - Commands: run, check, readers, mappers)            │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Configuration Layer                           │
│         (config.yaml → IngestSettings)                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Pipeline Orchestrator                         │
│  (Coordinates the flow: Read → Map → Upload → Send)            │
└───┬─────────────┬───────────────┬──────────────┬────────────────┘
    │             │               │              │
    ▼             ▼               ▼              ▼
┌────────┐   ┌────────┐     ┌─────────┐   ┌──────────┐
│ Reader │   │ Mapper │     │   API   │   │  Models  │
│Registry│   │Registry│     │ Clients │   │          │
└────────┘   └────────┘     └─────────┘   └──────────┘
```

## Component Details

### 1. Pipeline Orchestrator

**Location**: `ingest_cli/pipeline/orchestrator.py`

**Responsibilities**:
- Coordinates document flow through all stages
- Manages batching for efficient API usage
- Handles error collection and reporting
- Supports dry-run mode for validation

**Pipeline Stages**:
```
Raw Source → Reader → RawDocument → Mapper → Document → Event Builder → Event
                                                              ↓
                                                        File Upload (S3)
                                                              ↓
                                                        API Submission
```

**Key Features**:
- Batch processing (1-100 documents per batch)
- Offset and limit support for partial processing
- Comprehensive error tracking per stage
- Timing and metrics collection

### 2. Readers (Input Layer)

**Location**: `ingest_cli/readers/`

**Purpose**: Convert various input sources into a standardized `RawDocument` format

**Built-in Readers**:
- **CSV Reader**: Reads document metadata from CSV files
- **JSON Reader**: Parses JSON/JSONL files with document metadata
- **Directory Reader**: Scans filesystem directories for documents

**Registry Pattern**:
```python
# Readers register themselves
READER_REGISTRY = {
    "csv": CSVReader,
    "json": JSONReader,
    "directory": DirectoryReader,
}

# Automatic detection based on file extension
reader = get_reader("auto", source)
```

**Pluggability**:
1. Create a new class extending `BaseReader`
2. Implement required methods: `read()`, `validate_source()`
3. Register in `READER_REGISTRY`
4. No changes needed to pipeline code

**Example**: Adding a Database Reader
```python
class DatabaseReader(BaseReader):
    name = "database"
    description = "Read from SQL database"
    
    def read(self, source: str, **options) -> Iterator[RawDocument]:
        # Connect to database and yield documents
        pass
    
    @classmethod
    def validate_source(cls, source: str) -> bool:
        return source.startswith("db://")
```

### 3. Mappers (Transformation Layer)

**Location**: `ingest_cli/mappers/`

**Purpose**: Transform `RawDocument` into fully-specified `Document` objects

**Built-in Mappers**:
- **Identity Mapper**: Direct field mapping with sensible defaults
- **Field Mapper**: Flexible field-to-field mapping with custom rules

**Registry Pattern**:
```python
MAPPER_REGISTRY = {
    "identity": IdentityMapper,
    "field": FieldMapper,
}

# Get mapper by name or use default
mapper = get_mapper("identity")
```

**Pluggability**:
1. Create a new class extending `BaseMapper`
2. Implement `map()` method: `RawDocument → Document`
3. Register in `MAPPER_REGISTRY`
4. Can be specified in config or command line

**Example**: Adding a Custom Business Logic Mapper
```python
class EnrichmentMapper(BaseMapper):
    @property
    def name(self) -> str:
        return "enrichment"
    
    def map(self, raw: RawDocument) -> Document:
        # Add business logic: lookups, validation, enrichment
        # Call external services, apply rules, etc.
        return Document(...)
```

### 4. API Clients

**Location**: `ingest_cli/api/`

**Components**:
- **AuthClient**: Handles OAuth2 authentication
- **IngestionClient**: Manages document submission and file uploads

**Features**:
- Token caching and automatic refresh
- Retry logic with exponential backoff
- Batch operations for efficiency
- Presigned URL handling for file uploads

### 5. Data Models

**Location**: `ingest_cli/models/`

**Key Models**:

```
RawDocument
  ├─ file_path: Path
  ├─ title: str | None
  ├─ source_url: str | None
  └─ metadata: dict
         ↓ [Mapper]
Document
  ├─ object_id: str
  ├─ name: str
  ├─ doc_type: str
  ├─ created_by: str
  ├─ modified_by: str
  ├─ date_created: datetime
  ├─ date_modified: datetime
  ├─ file_path: Path | None
  └─ properties: dict
         ↓ [Event Builder]
CreateOrUpdateEvent
  ├─ objectId: str
  ├─ sourceId: str
  ├─ sourceTimestamp: int
  └─ properties: dict
```

### 6. Configuration

**Location**: `ingest_cli/config/`

**Configuration File** (`config.yaml`):
```yaml
environment_id: "uuid"
source_id: "my-source"
client_id: "client-id"
client_secret: "secret"
ingest_endpoint: "https://api.example.com/ingest/"
auth_endpoint: "https://auth.example.com/oauth/token"
batch_size: 50
```

**Loading Hierarchy**:
1. Default values
2. Configuration file
3. Environment variables (overrides)
4. Command-line flags (overrides all)

## Extension Points

### Adding a New Reader

1. **Create Reader Class**:
```python
# ingest_cli/readers/my_reader.py
from ingest_cli.readers.base import BaseReader, RawDocument

class MyReader(BaseReader):
    name = "myreader"
    description = "Read from my custom source"
    
    def read(self, source: str, **options):
        # Your implementation
        yield RawDocument(...)
    
    @classmethod
    def validate_source(cls, source: str) -> bool:
        return source.endswith(".myformat")
```

2. **Register in Registry**:
```python
# ingest_cli/readers/registry.py
from .my_reader import MyReader

READER_REGISTRY = {
    # ... existing readers
    "myreader": MyReader,
}
```

3. **Use in CLI**:
```bash
ingest run -i input.myformat -r myreader
```

### Adding a New Mapper

1. **Create Mapper Class**:
```python
# ingest_cli/mappers/my_mapper.py
from ingest_cli.mappers.base import BaseMapper
from ingest_cli.models import Document

class MyMapper(BaseMapper):
    @property
    def name(self) -> str:
        return "mymapper"
    
    def map(self, raw: RawDocument) -> Document:
        # Your transformation logic
        return Document(...)
```

2. **Register in Registry**:
```python
# ingest_cli/mappers/registry.py
from .my_mapper import MyMapper

MAPPER_REGISTRY = {
    # ... existing mappers
    "mymapper": MyMapper,
}
```

3. **Use in CLI**:
```bash
ingest run -i input.csv -m mymapper
```

## Data Flow Example

### End-to-End Flow

```
1. User Command:
   $ ingest run -i documents.csv --dry-run

2. Configuration Loading:
   config.yaml → IngestSettings

3. Component Creation:
   - Reader: CSVReader (auto-detected from .csv)
   - Mapper: IdentityMapper (default)
   - Pipeline: IngestionPipeline

4. Reading Phase:
   documents.csv → CSVReader
                 ↓
   RawDocument(file_path="doc1.pdf", metadata={...})

5. Mapping Phase:
   RawDocument → IdentityMapper
               ↓
   Document(object_id="DOC-001", name="Document 1", ...)

6. Event Building Phase:
   Document → Event Builder
           ↓
   CreateOrUpdateEvent(objectId="DOC-001", properties={...})

7. Upload Phase (if files exist):
   - Request presigned URLs from API
   - Upload files to S3
   - Update events with uploaded object keys

8. Submission Phase:
   - Batch events (up to 50)
   - Send to ingestion API
   - Collect results

9. Result:
   PipelineResult(total_read=100, total_sent=100, failed=0)
```

## Error Handling

### Error Collection

Errors are tracked with context:
```python
PipelineError(
    document_index=42,
    stage="map",  # "read", "map", "upload", "send"
    message="Missing required field: object_id",
    details={...}
)
```

### Error Recovery

- **Per-Document Errors**: Pipeline continues processing remaining documents
- **Batch Errors**: Entire batch fails, but next batch is attempted
- **Fatal Errors**: Stop processing immediately (e.g., auth failure)

## Testing Strategy

### Unit Tests

- **Readers**: Test with mock data sources
- **Mappers**: Test transformations with known inputs/outputs
- **Pipeline**: Test with mock readers, mappers, and API clients
- **API Clients**: Test with mocked HTTP responses

### Integration Tests

- End-to-end tests with real file formats
- Validation of complete pipeline flow
- Error scenario testing

### Test Data

Located in `tests/data/`:
- Sample CSV/JSON files
- Test documents
- Mock configuration files

## Performance Considerations

1. **Batching**: Process 1-100 documents per API call
2. **Streaming**: Readers yield documents incrementally
3. **Memory**: No full document list kept in memory
4. **Parallel Uploads**: Multiple files uploaded concurrently
5. **Connection Pooling**: HTTP clients reuse connections

## Best Practices

### For Reader Developers

- Validate source early in `validate_source()`
- Yield documents incrementally
- Include source line/row numbers in metadata
- Handle encoding issues gracefully
- Support both files and directories when applicable

### For Mapper Developers

- Fail fast with clear error messages
- Provide sensible defaults
- Document required metadata fields
- Keep mapping logic stateless
- Use utility functions for common operations

### For Users

- Always test with `--dry-run` first
- Use `ingest check` to validate configuration
- Start with small batches for testing
- Monitor logs for warnings
- Use offset/limit for incremental processing

## CLI Commands

### Primary Commands

- **`ingest run`**: Execute ingestion pipeline
- **`ingest check`**: Validate configuration and test pipeline
- **`ingest readers`**: List available readers
- **`ingest mappers`**: List available mappers

### Common Options

- `-i, --input`: Input source path
- `-c, --config`: Configuration file path
- `-r, --reader`: Reader type
- `-m, --mapper`: Mapper type
- `--dry-run`: Validate without API calls
- `--batch-size`: Override default batch size
- `--offset`: Skip first N documents
- `--limit`: Process only N documents

## Future Enhancements

### Planned Features

1. **Async Processing**: Non-blocking I/O for improved throughput
2. **Progress Tracking**: Real-time progress bars and ETA
3. **Resume Capability**: Checkpoint-based recovery
4. **Parallel Processing**: Multi-threaded document processing
5. **Plugin System**: Dynamic plugin loading from external packages
6. **Web UI**: Browser-based configuration and monitoring

### Extension Ideas

1. **Additional Readers**:
   - Database readers (PostgreSQL, MySQL, MongoDB)
   - API readers (REST, GraphQL)
   - Cloud storage readers (S3, Azure Blob, GCS)
   - Email readers (IMAP, EML files)

2. **Additional Mappers**:
   - AI-powered enrichment mapper
   - Validation and quality checking mapper
   - Deduplication mapper
   - Multi-source merge mapper

3. **Enhanced Features**:
   - Document transformation (format conversion)
   - OCR integration
   - Metadata extraction from file content
   - Workflow automation

## Conclusion

The ingest-cli architecture prioritizes:
- **Extensibility**: Easy to add new readers and mappers
- **Maintainability**: Clear separation of concerns
- **Reliability**: Comprehensive error handling and recovery
- **Performance**: Efficient batching and streaming
- **Usability**: Simple CLI with sensible defaults

The plugin-based design ensures that new input sources and transformation logic can be added without modifying the core pipeline code, making it a flexible foundation for various document ingestion scenarios.
