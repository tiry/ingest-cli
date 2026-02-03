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
        file_path: Path to the actual document file.
        title: Optional document title.
        source_url: Optional URL where the document came from.
        metadata: Additional metadata as key-value pairs.
        content: Document content (loaded lazily if not provided).
    """

    file_path: Path
    title: str | None = None
    source_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    content: bytes | None = None

    def __post_init__(self) -> None:
        """Ensure file_path is a Path object."""
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)

    @property
    def exists(self) -> bool:
        """Check if the file exists."""
        return self.file_path.exists()

    @property
    def filename(self) -> str:
        """Get the filename without directory."""
        return self.file_path.name

    def load_content(self) -> bytes:
        """Load content from file_path if not already loaded.

        Returns:
            The file content as bytes.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if self.content is None:
            self.content = self.file_path.read_bytes()
        return self.content


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
