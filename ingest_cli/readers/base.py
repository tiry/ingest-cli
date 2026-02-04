"""Base classes for document readers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger(__name__)


@dataclass
class RawDocument:
    """Raw document data from a reader.

    This is a simple container for document data before it is mapped
    to the API schema. It holds the file path and any metadata
    extracted from the source.

    Attributes:
        file_path: Path to the actual document file (optional for metadata-only).
        title: Optional document title.
        source_url: Optional URL where the document came from.
        metadata: Additional metadata as key-value pairs.
        content: Document content (loaded lazily if not provided).
    """

    file_path: Path | None = None
    title: str | None = None
    source_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    content: bytes | None = None

    def __post_init__(self) -> None:
        """Ensure file_path is a Path object if provided."""
        if self.file_path is not None and isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)

    @property
    def exists(self) -> bool:
        """Check if the file exists."""
        return self.file_path is not None and self.file_path.exists()

    @property
    def filename(self) -> str | None:
        """Get the filename without directory."""
        return self.file_path.name if self.file_path else None

    def load_content(self) -> bytes:
        """Load content from file_path if not already loaded.

        Returns:
            The file content as bytes.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If no file_path is set.
        """
        if self.content is None:
            if self.file_path is None:
                raise ValueError("No file_path set for this document")
            self.content = self.file_path.read_bytes()
        return self.content

    @property
    def data(self) -> dict[str, Any]:
        """Get all document data as a dictionary.

        Returns a dict combining file_path, title, source_url, and metadata.
        This is used by mappers for field transformation.

        Returns:
            Dict with all document data.
        """
        result = dict(self.metadata)
        if self.file_path:
            result.setdefault("file_path", self.file_path)
        if self.title:
            result.setdefault("title", self.title)
            result.setdefault("name", self.title)
        if self.source_url:
            result.setdefault("source_url", self.source_url)
        return result

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "RawDocument":
        """Create a RawDocument from a data dictionary.

        Args:
            data: Dict containing document data. Special keys:
                - file_path: Path to file
                - title: Document title
                - source_url: Source URL
                All other keys go into metadata.

        Returns:
            RawDocument instance.
        """
        file_path = data.pop("file_path", None)
        title = data.pop("title", None)
        source_url = data.pop("source_url", None)
        # Remaining data goes to metadata
        return cls(
            file_path=Path(file_path) if file_path else None,
            title=title,
            source_url=source_url,
            metadata=data,
        )


class BaseReader(ABC):
    """Abstract base class for all document readers.

    All reader implementations must inherit from this class and
    implement the abstract methods. The class provides metadata
    for CLI discovery and a common interface for reading documents.

    Class Attributes:
        name: Short name for the reader (e.g., "csv", "json").
        description: Human-readable description for CLI help.

    Example:
        >>> class MyReader(BaseReader):
        ...     name = "my-reader"
        ...     description = "Read from my custom source"
        ...
        ...     def read(self, source, **options):
        ...         # Implementation
        ...         pass
        ...
        ...     @classmethod
        ...     def validate_source(cls, source):
        ...         return source.endswith('.my')
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def read(self, source: str, **options: Any) -> Iterator[RawDocument]:
        """Read documents from the source.

        Args:
            source: The source path or location.
            **options: Reader-specific options.

        Yields:
            RawDocument instances for each document found.
        """
        pass

    @classmethod
    @abstractmethod
    def validate_source(cls, source: str) -> bool:
        """Check if this reader can handle the given source.

        This method is used for auto-detection of the appropriate
        reader for a given source.

        Args:
            source: The source path or location.

        Returns:
            True if this reader can handle the source.
        """
        pass

    def __repr__(self) -> str:
        """Return a string representation."""
        return f"<{self.__class__.__name__}(name={self.name!r})>"
