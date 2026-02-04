"""Tests for validation module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ingest_cli.config.settings import IngestSettings as Settings
from ingest_cli.models.document import Document
from ingest_cli.validation.validator import (
    PipelineValidator,
    ValidationResult,
    format_validation_result,
)

# =============================================================================
# ValidationResult Tests
# =============================================================================


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_default_is_valid(self) -> None:
        """Default result should be valid."""
        result = ValidationResult()
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error_marks_invalid(self) -> None:
        """Adding an error should mark result as invalid."""
        result = ValidationResult()
        result.add_error("Something went wrong")

        assert result.valid is False
        assert "Something went wrong" in result.errors

    def test_add_warning_keeps_valid(self) -> None:
        """Adding a warning should not mark result as invalid."""
        result = ValidationResult()
        result.add_warning("Minor issue")

        assert result.valid is True
        assert "Minor issue" in result.warnings

    def test_merge_combines_errors(self) -> None:
        """Merging should combine errors from both results."""
        result1 = ValidationResult()
        result1.add_error("Error 1")

        result2 = ValidationResult()
        result2.add_error("Error 2")

        result1.merge(result2)

        assert result1.valid is False
        assert "Error 1" in result1.errors
        assert "Error 2" in result1.errors

    def test_merge_combines_warnings(self) -> None:
        """Merging should combine warnings from both results."""
        result1 = ValidationResult()
        result1.add_warning("Warning 1")

        result2 = ValidationResult()
        result2.add_warning("Warning 2")

        result1.merge(result2)

        assert result1.valid is True
        assert "Warning 1" in result1.warnings
        assert "Warning 2" in result1.warnings

    def test_merge_invalid_result_makes_invalid(self) -> None:
        """Merging an invalid result should make the merged result invalid."""
        result1 = ValidationResult()  # valid

        result2 = ValidationResult()
        result2.add_error("Error")

        result1.merge(result2)

        assert result1.valid is False


# =============================================================================
# PipelineValidator - Config Validation Tests
# =============================================================================


class TestConfigValidation:
    """Tests for configuration validation."""

    @pytest.fixture
    def validator(self) -> PipelineValidator:
        """Create a validator instance."""
        return PipelineValidator()

    @pytest.fixture
    def valid_config(self) -> Settings:
        """Create a valid configuration."""
        return Settings(
            environment_id="12345678-1234-1234-1234-123456789abc",
            source_id="12345678-1234-1234-1234-123456789def",
            system_integration_id="12345678-1234-1234-1234-123456789012",
            client_id="client-abc",
            client_secret="secret-xyz",
            ingest_endpoint="https://api.example.com",
            auth_endpoint="https://auth.example.com",
            batch_size=50,
        )

    def test_valid_config_passes(
        self, validator: PipelineValidator, valid_config: Settings
    ) -> None:
        """Valid configuration should pass validation."""
        result = validator.validate_config(valid_config)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_environment_id(
        self, validator: PipelineValidator, valid_config: Settings
    ) -> None:
        """Missing environment_id should fail."""
        valid_config.environment_id = ""
        result = validator.validate_config(valid_config)

        assert result.valid is False
        assert any("environment_id" in e for e in result.errors)

    def test_missing_source_id(self, validator: PipelineValidator, valid_config: Settings) -> None:
        """Missing source_id should fail."""
        valid_config.source_id = ""
        result = validator.validate_config(valid_config)

        assert result.valid is False
        assert any("source_id" in e for e in result.errors)

    def test_missing_client_credentials(
        self, validator: PipelineValidator, valid_config: Settings
    ) -> None:
        """Missing client credentials should fail."""
        valid_config.client_id = ""
        valid_config.client_secret = ""
        result = validator.validate_config(valid_config)

        assert result.valid is False
        assert any("client_id" in e for e in result.errors)
        assert any("client_secret" in e for e in result.errors)

    def test_invalid_ingest_endpoint(
        self, validator: PipelineValidator, valid_config: Settings
    ) -> None:
        """Invalid ingest endpoint URL should fail."""
        valid_config.ingest_endpoint = "not-a-url"
        result = validator.validate_config(valid_config)

        assert result.valid is False
        assert any("ingest_endpoint" in e for e in result.errors)

    def test_invalid_auth_endpoint(
        self, validator: PipelineValidator, valid_config: Settings
    ) -> None:
        """Invalid auth endpoint URL should fail."""
        valid_config.auth_endpoint = "invalid"
        result = validator.validate_config(valid_config)

        assert result.valid is False
        assert any("auth_endpoint" in e for e in result.errors)

    def test_batch_size_too_small(
        self, validator: PipelineValidator, valid_config: Settings
    ) -> None:
        """Batch size less than 1 should fail."""
        valid_config.batch_size = 0
        result = validator.validate_config(valid_config)

        assert result.valid is False
        assert any("batch_size" in e for e in result.errors)

    def test_batch_size_too_large(
        self, validator: PipelineValidator, valid_config: Settings
    ) -> None:
        """Batch size greater than 100 should fail."""
        valid_config.batch_size = 101
        result = validator.validate_config(valid_config)

        assert result.valid is False
        assert any("batch_size" in e for e in result.errors)


# =============================================================================
# PipelineValidator - Input File Validation Tests
# =============================================================================


class TestInputFileValidation:
    """Tests for input file validation."""

    @pytest.fixture
    def validator(self) -> PipelineValidator:
        """Create a validator instance."""
        return PipelineValidator()

    def test_existing_file_passes(self, validator: PipelineValidator, tmp_path: Path) -> None:
        """Existing readable file should pass."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2")

        result = validator.validate_input_file(test_file)
        assert result.valid is True

    def test_missing_file_fails(self, validator: PipelineValidator) -> None:
        """Missing file should fail."""
        result = validator.validate_input_file(Path("/nonexistent/file.csv"))

        assert result.valid is False
        assert any("not found" in e for e in result.errors)

    def test_directory_fails(self, validator: PipelineValidator, tmp_path: Path) -> None:
        """Directory path (not file) should fail."""
        result = validator.validate_input_file(tmp_path)

        assert result.valid is False
        assert any("not a file" in e for e in result.errors)


# =============================================================================
# PipelineValidator - Reader Validation Tests
# =============================================================================


class TestReaderValidation:
    """Tests for reader validation."""

    @pytest.fixture
    def validator(self) -> PipelineValidator:
        """Create a validator instance."""
        return PipelineValidator()

    def test_working_reader_passes(self, validator: PipelineValidator, tmp_path: Path) -> None:
        """Reader that can parse file should pass."""
        # Create mock reader
        mock_reader = MagicMock()
        mock_reader.read.return_value = iter([{"col": "val1"}, {"col": "val2"}])

        test_file = tmp_path / "test.csv"
        test_file.write_text("col\nval1\nval2")

        result = validator.validate_reader(mock_reader, test_file)
        assert result.valid is True

    def test_empty_file_warns(self, validator: PipelineValidator, tmp_path: Path) -> None:
        """Empty file should produce warning."""
        mock_reader = MagicMock()
        mock_reader.read.return_value = iter([])

        test_file = tmp_path / "empty.csv"
        test_file.write_text("")

        result = validator.validate_reader(mock_reader, test_file)

        assert result.valid is True  # Warning, not error
        assert any("empty" in w for w in result.warnings)

    def test_reader_error_fails(self, validator: PipelineValidator, tmp_path: Path) -> None:
        """Reader that throws error should fail."""
        mock_reader = MagicMock()
        mock_reader.read.side_effect = ValueError("Parse error")

        test_file = tmp_path / "bad.csv"
        test_file.write_text("invalid")

        result = validator.validate_reader(mock_reader, test_file)

        assert result.valid is False
        assert any("failed to parse" in e.lower() for e in result.errors)


# =============================================================================
# PipelineValidator - Mapper Validation Tests
# =============================================================================


class TestMapperValidation:
    """Tests for mapper validation."""

    @pytest.fixture
    def validator(self) -> PipelineValidator:
        """Create a validator instance."""
        return PipelineValidator()

    def test_working_mapper_passes(self, validator: PipelineValidator) -> None:
        """Mapper that transforms correctly should pass."""
        mock_mapper = MagicMock()
        mock_mapper.map.return_value = {"name": "test"}

        sample_docs = [{"input": "data"}]
        result = validator.validate_mapper(mock_mapper, sample_docs)

        assert result.valid is True

    def test_mapper_returning_none_warns(self, validator: PipelineValidator) -> None:
        """Mapper returning None should warn."""
        mock_mapper = MagicMock()
        mock_mapper.map.return_value = None

        sample_docs = [{"input": "data"}]
        result = validator.validate_mapper(mock_mapper, sample_docs)

        assert result.valid is True  # Warning, not error
        assert any("None" in w for w in result.warnings)

    def test_mapper_error_fails(self, validator: PipelineValidator) -> None:
        """Mapper that throws error should fail."""
        mock_mapper = MagicMock()
        mock_mapper.map.side_effect = KeyError("missing_field")

        sample_docs = [{"input": "data"}]
        result = validator.validate_mapper(mock_mapper, sample_docs)

        assert result.valid is False
        assert any("failed" in e.lower() for e in result.errors)

    def test_empty_sample_warns(self, validator: PipelineValidator) -> None:
        """Empty sample docs should warn."""
        mock_mapper = MagicMock()

        result = validator.validate_mapper(mock_mapper, [])

        assert result.valid is True
        assert any("No sample" in w for w in result.warnings)


# =============================================================================
# PipelineValidator - Document Validation Tests
# =============================================================================


class TestDocumentValidation:
    """Tests for document validation."""

    @pytest.fixture
    def validator(self) -> PipelineValidator:
        """Create a validator instance."""
        return PipelineValidator()

    @pytest.fixture
    def valid_document(self) -> Document:
        """Create a valid document with all required fields."""
        return Document(
            object_id="doc-001",
            name="Test Document",
            doc_type="Report",
            date_created=datetime.now(),
            created_by="user@example.com",
            date_modified=datetime.now(),
            modified_by="user@example.com",
        )

    def test_valid_document_passes(
        self, validator: PipelineValidator, valid_document: Document
    ) -> None:
        """Document with all required fields should pass."""
        result = validator.validate_document(valid_document)
        assert result.valid is True

    def test_empty_object_id_fails(self, validator: PipelineValidator) -> None:
        """Document with empty object_id should fail."""
        doc = Document(
            object_id="",  # Empty
            name="Test",
            doc_type="Report",
            date_created=datetime.now(),
            created_by="user",
            date_modified=datetime.now(),
            modified_by="user",
        )

        result = validator.validate_document(doc)

        assert result.valid is False
        assert any("object_id" in e for e in result.errors)

    def test_empty_name_fails(self, validator: PipelineValidator) -> None:
        """Document with empty name should fail."""
        doc = Document(
            object_id="doc-001",
            name="",  # Empty
            doc_type="Report",
            date_created=datetime.now(),
            created_by="user",
            date_modified=datetime.now(),
            modified_by="user",
        )

        result = validator.validate_document(doc)

        assert result.valid is False
        assert any("name" in e for e in result.errors)

    def test_missing_file_fails(
        self, validator: PipelineValidator, valid_document: Document
    ) -> None:
        """Document with non-existent file_path should fail."""
        # Manually set file_path to a non-existent path
        valid_document.file_path = Path("/nonexistent/file.pdf")
        valid_document.file_content_type = "application/pdf"

        result = validator.validate_document(valid_document)

        assert result.valid is False
        assert any("file not found" in e.lower() for e in result.errors)

    def test_existing_file_passes(
        self,
        validator: PipelineValidator,
        valid_document: Document,
        tmp_path: Path,
    ) -> None:
        """Document with existing file reference should pass."""
        test_file = tmp_path / "doc.pdf"
        test_file.write_bytes(b"PDF content")

        valid_document.file_path = test_file
        valid_document.file_content_type = "application/pdf"

        result = validator.validate_document(valid_document)
        assert result.valid is True


# =============================================================================
# Format Validation Result Tests
# =============================================================================


class TestFormatValidationResult:
    """Tests for format_validation_result function."""

    def test_valid_result_shows_passed(self) -> None:
        """Valid result should show passed message."""
        result = ValidationResult()
        output = format_validation_result(result)

        assert "passed" in output.lower()
        assert "✓" in output

    def test_invalid_result_shows_failed(self) -> None:
        """Invalid result should show failed message."""
        result = ValidationResult()
        result.add_error("Something wrong")
        output = format_validation_result(result)

        assert "failed" in output.lower()
        assert "✗" in output

    def test_errors_are_listed(self) -> None:
        """Errors should be listed in output."""
        result = ValidationResult()
        result.add_error("Error one")
        result.add_error("Error two")
        output = format_validation_result(result)

        assert "Error one" in output
        assert "Error two" in output
        assert "Errors:" in output

    def test_warnings_are_listed(self) -> None:
        """Warnings should be listed in output."""
        result = ValidationResult()
        result.add_warning("Warning one")
        output = format_validation_result(result)

        assert "Warning one" in output
        assert "Warnings:" in output
        assert "⚠" in output
