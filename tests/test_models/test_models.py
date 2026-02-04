"""Tests for data models."""

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from ingest_cli.models import (
    BooleanValue,
    ContentMetadata,
    CreatedByAnnotation,
    CreateOrUpdateEvent,
    CurrencyValue,
    DateCreatedAnnotation,
    DateModifiedAnnotation,
    DatetimeValue,
    DateValue,
    DeleteEvent,
    Document,
    FileMetadataWithUpload,
    FileProperty,
    FileUpload,
    FloatValue,
    IntegerValue,
    ModifiedByAnnotation,
    NameAnnotation,
    ObjectValue,
    StringValue,
    TypeAnnotation,
    format_datetime,
)


class TestPropertyValues:
    """Tests for typed property value models."""

    def test_string_value_single(self) -> None:
        """String value with single string."""
        val = StringValue(value="hello")
        assert val.type == "string"
        assert val.value == "hello"
        data = val.model_dump()
        assert data == {"type": "string", "value": "hello"}

    def test_string_value_array(self) -> None:
        """String value with array of strings."""
        val = StringValue(value=["tag1", "tag2", "tag3"])
        assert val.value == ["tag1", "tag2", "tag3"]

    def test_integer_value(self) -> None:
        """Integer property value."""
        val = IntegerValue(value=42)
        assert val.type == "integer"
        assert val.value == 42

    def test_integer_value_array(self) -> None:
        """Integer value with array."""
        val = IntegerValue(value=[1, 2, 3])
        assert val.value == [1, 2, 3]

    def test_float_value(self) -> None:
        """Float property value."""
        val = FloatValue(value=3.14159)
        assert val.type == "float"
        assert val.value == 3.14159

    def test_boolean_value(self) -> None:
        """Boolean property value."""
        val = BooleanValue(value=True)
        assert val.type == "boolean"
        assert val.value is True

    def test_date_value(self) -> None:
        """Date property value."""
        val = DateValue(value="2024-01-15")
        assert val.type == "date"
        assert val.value == "2024-01-15"

    def test_datetime_value(self) -> None:
        """Datetime property value."""
        val = DatetimeValue(value="2024-01-15T10:30:00.000Z")
        assert val.type == "datetime"
        assert val.value == "2024-01-15T10:30:00.000Z"

    def test_currency_value(self) -> None:
        """Currency property value."""
        val = CurrencyValue(value="12.34USD")
        assert val.type == "currency"
        assert val.value == "12.34USD"

    def test_object_value(self) -> None:
        """Object property value."""
        val = ObjectValue(value={"key": "value", "count": 42})
        assert val.type == "object"
        assert val.value == {"key": "value", "count": 42}

    def test_object_value_array(self) -> None:
        """Object value with array of dicts."""
        val = ObjectValue(value=[{"a": 1}, {"b": 2}])
        assert val.value == [{"a": 1}, {"b": 2}]


class TestAnnotations:
    """Tests for annotation models."""

    def test_name_annotation(self) -> None:
        """Name annotation serialization."""
        ann = NameAnnotation(value="Test Document")
        data = ann.model_dump()
        assert data == {"annotation": "name", "value": "Test Document"}

    def test_type_annotation(self) -> None:
        """Type annotation serialization."""
        ann = TypeAnnotation(value="Invoice")
        data = ann.model_dump()
        assert data == {"annotation": "type", "type": "string", "value": "Invoice"}

    def test_date_created_annotation(self) -> None:
        """DateCreated annotation."""
        ann = DateCreatedAnnotation(value="2024-01-15T10:30:00.000Z")
        data = ann.model_dump()
        assert data["annotation"] == "dateCreated"
        assert data["type"] == "datetime"
        assert data["value"] == "2024-01-15T10:30:00.000Z"

    def test_created_by_annotation(self) -> None:
        """CreatedBy annotation."""
        ann = CreatedByAnnotation(value="user-123")
        data = ann.model_dump()
        assert data["annotation"] == "createdBy"
        assert data["value"] == "user-123"

    def test_date_modified_annotation(self) -> None:
        """DateModified annotation."""
        ann = DateModifiedAnnotation(value="2024-01-16T14:20:00.000Z")
        data = ann.model_dump()
        assert data["annotation"] == "dateModified"

    def test_modified_by_annotation(self) -> None:
        """ModifiedBy annotation with single value."""
        ann = ModifiedByAnnotation(value="admin")
        assert ann.value == "admin"

    def test_modified_by_annotation_array(self) -> None:
        """ModifiedBy annotation with array."""
        ann = ModifiedByAnnotation(value=["user1", "user2"])
        assert ann.value == ["user1", "user2"]


class TestFileModels:
    """Tests for file metadata models."""

    def test_content_metadata(self) -> None:
        """File content metadata structure."""
        meta = ContentMetadata(
            size=23100,
            name="document.pdf",
            content_type="application/pdf",
        )
        data = meta.model_dump(by_alias=True)
        assert data["size"] == 23100
        assert data["name"] == "document.pdf"
        assert data["content-type"] == "application/pdf"

    def test_content_metadata_with_digest(self) -> None:
        """File metadata with digest."""
        meta = ContentMetadata(
            size=1000,
            name="file.txt",
            content_type="text/plain",
            digest="sha256:abc123",
        )
        assert meta.digest == "sha256:abc123"

    def test_file_upload_reference(self) -> None:
        """Upload ID reference."""
        upload = FileUpload(
            id="e381e783-1e30-4793-b250-3eda634b7c2c",
            content_type="application/pdf",
        )
        data = upload.model_dump(by_alias=True)
        assert data["id"] == "e381e783-1e30-4793-b250-3eda634b7c2c"
        assert data["content-type"] == "application/pdf"

    def test_file_property_with_upload(self) -> None:
        """FileProperty with upload and metadata."""
        fp = FileProperty.with_upload(
            upload_id="uuid-123",
            content_type="application/pdf",
            size=5000,
            name="report.pdf",
        )
        assert isinstance(fp.file, FileMetadataWithUpload)
        assert fp.file.id == "uuid-123"

    def test_file_property_upload_only(self) -> None:
        """FileProperty with just upload reference."""
        fp = FileProperty.upload_only("uuid-456", "image/jpeg")
        assert isinstance(fp.file, FileUpload)

    def test_file_property_metadata_only(self) -> None:
        """FileProperty with metadata only."""
        fp = FileProperty.metadata_only(
            size=1024,
            name="image.png",
            content_type="image/png",
        )
        data = fp.model_dump(by_alias=True)
        assert "file" in data


class TestEvents:
    """Tests for content event models."""

    def test_create_or_update_event_minimal(self) -> None:
        """Event with required fields only."""
        event = CreateOrUpdateEvent(
            object_id="doc-123",
            source_id="a52878a6-b459-4a13-bdd9-7d086f591d58",
            source_timestamp=1732022495428,
            properties={"name": NameAnnotation(value="Test")},
        )
        assert event.object_id == "doc-123"
        assert event.event_type == "createOrUpdate"

    def test_create_or_update_event_serialization(self) -> None:
        """JSON output matches API schema."""
        event = CreateOrUpdateEvent(
            object_id="doc-123",
            source_id="a52878a6-b459-4a13-bdd9-7d086f591d58",
            source_timestamp=1732022495428,
            properties={
                "name": NameAnnotation(value="Test Document"),
                "type": TypeAnnotation(value="Report"),
            },
        )
        data = event.model_dump(by_alias=True)
        assert data["objectId"] == "doc-123"
        assert data["sourceId"] == "a52878a6-b459-4a13-bdd9-7d086f591d58"
        assert data["eventType"] == "createOrUpdate"
        assert "properties" in data

    def test_delete_event(self) -> None:
        """Delete event structure."""
        event = DeleteEvent(
            object_id="doc-456",
            source_id="a52878a6-b459-4a13-bdd9-7d086f591d58",
            source_timestamp=1732022495428,
        )
        assert event.event_type == "delete"
        data = event.model_dump(by_alias=True)
        assert data["eventType"] == "delete"

    def test_event_validates_object_id_pattern(self) -> None:
        """ObjectId pattern validation."""
        # Valid patterns
        CreateOrUpdateEvent(
            object_id="doc-123",
            source_id="uuid",
            source_timestamp=123,
            properties={},
        )
        CreateOrUpdateEvent(
            object_id="file.name_test-1",
            source_id="uuid",
            source_timestamp=123,
            properties={},
        )

        # Invalid patterns should fail
        with pytest.raises(ValidationError):
            CreateOrUpdateEvent(
                object_id="invalid/id",  # Contains slash
                source_id="uuid",
                source_timestamp=123,
                properties={},
            )

        with pytest.raises(ValidationError):
            CreateOrUpdateEvent(
                object_id="invalid id",  # Contains space
                source_id="uuid",
                source_timestamp=123,
                properties={},
            )


class TestDocument:
    """Tests for high-level Document model."""

    def test_format_datetime(self) -> None:
        """Datetime formatting to ISO 8601."""
        dt = datetime(2024, 1, 15, 10, 30, 0, 123000)
        formatted = format_datetime(dt)
        assert formatted == "2024-01-15T10:30:00.123Z"

    def test_document_creation(self) -> None:
        """Basic document creation."""
        doc = Document(
            object_id="doc-001",
            name="Test Document",
            doc_type="Report",
            date_created=datetime(2024, 1, 15, 10, 0, 0),
            created_by="user-1",
            date_modified=datetime(2024, 1, 16, 14, 0, 0),
            modified_by="user-2",
        )
        assert doc.object_id == "doc-001"
        assert doc.name == "Test Document"
        assert not doc.has_file()

    def test_document_to_event(self) -> None:
        """Convert Document to API event."""
        doc = Document(
            object_id="doc-001",
            name="Test Document",
            doc_type="Report",
            date_created=datetime(2024, 1, 15, 10, 0, 0),
            created_by="user-1",
            date_modified=datetime(2024, 1, 16, 14, 0, 0),
            modified_by="user-2",
        )
        event = doc.to_event(
            source_id="a52878a6-b459-4a13-bdd9-7d086f591d58",
            source_timestamp=1732022495428,
        )
        assert isinstance(event, CreateOrUpdateEvent)
        assert event.object_id == "doc-001"

        # Check properties contain all required annotations
        props = event.properties
        assert "name" in props
        assert "type" in props
        assert "dateCreated" in props
        assert "createdBy" in props
        assert "dateModified" in props
        assert "modifiedBy" in props

    def test_document_with_custom_properties(self) -> None:
        """Document with additional custom properties."""
        doc = Document(
            object_id="doc-001",
            name="Test",
            doc_type="Report",
            date_created=datetime.now(),
            created_by="user",
            date_modified=datetime.now(),
            modified_by="user",
            properties={"category": "Finance", "priority": IntegerValue(value=1)},
        )
        event = doc.to_event(
            source_id="uuid",
            source_timestamp=123,
        )
        assert "category" in event.properties
        assert "priority" in event.properties

    def test_document_with_file_requires_upload_id(self, tmp_path: Path) -> None:
        """Document with file requires upload_id."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        doc = Document(
            object_id="doc-001",
            name="Test",
            doc_type="Report",
            date_created=datetime.now(),
            created_by="user",
            date_modified=datetime.now(),
            modified_by="user",
            file_path=test_file,
            file_content_type="text/plain",
        )
        assert doc.has_file()

        # Should fail without upload_id
        with pytest.raises(ValueError, match="upload_id is required"):
            doc.to_event(source_id="uuid")

        # Should succeed with upload_id
        event = doc.to_event(source_id="uuid", upload_id="upload-123")
        assert "file" in event.properties

    def test_document_file_requires_content_type(self, tmp_path: Path) -> None:
        """File attachment requires content type."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with pytest.raises(ValueError, match="file_content_type is required"):
            Document(
                object_id="doc-001",
                name="Test",
                doc_type="Report",
                date_created=datetime.now(),
                created_by="user",
                date_modified=datetime.now(),
                modified_by="user",
                file_path=test_file,
                # Missing file_content_type
            )

    def test_document_to_delete_event(self) -> None:
        """Create delete event from document."""
        doc = Document(
            object_id="doc-to-delete",
            name="Test",
            doc_type="Report",
            date_created=datetime.now(),
            created_by="user",
            date_modified=datetime.now(),
            modified_by="user",
        )
        event = doc.to_delete_event(
            source_id="uuid",
            source_timestamp=123456789,
        )
        assert isinstance(event, DeleteEvent)
        assert event.object_id == "doc-to-delete"
        assert event.event_type == "delete"
