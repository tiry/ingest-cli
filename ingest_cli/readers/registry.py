"""Reader registry for discovery and auto-detection."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseReader

logger = logging.getLogger(__name__)


class ReaderRegistry:
    """Central registry for document readers.

    Provides methods to register, retrieve, and auto-detect readers.
    Can be used as a decorator for reader classes.

    Example:
        >>> @ReaderRegistry.register
        ... class MyReader(BaseReader):
        ...     name = "my-reader"
        ...     # ...

        >>> reader_cls = ReaderRegistry.get("my-reader")
        >>> reader = reader_cls()
    """

    _readers: dict[str, type[BaseReader]] = {}

    @classmethod
    def register(cls, reader_class: type[BaseReader]) -> type[BaseReader]:
        """Register a reader class.

        Can be used as a decorator:
            @ReaderRegistry.register
            class MyReader(BaseReader):
                ...

        Args:
            reader_class: The reader class to register.

        Returns:
            The same reader class (for decorator use).

        Raises:
            ValueError: If the reader has no name attribute.
        """
        name = getattr(reader_class, "name", None)
        if not name:
            raise ValueError(f"Reader {reader_class.__name__} must have a 'name' attribute")

        cls._readers[name] = reader_class
        logger.debug(f"Registered reader: {name}")
        return reader_class

    @classmethod
    def get(cls, name: str) -> type[BaseReader] | None:
        """Get a reader class by name.

        Args:
            name: The reader name (e.g., "csv", "json").

        Returns:
            The reader class, or None if not found.
        """
        return cls._readers.get(name)

    @classmethod
    def list_all(cls) -> list[type[BaseReader]]:
        """List all registered reader classes.

        Returns:
            List of reader classes, sorted by name.
        """
        return sorted(cls._readers.values(), key=lambda r: r.name)

    @classmethod
    def names(cls) -> list[str]:
        """Get all registered reader names.

        Returns:
            Sorted list of reader names.
        """
        return sorted(cls._readers.keys())

    @classmethod
    def auto_detect(cls, source: str) -> type[BaseReader] | None:
        """Auto-detect the appropriate reader for a source.

        Iterates through registered readers and returns the first
        one that can handle the source.

        Args:
            source: The source path or location.

        Returns:
            The reader class that can handle the source, or None.
        """
        for reader_class in cls._readers.values():
            try:
                if reader_class.validate_source(source):
                    logger.debug(f"Auto-detected reader '{reader_class.name}' for source: {source}")
                    return reader_class
            except Exception as e:
                logger.debug(f"Reader {reader_class.name} validation failed: {e}")
                continue

        logger.debug(f"No reader found for source: {source}")
        return None

    @classmethod
    def clear(cls) -> None:
        """Clear all registered readers (mainly for testing)."""
        cls._readers.clear()


def register_default_readers() -> None:
    """Register the built-in readers.

    This function is called during module initialization to
    register the CSV, JSON, and Directory readers.
    """
    # Import here to avoid circular imports
    from .csv_reader import CSVReader
    from .directory_reader import DirectoryReader
    from .json_reader import JSONReader

    ReaderRegistry.register(CSVReader)
    ReaderRegistry.register(JSONReader)
    ReaderRegistry.register(DirectoryReader)

    logger.debug("Default readers registered")
