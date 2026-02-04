"""Tests for mapper module."""

from datetime import datetime
from pathlib import Path

import pytest

from ingest_cli.mappers import (
    BaseMapper,
    FieldMapper,
    IdentityMapper,
    MapperError,
    MapperLoadError,
    MapperNotFoundError,
    MissingFieldError,
    create_mapper,
    get_available_mappers,
    get_mapper,
    get_mapper_info,
    list_mappers,
)
from ingest_cli.models import Document
from ingest_cli.readers.base import RawDocument

# =============================================================================
# BaseMapper Tests
# =============================================================================


class TestBaseMappingUtilities:
    """Test base mapper utility methods."""

    def test_parse_datetime_from_datetime(self):
        """Test parsing datetime object."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = BaseMapper.parse_datetime(dt)
        assert result == dt

    def test_parse_datetime_from_string_iso(self):
        """Test parsing ISO format string."""
        result = BaseMapper.parse_datetime("2024-01-15T10:30:00Z")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_datetime_from_string_milliseconds(self):
        """Test parsing ISO format with milliseconds."""
        result = BaseMapper.parse_datetime("2024-01-15T10:30:00.123Z")
        assert result.year == 2024
        assert result.microsecond == 123000

    def test_parse_datetime_date_only(self):
        """Test parsing date-only string."""
        result = BaseMapper.parse_datetime("2024-01-15")
        assert result.year == 2024
        assert result.hour == 0

    def test_parse_datetime_none_default(self):
        """Test parsing None uses default."""
        default = datetime(2000, 1, 1)
        result = BaseMapper.parse_datetime(None, default=default)
        assert result == default

    def test_parse_datetime_none_no_default(self):
        """Test parsing None without default uses now."""
        result = BaseMapper.parse_datetime(None)
        assert isinstance(result, datetime)
        assert result.year >= 2024

    def test_parse_datetime_invalid_string(self):
        """Test parsing invalid string raises error."""
        with pytest.raises(ValueError, match="Cannot parse datetime"):
            BaseMapper.parse_datetime("not a date")

    def test_parse_path_from_string(self):
        """Test parsing path from string."""
        result = BaseMapper.parse_path("/path/to/file.txt")
        assert result == Path("/path/to/file.txt")

    def test_parse_path_from_path(self):
        """Test parsing Path object."""
        path = Path("/path/to/file")
        result = BaseMapper.parse_path(path)
        assert result == path

    def test_parse_path_none(self):
        """Test parsing None returns None."""
        result = BaseMapper.parse_path(None)
        assert result is None


# =============================================================================
# IdentityMapper Tests
# =============================================================================


class TestIdentityMapper:
    """Test identity mapper."""

    def test_identity_mapper_name(self):
        """Test mapper name."""
        mapper = IdentityMapper()
        assert mapper.name == "identity"

    def test_identity_mapper_basic(self):
        """Test basic identity mapping."""
        mapper = IdentityMapper()
        raw = RawDocument.from_data({
            "object_id": "doc-123",
            "name": "Test Document",
            "doc_type": "Report",
            "created_by": "user-1",
            "modified_by": "user-2",
        })

        doc = mapper.map(raw)

        assert isinstance(doc, Document)
        assert doc.object_id == "doc-123"
        assert doc.name == "Test Document"
        assert doc.doc_type == "Report"
        assert doc.created_by == "user-1"
        assert doc.modified_by == "user-2"

    def test_identity_mapper_with_datetime(self):
        """Test mapping with datetime values."""
        mapper = IdentityMapper()
        dt = datetime(2024, 1, 15, 10, 30)
        raw = RawDocument.from_data({
            "object_id": "doc-123",
            "name": "Test",
            "doc_type": "Report",
            "date_created": dt,
            "created_by": "user-1",
            "date_modified": "2024-02-15T14:20:00Z",
            "modified_by": "user-2",
        })

        doc = mapper.map(raw)

        assert doc.date_created == dt
        assert doc.date_modified.year == 2024
        assert doc.date_modified.month == 2

    def test_identity_mapper_with_file(self):
        """Test mapping with file path."""
        mapper = IdentityMapper()
        raw = RawDocument.from_data({
            "object_id": "doc-123",
            "name": "Test",
            "doc_type": "Report",
            "created_by": "user-1",
            "modified_by": "user-2",
            "file_path": "/path/to/file.pdf",
            "file_content_type": "application/pdf",
        })

        doc = mapper.map(raw)

        assert doc.file_path == Path("/path/to/file.pdf")
        assert doc.file_content_type == "application/pdf"

    def test_identity_mapper_with_properties(self):
        """Test mapping with custom properties."""
        mapper = IdentityMapper()
        raw = RawDocument.from_data({
            "object_id": "doc-123",
            "name": "Test",
            "doc_type": "Report",
            "created_by": "user-1",
            "modified_by": "user-2",
            "properties": {"department": "Engineering", "priority": 1},
        })

        doc = mapper.map(raw)

        assert doc.properties == {"department": "Engineering", "priority": 1}

    def test_identity_mapper_missing_field(self):
        """Test missing required field raises error."""
        mapper = IdentityMapper()
        raw = RawDocument.from_data({
            "object_id": "doc-123",
            "name": "Test",
            # Missing doc_type, created_by, modified_by
        })

        with pytest.raises(MissingFieldError) as exc_info:
            mapper.map(raw)

        assert "doc_type" in exc_info.value.fields
        assert "created_by" in exc_info.value.fields
        assert "modified_by" in exc_info.value.fields


# =============================================================================
# FieldMapper Tests
# =============================================================================


class TestFieldMapper:
    """Test field mapper."""

    def test_field_mapper_name(self):
        """Test mapper name."""
        mapper = FieldMapper()
        assert mapper.name == "field"

    def test_field_mapper_no_mapping(self):
        """Test field mapper without mapping (uses field names as-is)."""
        mapper = FieldMapper()
        raw = RawDocument.from_data({
            "object_id": "doc-123",
            "name": "Test",
            "doc_type": "Report",
            "created_by": "user-1",
            "modified_by": "user-2",
        })

        doc = mapper.map(raw)

        assert doc.object_id == "doc-123"
        assert doc.name == "Test"

    def test_field_mapper_with_mapping(self):
        """Test field mapper with field name mapping."""
        mapper = FieldMapper(
            mapping={
                "object_id": "id",
                "name": "title",
                "doc_type": "category",
                "created_by": "author",
                "modified_by": "editor",
            }
        )
        raw = RawDocument.from_data({
            "id": "doc-456",
            "title": "My Document",
            "category": "Memo",
            "author": "jane",
            "editor": "bob",
        })

        doc = mapper.map(raw)

        assert doc.object_id == "doc-456"
        assert doc.name == "My Document"
        assert doc.doc_type == "Memo"
        assert doc.created_by == "jane"
        assert doc.modified_by == "bob"

    def test_field_mapper_with_defaults(self):
        """Test field mapper with default values."""
        mapper = FieldMapper(
            defaults={
                "doc_type": "Document",
                "created_by": "system",
                "modified_by": "system",
            }
        )
        raw = RawDocument.from_data({
            "object_id": "doc-123",
            "name": "Test",
            # No doc_type, created_by, modified_by
        })

        doc = mapper.map(raw)

        assert doc.doc_type == "Document"
        assert doc.created_by == "system"
        assert doc.modified_by == "system"

    def test_field_mapper_missing_required(self):
        """Test field mapper with missing required field."""
        mapper = FieldMapper(mapping={"object_id": "id"})
        raw = RawDocument.from_data({
            "id": "doc-123",
            "name": "Test",
            # Missing doc_type, created_by, modified_by
        })

        with pytest.raises(MapperError, match="Required field"):
            mapper.map(raw)


# =============================================================================
# Registry Tests
# =============================================================================


class TestMapperRegistry:
    """Test mapper registry."""

    def test_list_mappers(self):
        """Test listing available mappers."""
        mappers = list_mappers()
        assert "identity" in mappers
        assert "field" in mappers

    def test_get_mapper_identity(self):
        """Test getting identity mapper class."""
        mapper_class = get_mapper("identity")
        assert mapper_class is IdentityMapper

    def test_get_mapper_field(self):
        """Test getting field mapper class."""
        mapper_class = get_mapper("field")
        assert mapper_class is FieldMapper

    def test_get_mapper_not_found(self):
        """Test getting unknown mapper raises error."""
        with pytest.raises(MapperNotFoundError) as exc_info:
            get_mapper("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert "identity" in exc_info.value.available

    def test_get_mapper_info(self):
        """Test getting mapper info."""
        info = get_mapper_info("identity")

        assert info["name"] == "identity"
        assert "IdentityMapper" in info["class"]
        assert "description" in info


# =============================================================================
# Factory Tests
# =============================================================================


class TestMapperFactory:
    """Test mapper factory."""

    def test_create_mapper_default(self):
        """Test creating default mapper (identity)."""
        mapper = create_mapper()

        assert isinstance(mapper, IdentityMapper)

    def test_create_mapper_by_name_identity(self):
        """Test creating identity mapper by name."""
        mapper = create_mapper("identity")

        assert isinstance(mapper, IdentityMapper)

    def test_create_mapper_by_name_field(self):
        """Test creating field mapper by name."""
        mapper = create_mapper("field")

        assert isinstance(mapper, FieldMapper)

    def test_create_mapper_with_config(self):
        """Test creating field mapper with configuration."""
        mapper = create_mapper(
            "field",
            config={
                "mapping": {"object_id": "id"},
                "defaults": {"doc_type": "Test"},
            },
        )

        assert isinstance(mapper, FieldMapper)
        # Verify config was applied by mapping a document
        raw = RawDocument.from_data({
            "id": "123",
            "name": "Test",
            "created_by": "user",
            "modified_by": "user",
        })
        doc = mapper.map(raw)
        assert doc.object_id == "123"
        assert doc.doc_type == "Test"

    def test_create_mapper_unknown_name(self):
        """Test creating mapper with unknown name."""
        with pytest.raises(MapperNotFoundError):
            create_mapper("unknown_mapper")

    def test_create_mapper_module_not_found(self):
        """Test creating mapper from nonexistent module."""
        with pytest.raises(MapperLoadError, match="Module not found"):
            create_mapper(module_path="/nonexistent/path/mapper.py")

    def test_create_mapper_invalid_module_extension(self):
        """Test creating mapper from non-Python file."""
        with pytest.raises(MapperLoadError, match="must be a .py file"):
            create_mapper(module_path="/path/to/file.txt")


class TestGetAvailableMappers:
    """Test get_available_mappers function."""

    def test_returns_list_of_mapper_info(self):
        """Test that function returns list of mapper info dicts."""
        mappers = get_available_mappers()

        assert isinstance(mappers, list)
        assert len(mappers) >= 2  # At least identity and field

        # Check structure
        for info in mappers:
            assert "name" in info
            assert "class" in info
            assert "description" in info

    def test_includes_built_in_mappers(self):
        """Test that built-in mappers are included."""
        mappers = get_available_mappers()
        names = [m["name"] for m in mappers]

        assert "identity" in names
        assert "field" in names


# =============================================================================
# Integration Tests
# =============================================================================


class TestMapperIntegration:
    """Integration tests for mapper workflow."""

    def test_identity_mapper_to_event(self):
        """Test full workflow: raw -> document -> event."""
        mapper = IdentityMapper()
        raw = RawDocument.from_data({
            "object_id": "doc-integration-test",
            "name": "Integration Test Document",
            "doc_type": "TestReport",
            "created_by": "test-user",
            "modified_by": "test-user",
            "date_created": "2024-01-15T10:30:00Z",
            "date_modified": "2024-01-16T14:20:00Z",
            "properties": {"version": "1.0"},
        })

        # Map to document
        doc = mapper.map(raw)

        # Convert to event
        event = doc.to_event(source_id="test-source-id")

        assert event.object_id == "doc-integration-test"
        assert "name" in event.properties
        assert event.properties["name"].value == "Integration Test Document"

    def test_field_mapper_to_event(self):
        """Test field mapper workflow."""
        mapper = FieldMapper(
            mapping={
                "object_id": "document_id",
                "name": "document_title",
                "doc_type": "document_type",
                "created_by": "author",
                "modified_by": "last_editor",
            }
        )
        raw = RawDocument.from_data({
            "document_id": "mapped-doc-123",
            "document_title": "Mapped Document",
            "document_type": "MappedReport",
            "author": "mapper-user",
            "last_editor": "editor-user",
        })

        doc = mapper.map(raw)
        event = doc.to_event(source_id="test-source")

        assert event.object_id == "mapped-doc-123"
        assert event.properties["name"].value == "Mapped Document"
        assert event.properties["type"].value == "MappedReport"
