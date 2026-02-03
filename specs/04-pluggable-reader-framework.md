# Step 4: Pluggable Reader Framework

**Status:** ✅ Completed

## Objective

Implement a pluggable reader framework that supports multiple input sources (CSV, JSON, local files) with a clean, extensible architecture.

## Requirements

### From seed.md:
- Read documents from various sources:
  - CSV files with paths/metadata columns
  - JSON/JSONL files
  - Local file system (directory scanning)
- Support future expansion (SharePoint connector)
- Reader auto-discovery from CLI (`ingest readers` command)

## Design

### Reader Interface

All readers implement a common abstract base class:

```python
from abc import ABC, abstractmethod
from typing import Iterator
from ingest_cli.models import RawDocument

class BaseReader(ABC):
    """Base class for all document readers."""
    
    # Metadata for CLI discovery
    name: str           # Short name (e.g., "csv", "json")
    description: str    # Human-readable description
    
    @abstractmethod
    def read(self, source: str, **options) -> Iterator[RawDocument]:
        """Read documents from the source.
        
        Args:
            source: The source path/location.
            **options: Reader-specific options.
            
        Yields:
            RawDocument instances for each document found.
        """
        pass
    
    @classmethod
    @abstractmethod
    def validate_source(cls, source: str) -> bool:
        """Check if this reader can handle the given source."""
        pass
```

### RawDocument Model

Simple container for document data before mapping:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class RawDocument:
    """Raw document data from a reader."""
    
    # Required
    file_path: Path              # Path to the actual file
    
    # Optional metadata
    title: str | None = None
    source_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Content (loaded lazily or provided)
    content: bytes | None = None
    
    def load_content(self) -> bytes:
        """Load content from file_path if not already loaded."""
        if self.content is None:
            self.content = self.file_path.read_bytes()
        return self.content
```

## Deliverables

### 1. CSV Reader (`ingest_cli/readers/csv_reader.py`)

Read documents from CSV files:

```python
class CSVReader(BaseReader):
    """Read documents from a CSV file."""
    
    name = "csv"
    description = "Read document paths and metadata from CSV files"
    
    # Column mappings (configurable)
    DEFAULT_PATH_COLUMN = "file_path"
    DEFAULT_TITLE_COLUMN = "title"
    DEFAULT_URL_COLUMN = "source_url"
```

**CSV Format:**
```csv
file_path,title,source_url,custom_field
/path/to/doc1.pdf,Document One,https://example.com/doc1,value1
/path/to/doc2.pdf,Document Two,https://example.com/doc2,value2
```

**Features:**
- Configurable column names via options
- Support for additional metadata columns
- Skip invalid/missing files with warning
- Auto-detect delimiter (comma, semicolon, tab)

### 2. JSON Reader (`ingest_cli/readers/json_reader.py`)

Read documents from JSON/JSONL files:

```python
class JSONReader(BaseReader):
    """Read documents from JSON or JSONL files."""
    
    name = "json"
    description = "Read document metadata from JSON or JSONL files"
```

**JSON Format (array):**
```json
[
  {"file_path": "/path/to/doc1.pdf", "title": "Document One"},
  {"file_path": "/path/to/doc2.pdf", "title": "Document Two"}
]
```

**JSONL Format (newline-delimited):**
```jsonl
{"file_path": "/path/to/doc1.pdf", "title": "Document One"}
{"file_path": "/path/to/doc2.pdf", "title": "Document Two"}
```

### 3. Directory Reader (`ingest_cli/readers/directory_reader.py`)

Scan a directory for files:

```python
class DirectoryReader(BaseReader):
    """Read documents from a local directory."""
    
    name = "directory"
    description = "Scan a directory for document files"
```

**Features:**
- Recursive or non-recursive scan
- File extension filtering (e.g., `--extensions .pdf,.docx`)
- Glob pattern support
- Title derived from filename

### 4. Reader Registry (`ingest_cli/readers/registry.py`)

Central registry for reader discovery:

```python
class ReaderRegistry:
    """Registry for document readers."""
    
    _readers: dict[str, type[BaseReader]] = {}
    
    @classmethod
    def register(cls, reader_class: type[BaseReader]) -> type[BaseReader]:
        """Register a reader class (can be used as decorator)."""
        
    @classmethod
    def get(cls, name: str) -> type[BaseReader] | None:
        """Get a reader by name."""
        
    @classmethod
    def list_all(cls) -> list[type[BaseReader]]:
        """List all registered readers."""
        
    @classmethod
    def auto_detect(cls, source: str) -> type[BaseReader] | None:
        """Auto-detect the appropriate reader for a source."""
```

### 5. Reader Factory (`ingest_cli/readers/factory.py`)

Factory function for creating readers:

```python
def create_reader(
    reader_type: str | None = None,
    source: str | None = None,
) -> BaseReader:
    """Create a reader instance.
    
    Args:
        reader_type: Explicit reader type (csv, json, directory).
        source: Source path (used for auto-detection if type not specified).
        
    Returns:
        A configured reader instance.
    """
```

## CLI Integration

Update `ingest readers` command to show registered readers:

```
$ ingest readers

Available readers:
  csv        Read document paths and metadata from CSV files
  json       Read document metadata from JSON or JSONL files
  directory  Scan a directory for document files

Use 'ingest run --reader <name> --input <source>' to process documents.
```

## Test Coverage

**Test file:** `tests/test_readers/test_readers.py`

### CSV Reader Tests
| Test | Description |
|------|-------------|
| `test_csv_read_basic` | Read simple CSV with defaults |
| `test_csv_custom_columns` | Custom column name mapping |
| `test_csv_missing_file_skipped` | Missing files logged and skipped |
| `test_csv_semicolon_delimiter` | Auto-detect semicolon delimiter |
| `test_csv_extra_metadata` | Extra columns stored in metadata |

### JSON Reader Tests
| Test | Description |
|------|-------------|
| `test_json_read_array` | Read JSON array format |
| `test_jsonl_read` | Read JSONL format |
| `test_json_invalid_entry_skipped` | Invalid entries skipped |

### Directory Reader Tests
| Test | Description |
|------|-------------|
| `test_directory_read_flat` | Read files from flat directory |
| `test_directory_read_recursive` | Recursive directory scan |
| `test_directory_filter_extensions` | Filter by file extension |
| `test_directory_glob_pattern` | Use glob pattern |

### Registry Tests
| Test | Description |
|------|-------------|
| `test_register_reader` | Register a reader class |
| `test_get_reader_by_name` | Get reader by name |
| `test_auto_detect_csv` | Auto-detect CSV files |
| `test_auto_detect_directory` | Auto-detect directories |
| `test_list_all_readers` | List all registered readers |

## Files to Create

| File | Purpose |
|------|---------|
| `ingest_cli/readers/base.py` | BaseReader ABC and RawDocument |
| `ingest_cli/readers/csv_reader.py` | CSV file reader |
| `ingest_cli/readers/json_reader.py` | JSON/JSONL file reader |
| `ingest_cli/readers/directory_reader.py` | Directory scanner |
| `ingest_cli/readers/registry.py` | Reader registry |
| `ingest_cli/readers/factory.py` | Reader factory |
| `tests/test_readers/__init__.py` | Test package |
| `tests/test_readers/test_csv_reader.py` | CSV reader tests |
| `tests/test_readers/test_json_reader.py` | JSON reader tests |
| `tests/test_readers/test_directory_reader.py` | Directory reader tests |
| `tests/test_readers/test_registry.py` | Registry tests |

## Files to Modify

| File | Changes |
|------|---------|
| `ingest_cli/readers/__init__.py` | Export public API |
| `ingest_cli/cli/main.py` | Update `readers` command |

## Verification

```bash
# Create test CSV
cat > test_docs.csv << EOF
file_path,title
/tmp/doc1.txt,Document One
/tmp/doc2.txt,Document Two
EOF

# Create test files
echo "Content 1" > /tmp/doc1.txt
echo "Content 2" > /tmp/doc2.txt

# List readers
ingest readers

# Run tests
pytest tests/test_readers/ -v
```

## Next Steps

→ **Step 5: Document Models** - Define the Pydantic models matching the OpenAPI schema for the ingestion API.
