# Step 5: Document Models

**Status:** ✅ Complete (35 tests)

## Objective

Define Pydantic models that match the HxAI Ingestion API schema for v2 ingestion events, property values, annotations, and file metadata.

## Requirements

### From OpenAPI spec:
- v2 API uses `ContentEventsV2` with:
  - `CreateOrUpdateContentEventV2`
  - `DeleteContentEvent`
- Required annotations for createOrUpdate:
  - name, type, dateCreated, createdBy, dateModified, modifiedBy
- Property value types:
  - string, integer, float, boolean, date, datetime, currency, object
  - Single values or arrays
- File metadata with upload ID and content-type

## Design

### Model Hierarchy

```
ContentEvent (base)
├── CreateOrUpdateEvent
└── DeleteEvent

PropertyValue (discriminated union)
├── AnnotatedValue (name, type, dateCreated, etc.)
├── TypedValue (string, integer, float, etc.)
└── FileProperty

FileMetadata
├── ContentMetadata (size, name, content-type, digest)
└── UploadInfo (id, content-type)
```

## Deliverables

### 1. PropertyValue Models (`models/properties.py`)

```python
from datetime import datetime
from typing import Literal, Union

from pydantic import BaseModel, Field

class StringValue(BaseModel):
    """String property value."""
    type: Literal["string"] = "string"
    value: str | list[str]

class IntegerValue(BaseModel):
    """Integer property value."""
    type: Literal["integer"] = "integer"
    value: int | list[int]

class FloatValue(BaseModel):
    """Float property value."""
    type: Literal["float"] = "float"
    value: float | list[float]

class BooleanValue(BaseModel):
    """Boolean property value."""
    type: Literal["boolean"] = "boolean"
    value: bool | list[bool]

class DateValue(BaseModel):
    """Date property value (YYYY-MM-DD)."""
    type: Literal["date"] = "date"
    value: str | list[str]  # Pattern: \d{4}-\d{2}-\d{2}

class DatetimeValue(BaseModel):
    """Datetime property value (ISO 8601)."""
    type: Literal["datetime"] = "datetime"
    value: str | list[str]  # Pattern: ISO 8601 with Z

class CurrencyValue(BaseModel):
    """Currency property value (amount + currency code)."""
    type: Literal["currency"] = "currency"
    value: str | list[str]  # Pattern: (-)?\d+(\.\d+)?[A-Z]{3}

class ObjectValue(BaseModel):
    """Object property value."""
    type: Literal["object"] = "object"
    value: dict | list[dict]
```

### 2. Annotation Models (`models/annotations.py`)

```python
class NameAnnotation(BaseModel):
    """Document name annotation (required)."""
    annotation: Literal["name"] = "name"
    value: str

class TypeAnnotation(BaseModel):
    """Document type annotation (required)."""
    annotation: Literal["type"] = "type"
    type: Literal["string"] = "string"
    value: str

class DateCreatedAnnotation(BaseModel):
    """Date created annotation (required)."""
    annotation: Literal["dateCreated"] = "dateCreated"
    type: Literal["datetime"] = "datetime"
    value: str  # ISO 8601 datetime

class CreatedByAnnotation(BaseModel):
    """Created by user annotation (required)."""
    annotation: Literal["createdBy"] = "createdBy"
    type: Literal["string"] = "string"
    value: str

class DateModifiedAnnotation(BaseModel):
    """Date modified annotation (required)."""
    annotation: Literal["dateModified"] = "dateModified"
    type: Literal["datetime"] = "datetime"
    value: str  # ISO 8601 datetime

class ModifiedByAnnotation(BaseModel):
    """Modified by user annotation (required)."""
    annotation: Literal["modifiedBy"] = "modifiedBy"
    type: Literal["string"] = "string"
    value: str | list[str]
```

### 3. File Models (`models/file.py`)

```python
class ContentMetadata(BaseModel):
    """File content metadata."""
    size: int = Field(ge=0)
    name: str = Field(min_length=1)
    content_type: str = Field(alias="content-type")
    digest: str | None = None

class FileUpload(BaseModel):
    """File upload reference."""
    id: str = Field(min_length=1)
    content_type: str = Field(alias="content-type")

class FileMetadataWithUpload(BaseModel):
    """File with metadata and upload info."""
    content_metadata: ContentMetadata = Field(alias="content-metadata")
    id: str = Field(min_length=1)
    content_type: str = Field(alias="content-type")

class FileProperty(BaseModel):
    """File property wrapper."""
    file: FileMetadataWithUpload | FileUpload | ContentMetadata
```

### 4. Event Models (`models/event.py`)

```python
from typing import Literal

from pydantic import BaseModel, Field

PropertyValue = Union[
    StringValue, IntegerValue, FloatValue, BooleanValue,
    DateValue, DatetimeValue, CurrencyValue, ObjectValue,
    NameAnnotation, TypeAnnotation, DateCreatedAnnotation,
    CreatedByAnnotation, DateModifiedAnnotation, ModifiedByAnnotation,
    FileProperty
]

class ContentEventBase(BaseModel):
    """Base for all content events."""
    object_id: str = Field(alias="objectId", min_length=1, max_length=128)
    source_id: str = Field(alias="sourceId")  # UUID format
    source_timestamp: int = Field(alias="sourceTimestamp")

class CreateOrUpdateEvent(ContentEventBase):
    """Create or update content event."""
    event_type: Literal["createOrUpdate"] = Field(
        "createOrUpdate", alias="eventType"
    )
    properties: dict[str, PropertyValue]

class DeleteEvent(ContentEventBase):
    """Delete content event."""
    event_type: Literal["delete"] = Field("delete", alias="eventType")
```

### 5. Document Model (`models/document.py`)

High-level document model for the pipeline:

```python
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

@dataclass
class Document:
    """Document for ingestion pipeline."""
    
    # Identifiers
    object_id: str
    
    # Required annotations
    name: str
    doc_type: str
    date_created: datetime
    created_by: str
    date_modified: datetime
    modified_by: str
    
    # Optional file
    file_path: Path | None = None
    file_content_type: str | None = None
    
    # Custom properties
    properties: dict = field(default_factory=dict)
    
    def to_event(
        self, source_id: str, upload_id: str | None = None
    ) -> CreateOrUpdateEvent:
        """Convert to API event format."""
        ...
```

## Test Coverage

**Test file:** `tests/test_models/test_models.py`

### Property Value Tests
| Test | Description |
|------|-------------|
| `test_string_value_single` | Single string value |
| `test_string_value_array` | Array of strings |
| `test_integer_value` | Integer value |
| `test_float_value` | Float value |
| `test_boolean_value` | Boolean value |
| `test_date_value_format` | Date format validation |
| `test_datetime_value_format` | Datetime format validation |
| `test_currency_value_format` | Currency format validation |
| `test_object_value` | Object/dict value |

### Annotation Tests
| Test | Description |
|------|-------------|
| `test_name_annotation` | Name annotation serialization |
| `test_type_annotation` | Type annotation serialization |
| `test_date_created_annotation` | DateCreated annotation |
| `test_created_by_annotation` | CreatedBy annotation |
| `test_date_modified_annotation` | DateModified annotation |
| `test_modified_by_annotation` | ModifiedBy annotation |

### File Tests
| Test | Description |
|------|-------------|
| `test_content_metadata` | File metadata structure |
| `test_file_upload_reference` | Upload ID reference |
| `test_file_with_metadata_and_upload` | Combined metadata + upload |

### Event Tests
| Test | Description |
|------|-------------|
| `test_create_or_update_event_minimal` | Event with required fields only |
| `test_create_or_update_event_with_file` | Event with file property |
| `test_create_or_update_event_serialization` | JSON output matches API schema |
| `test_delete_event` | Delete event structure |
| `test_event_validates_object_id_pattern` | ObjectId pattern validation |

### Document Tests
| Test | Description |
|------|-------------|
| `test_document_to_event` | Convert Document to API event |
| `test_document_with_file` | Document with file attachment |
| `test_document_required_fields` | Validates required annotations |

## Files to Create

| File | Purpose |
|------|---------|
| `ingest_cli/models/properties.py` | Typed property value models |
| `ingest_cli/models/annotations.py` | Annotation models |
| `ingest_cli/models/file.py` | File metadata models |
| `ingest_cli/models/event.py` | Content event models |
| `ingest_cli/models/document.py` | High-level Document model |
| `tests/test_models/__init__.py` | Test package |
| `tests/test_models/test_models.py` | Model tests |

## Files to Modify

| File | Changes |
|------|---------|
| `ingest_cli/models/__init__.py` | Export public API |

## Verification

```bash
# Run model tests
pytest tests/test_models/ -v

# Test JSON serialization
python -c "
from ingest_cli.models import CreateOrUpdateEvent, NameAnnotation
event = CreateOrUpdateEvent(
    object_id='doc-123',
    source_id='a52878a6-b459-4a13-bdd9-7d086f591d58',
    source_timestamp=1732022495428,
    properties={'name': NameAnnotation(value='Test Doc')}
)
print(event.model_dump_json(by_alias=True, indent=2))
"
```

## Example Output

A valid v2 createOrUpdate event should serialize to:

```json
{
  "objectId": "doc-123",
  "sourceId": "a52878a6-b459-4a13-bdd9-7d086f591d58",
  "sourceTimestamp": 1732022495428,
  "eventType": "createOrUpdate",
  "properties": {
    "name": {
      "annotation": "name",
      "value": "Test Document"
    },
    "type": {
      "annotation": "type",
      "type": "string",
      "value": "Report"
    },
    "dateCreated": {
      "annotation": "dateCreated",
      "type": "datetime",
      "value": "2024-01-15T10:30:00.000Z"
    },
    "createdBy": {
      "annotation": "createdBy",
      "type": "string",
      "value": "user-123"
    },
    "dateModified": {
      "annotation": "dateModified",
      "type": "datetime",
      "value": "2024-01-16T14:20:00.000Z"
    },
    "modifiedBy": {
      "annotation": "modifiedBy",
      "type": "string",
      "value": "user-456"
    },
    "customField": {
      "type": "string",
      "value": "custom value"
    }
  }
}
```

## Next Steps

→ **Step 6: Mapper Framework** - Create mapper interface for transforming RawDocument to Document.

---

## Related Specs

- `00-implementation_plan.md` - Overall plan
- `04-pluggable-reader-framework.md` - Reader framework (RawDocument)
- `openapi/insight-ingestion-merged-components.yaml` - API schema
