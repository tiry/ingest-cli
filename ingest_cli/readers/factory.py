"""Factory functions for creating readers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .registry import ReaderRegistry

if TYPE_CHECKING:
    from .base import BaseReader

logger = logging.getLogger(__name__)


class ReaderNotFoundError(Exception):
    """Raised when a reader cannot be found."""

    pass


def create_reader(
    reader_type: str | None = None,
    source: str | None = None,
) -> BaseReader:
    """Create a reader instance.

    Args:
        reader_type: Explicit reader type (e.g., "csv", "json", "directory").
                    If not provided, auto-detection is attempted.
        source: Source path (used for auto-detection if type not specified).

    Returns:
        A configured reader instance.

    Raises:
        ReaderNotFoundError: If the reader type is not found or
                            auto-detection fails.
        ValueError: If neither reader_type nor source is provided.
    """
    if reader_type:
        # Explicit reader type
        reader_class = ReaderRegistry.get(reader_type)
        if reader_class is None:
            available = ", ".join(ReaderRegistry.names())
            raise ReaderNotFoundError(
                f"Unknown reader type: '{reader_type}'. "
                f"Available readers: {available}"
            )
        logger.debug(f"Creating reader: {reader_type}")
        return reader_class()

    elif source:
        # Auto-detect from source
        reader_class = ReaderRegistry.auto_detect(source)
        if reader_class is None:
            available = ", ".join(ReaderRegistry.names())
            raise ReaderNotFoundError(
                f"Could not auto-detect reader for source: '{source}'. "
                f"Use --reader to specify one of: {available}"
            )
        logger.debug(f"Auto-detected reader: {reader_class.name}")
        return reader_class()

    else:
        raise ValueError("Either reader_type or source must be provided")


def get_reader_info() -> list[dict[str, str]]:
    """Get information about all registered readers.

    Returns:
        List of dicts with 'name' and 'description' keys.
    """
    return [{"name": r.name, "description": r.description} for r in ReaderRegistry.list_all()]
