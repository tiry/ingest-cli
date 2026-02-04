"""Base mapper interface for document transformation.

Mappers transform RawDocument (from readers) into Document (for API).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from ingest_cli.models import Document
from ingest_cli.readers.base import RawDocument


class MapperError(Exception):
    """Base exception for mapper errors."""

    pass


class MissingFieldError(MapperError):
    """Raised when a required field is missing."""

    def __init__(self, fields: list[str]) -> None:
        self.fields = fields
        super().__init__(f"Missing required fields: {', '.join(fields)}")


class BaseMapper(ABC):
    """Abstract base class for document mappers.

    Mappers transform RawDocument data into Document objects
    ready for API submission.

    Subclasses must implement:
    - name property
    - map() method
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this mapper.

        Returns:
            Mapper name used for registration and CLI.
        """
        pass

    @abstractmethod
    def map(self, raw: RawDocument) -> Document:
        """Transform a raw document into an API document.

        Args:
            raw: RawDocument from a reader

        Returns:
            Document ready for API submission

        Raises:
            MapperError: If transformation fails
            MissingFieldError: If required fields are missing
        """
        pass

    def validate_required_fields(
        self,
        data: dict[str, Any],
        required: list[str] | None = None,
    ) -> None:
        """Validate that required fields are present.

        Args:
            data: Source data dictionary
            required: List of required field names (defaults to standard fields)

        Raises:
            MissingFieldError: If any required field is missing or None
        """
        if required is None:
            required = [
                "object_id",
                "name",
                "doc_type",
                "created_by",
                "modified_by",
            ]

        missing = [f for f in required if f not in data or data[f] is None]
        if missing:
            raise MissingFieldError(missing)

    @staticmethod
    def parse_datetime(
        value: datetime | str | None,
        default: datetime | None = None,
    ) -> datetime:
        """Parse a datetime value from various formats.

        Args:
            value: Datetime object, ISO string, or None
            default: Default value if None (defaults to datetime.now())

        Returns:
            Parsed datetime object

        Raises:
            ValueError: If string cannot be parsed
        """
        if value is None:
            return default if default is not None else datetime.now()

        if isinstance(value, datetime):
            return value

        # Try ISO 8601 formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%fZ",  # With milliseconds and Z
            "%Y-%m-%dT%H:%M:%SZ",  # Without milliseconds
            "%Y-%m-%dT%H:%M:%S.%f",  # With milliseconds, no Z
            "%Y-%m-%dT%H:%M:%S",  # Basic ISO
            "%Y-%m-%d %H:%M:%S",  # Space separator
            "%Y-%m-%d",  # Date only
        ]:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        msg = f"Cannot parse datetime: {value}"
        raise ValueError(msg)

    @staticmethod
    def parse_path(value: str | Path | None) -> Path | None:
        """Parse a path value.

        Args:
            value: String path, Path object, or None

        Returns:
            Path object or None
        """
        if value is None:
            return None
        return Path(value) if isinstance(value, str) else value
