"""Document readers module.

This module provides a pluggable framework for reading documents
from various sources including CSV files, JSON/JSONL files, and
local directories.

Example:
    >>> from ingest_cli.readers import create_reader
    >>>
    >>> # Create a reader by type
    >>> reader = create_reader(reader_type="csv")
    >>> for doc in reader.read("documents.csv"):
    ...     print(doc.file_path, doc.title)
    >>>
    >>> # Auto-detect reader from source
    >>> reader = create_reader(source="/path/to/data.json")
    >>> for doc in reader.read("/path/to/data.json"):
    ...     print(doc.file_path)
"""

from .base import BaseReader, RawDocument
from .csv_reader import CSVReader
from .directory_reader import DirectoryReader
from .factory import ReaderNotFoundError, create_reader, get_reader_info
from .json_reader import JSONReader
from .registry import ReaderRegistry, register_default_readers

# Register default readers on import
register_default_readers()

__all__ = [
    # Base classes
    "BaseReader",
    "RawDocument",
    # Concrete readers
    "CSVReader",
    "JSONReader",
    "DirectoryReader",
    # Registry
    "ReaderRegistry",
    "register_default_readers",
    # Factory
    "create_reader",
    "get_reader_info",
    "ReaderNotFoundError",
]
