"""Validation module for pre-flight checks."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from ingest_cli.config.settings import IngestSettings
    from ingest_cli.mappers.base import BaseMapper
    from ingest_cli.models.document import Document
    from ingest_cli.readers.base import BaseReader

# Type alias for settings
Settings = "IngestSettings"

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check.

    Attributes:
        valid: Whether validation passed (no errors).
        errors: List of error messages.
        warnings: List of warning messages.
    """

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add an error message and mark as invalid."""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def merge(self, other: ValidationResult) -> None:
        """Merge another result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.valid:
            self.valid = False


class PipelineValidator:
    """Validates pipeline configuration and input.

    Performs pre-flight checks to catch errors before
    actual API calls are made.
    """

    def __init__(self, sample_size: int = 5) -> None:
        """Initialize the validator.

        Args:
            sample_size: Number of documents to sample for validation.
        """
        self.sample_size = sample_size

    def validate_config(self, config: IngestSettings) -> ValidationResult:
        """Validate configuration settings.

        Args:
            config: Configuration settings to validate.

        Returns:
            ValidationResult with any errors/warnings.
        """
        result = ValidationResult()

        # Check required fields
        if not config.environment_id:
            result.add_error("Missing required field: environment_id")

        if not config.source_id:
            result.add_error("Missing required field: source_id")

        if not config.system_integration_id:
            result.add_error("Missing required field: system_integration_id")

        if not config.client_id:
            result.add_error("Missing required field: client_id")

        if not config.client_secret:
            result.add_error("Missing required field: client_secret")

        # Validate endpoints
        if config.ingest_endpoint:
            if not self._is_valid_url(config.ingest_endpoint):
                result.add_error(f"Invalid ingest_endpoint URL: {config.ingest_endpoint}")
        else:
            result.add_error("Missing required field: ingest_endpoint")

        if config.auth_endpoint:
            if not self._is_valid_url(config.auth_endpoint):
                result.add_error(f"Invalid auth_endpoint URL: {config.auth_endpoint}")
        else:
            result.add_error("Missing required field: auth_endpoint")

        # Validate batch_size
        if config.batch_size is not None:
            if config.batch_size < 1:
                result.add_error("batch_size must be at least 1")
            elif config.batch_size > 100:
                result.add_error("batch_size cannot exceed 100 (API limit)")

        return result

    def validate_input_file(self, input_path: Path) -> ValidationResult:
        """Validate input file exists and is readable.

        Args:
            input_path: Path to the input file.

        Returns:
            ValidationResult with any errors/warnings.
        """
        result = ValidationResult()

        if not input_path.exists():
            result.add_error(f"Input file not found: {input_path}")
            return result

        if not input_path.is_file():
            result.add_error(f"Input path is not a file: {input_path}")
            return result

        # Check readability
        try:
            with open(input_path, encoding="utf-8") as f:
                f.read(1)  # Try to read first byte
        except PermissionError:
            result.add_error(f"Permission denied reading: {input_path}")
        except UnicodeDecodeError:
            result.add_warning(f"File may not be UTF-8 encoded: {input_path}")
        except Exception as e:
            result.add_error(f"Cannot read file {input_path}: {e}")

        return result

    def validate_reader(
        self,
        reader: BaseReader,
        input_path: Path,
    ) -> ValidationResult:
        """Validate reader can parse the input file.

        Args:
            reader: Reader instance to test.
            input_path: Path to the input file.

        Returns:
            ValidationResult with any errors/warnings.
        """
        result = ValidationResult()

        try:
            # Try to read a few records
            records = list(self._take_n(reader.read(str(input_path)), self.sample_size))

            if not records:
                result.add_warning("Input file appears to be empty")
            else:
                logger.debug(
                    "Reader successfully parsed %d sample records",
                    len(records),
                )

        except Exception as e:
            result.add_error(f"Reader failed to parse input: {e}")

        return result

    def validate_mapper(
        self,
        mapper: BaseMapper,
        sample_docs: list[dict],
    ) -> ValidationResult:
        """Validate mapper transforms documents correctly.

        Args:
            mapper: Mapper instance to test.
            sample_docs: Sample documents to transform.

        Returns:
            ValidationResult with any errors/warnings.
        """
        result = ValidationResult()

        if not sample_docs:
            result.add_warning("No sample documents to validate mapper")
            return result

        for i, doc in enumerate(sample_docs):
            try:
                mapped = mapper.map(doc)  # type: ignore[arg-type]
                if mapped is None:
                    result.add_warning(f"Mapper returned None for document {i + 1}")
                elif not isinstance(mapped, dict):
                    result.add_error(
                        f"Mapper returned non-dict for document {i + 1}: {type(mapped).__name__}"
                    )
            except Exception as e:
                result.add_error(f"Mapper failed on document {i + 1}: {e}")

        return result

    def validate_document(self, document: Document) -> ValidationResult:
        """Validate a single document meets API requirements.

        Args:
            document: Document to validate.

        Returns:
            ValidationResult with any errors/warnings.
        """
        result = ValidationResult()

        # Check required fields (Document dataclass has typed attributes)
        if not document.object_id:
            result.add_error("Missing required field: object_id")

        if not document.name:
            result.add_error("Missing required field: name")

        if not document.doc_type:
            result.add_error("Missing required field: doc_type")

        if not document.created_by:
            result.add_error("Missing required field: created_by")

        if not document.modified_by:
            result.add_error("Missing required field: modified_by")

        # Validate file exists if path is set
        if document.file_path is not None:
            if not document.file_path.exists():
                result.add_error(f"File not found: {document.file_path}")

        return result

    def validate_documents(
        self,
        documents: list[Document],
    ) -> ValidationResult:
        """Validate multiple documents.

        Args:
            documents: Documents to validate.

        Returns:
            ValidationResult with any errors/warnings.
        """
        result = ValidationResult()

        for i, doc in enumerate(documents):
            doc_result = self.validate_document(doc)
            if not doc_result.valid:
                for error in doc_result.errors:
                    result.add_error(f"Document {i + 1}: {error}")
            for warning in doc_result.warnings:
                result.add_warning(f"Document {i + 1}: {warning}")

        return result

    def validate_all(
        self,
        config: IngestSettings,
        input_path: Path,
        reader: BaseReader,
        mapper: BaseMapper,
    ) -> ValidationResult:
        """Run all validation checks.

        Args:
            config: Configuration settings.
            input_path: Path to input file.
            reader: Reader instance.
            mapper: Mapper instance.

        Returns:
            Combined ValidationResult.
        """
        result = ValidationResult()

        # Config validation
        logger.info("Validating configuration...")
        config_result = self.validate_config(config)
        result.merge(config_result)

        # Input file validation
        logger.info("Validating input file...")
        input_result = self.validate_input_file(input_path)
        result.merge(input_result)

        if not input_result.valid:
            # Can't continue without valid input file
            return result

        # Reader validation
        logger.info("Validating reader...")
        reader_result = self.validate_reader(reader, input_path)
        result.merge(reader_result)

        if not reader_result.valid:
            # Can't continue if reader fails
            return result

        # Get sample documents for mapper validation
        try:
            sample_docs = list(self._take_n(reader.read(str(input_path)), self.sample_size))
        except Exception:
            sample_docs = []

        # Mapper validation
        logger.info("Validating mapper...")
        mapper_result = self.validate_mapper(mapper, sample_docs)
        result.merge(mapper_result)

        return result

    def _is_valid_url(self, url: str) -> bool:
        """Check if a string is a valid URL.

        Args:
            url: URL string to validate.

        Returns:
            True if valid URL with http/https scheme.
        """
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    def _take_n(self, iterator: Iterator, n: int) -> Iterator:
        """Take first n items from an iterator.

        Args:
            iterator: Source iterator.
            n: Maximum items to take.

        Yields:
            Up to n items from the iterator.
        """
        for i, item in enumerate(iterator):
            if i >= n:
                break
            yield item


def format_validation_result(result: ValidationResult) -> str:
    """Format a validation result for display.

    Args:
        result: ValidationResult to format.

    Returns:
        Formatted string for CLI output.
    """
    lines = []

    if result.valid:
        lines.append("✓ Validation passed")
    else:
        lines.append("✗ Validation failed")

    if result.errors:
        lines.append("")
        lines.append("Errors:")
        for error in result.errors:
            lines.append(f"  • {error}")

    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in result.warnings:
            lines.append(f"  ⚠ {warning}")

    return "\n".join(lines)
