# Step 6: Mapper Framework

**Status:** 🔄 In Progress

## Objective

Create a pluggable mapper framework for transforming RawDocument (from readers) into Document (for the API). Mappers allow users to customize field mapping and transformation logic.

## Requirements

From implementation plan:
- Abstract mapper interface
- Identity mapper (passthrough)
- Field mapping configuration
- Support for custom mapper modules
- Clear error messages for invalid mappers

## Design

### Mapper Interface

```python
from abc import ABC, abstractmethod
from ingest_cli.readers.base import RawDocument
from ingest_cli.models import Document

class BaseMapper(ABC):
    """Abstract base class for document mappers."""
    
    @abstractmethod
    def map(self, raw: RawDocument) -> Document:
        """Transform a raw document into an API document.
        
        Args:
            raw: RawDocument from a reader
            
        Returns:
            Document ready for API submission
        """
        pass
```

### Data Flow

```
Reader            Mapper             Pipeline
  │                 │                    │
  │ RawDocument     │                    │
  ├────────────────>│ Document          │
  │                 ├──────────────────>│
  │                 │                    │ to_event()
  │                 │                    ├──────────> API
```

### Mapper Types

1. **IdentityMapper**: Pass-through for pre-formatted data
2. **FieldMapper**: Configure field mappings via config
3. **Custom Mapper**: User-provided Python module

## Deliverables

### 1. Base Mapper (`mappers/base.py`)

```python
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from ingest_cli.models import Document
from ingest_cli.readers.base import RawDocument


class BaseMapper(ABC):
    """Abstract base class for document mappers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this mapper."""
        pass
    
    @abstractmethod
    def map(self, raw: RawDocument) -> Document:
        """Transform a raw document into an API document."""
        pass
    
    def validate_required_fields(self, data: dict[str, Any]) -> None:
        """Validate that required fields are present."""
        required = ["object_id", "name", "doc_type", "created_by", "modified_by"]
        missing = [f for f in required if f not in data or data[f] is None]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
```

### 2. Identity Mapper (`mappers/identity.py`)

```python
class IdentityMapper(BaseMapper):
    """Pass-through mapper for pre-formatted documents.
    
    Expects RawDocument data to contain:
    - object_id: str
    - name: str
    - doc_type: str
    - date_created: datetime or ISO string
    - created_by: str
    - date_modified: datetime or ISO string
    - modified_by: str
    - file_path: Path (optional)
    - file_content_type: str (optional, required if file_path)
    - properties: dict (optional)
    """
    
    @property
    def name(self) -> str:
        return "identity"
    
    def map(self, raw: RawDocument) -> Document:
        data = raw.data
        self.validate_required_fields(data)
        
        return Document(
            object_id=str(data["object_id"]),
            name=str(data["name"]),
            doc_type=str(data["doc_type"]),
            date_created=self._parse_datetime(data.get("date_created")),
            created_by=str(data["created_by"]),
            date_modified=self._parse_datetime(data.get("date_modified")),
            modified_by=data["modified_by"],
            file_path=data.get("file_path"),
            file_content_type=data.get("file_content_type"),
            properties=data.get("properties", {}),
        )
```

### 3. Field Mapper (`mappers/field_mapper.py`)

Configurable field mapping via YAML config:

```python
class FieldConfig:
    """Configuration for field mapping."""
    source: str              # Source field name in raw data
    target: str              # Target field in Document
    transform: str | None    # Optional transform function
    default: Any | None      # Default value if missing

class FieldMapper(BaseMapper):
    """Configurable field mapper with mapping rules."""
    
    def __init__(self, mapping: dict[str, str | FieldConfig]):
        """Initialize with field mappings.
        
        Args:
            mapping: Dict mapping target fields to source fields or configs
        """
        self._mapping = mapping
    
    def map(self, raw: RawDocument) -> Document:
        # Apply field mappings
        ...
```

### 4. Mapper Registry (`mappers/registry.py`)

```python
class MapperRegistry:
    """Registry for mapper implementations."""
    
    _mappers: dict[str, type[BaseMapper]]
    
    @classmethod
    def register(cls, mapper_class: type[BaseMapper]) -> None:
        """Register a mapper class."""
        
    @classmethod
    def get(cls, name: str) -> type[BaseMapper]:
        """Get mapper class by name."""
        
    @classmethod
    def list_mappers(cls) -> list[str]:
        """List all registered mapper names."""
```

### 5. Mapper Factory (`mappers/factory.py`)

```python
def create_mapper(
    name: str | None = None,
    module_path: str | None = None,
    config: dict | None = None,
) -> BaseMapper:
    """Create a mapper instance.
    
    Args:
        name: Registered mapper name (e.g., "identity", "field")
        module_path: Path to custom mapper module
        config: Configuration for the mapper
        
    Returns:
        Mapper instance
    """
```

## Configuration Example

```yaml
# In config.yaml
mapper:
  type: field  # or "identity", or path to custom module
  
  # Field mappings (for field mapper)
  fields:
    object_id: id
    name: title
    doc_type: category
    date_created: created_at
    created_by: author
    date_modified: updated_at
    modified_by: editor
    
  # Default values
  defaults:
    doc_type: "Document"
    created_by: "system"
    modified_by: "system"
```

## Test Cases

### Base Mapper Tests (`tests/test_mappers/test_base.py`)
| Test | Description |
|------|-------------|
| `test_validate_required_fields_all_present` | All required fields present |
| `test_validate_required_fields_missing` | Missing required field raises error |

### Identity Mapper Tests (`tests/test_mappers/test_identity.py`)
| Test | Description |
|------|-------------|
| `test_identity_mapper_basic` | Basic mapping works |
| `test_identity_mapper_with_file` | Maps file path and content type |
| `test_identity_mapper_with_properties` | Custom properties preserved |
| `test_identity_mapper_datetime_parsing` | Parses datetime strings |
| `test_identity_mapper_missing_field` | Raises error for missing field |

### Field Mapper Tests (`tests/test_mappers/test_field_mapper.py`)
| Test | Description |
|------|-------------|
| `test_field_mapper_simple` | Simple field renaming |
| `test_field_mapper_with_defaults` | Uses default values |
| `test_field_mapper_missing_required` | Error if required field missing |

### Factory Tests (`tests/test_mappers/test_factory.py`)
| Test | Description |
|------|-------------|
| `test_create_mapper_by_name` | Create mapper by registered name |
| `test_create_mapper_default` | Default mapper is identity |
| `test_create_mapper_unknown` | Unknown name raises error |
| `test_create_mapper_from_module` | Load custom mapper from path |

## Files to Create

| File | Purpose |
|------|---------|
| `ingest_cli/mappers/base.py` | Abstract mapper interface |
| `ingest_cli/mappers/identity.py` | Pass-through mapper |
| `ingest_cli/mappers/field_mapper.py` | Configurable field mapper |
| `ingest_cli/mappers/registry.py` | Mapper registry |
| `ingest_cli/mappers/factory.py` | Mapper factory |
| `tests/test_mappers/__init__.py` | Test package |
| `tests/test_mappers/test_mappers.py` | Mapper tests |

## Files to Modify

| File | Changes |
|------|---------|
| `ingest_cli/mappers/__init__.py` | Export public API |

## Verification

```bash
# Run mapper tests
pytest tests/test_mappers/ -v

# Test mapper creation
python -c "
from ingest_cli.mappers import create_mapper, IdentityMapper
mapper = create_mapper('identity')
print(f'Mapper: {mapper.name}')
"
```

## Next Steps

→ **Step 7: Ingestion API Client** - Implement the HxAI Ingestion API client.

---

## Related Specs

- `04-pluggable-reader-framework.md` - Reader framework (RawDocument)
- `05-document-models.md` - Document model
- `00-implementation_plan.md` - Overall plan
