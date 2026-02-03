"""JSON and JSONL file reader for document metadata."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Iterator

from .base import BaseReader, RawDocument

logger = logging.getLogger(__name__)


class JSONReader(BaseReader):
    """Read documents from JSON or JSONL files.

    Supports two formats:
    1. JSON array: A single JSON array of document objects
    2. JSONL: Newline-delimited JSON, one object per line

    Example JSON array format:
        [
          {"file_path": "/path/to/doc1.pdf", "title": "Document One"},
          {"file_path": "/path/to/doc2.pdf", "title": "Document Two"}
        ]

    Example JSONL format:
        {"file_path": "/path/to/doc1.pdf", "title": "Document One"}
        {"file_path": "/path/to/doc2.pdf", "title": "Document Two"}

    Attributes:
        name: Reader identifier ("json").
        description: Human-readable description.
    """

    name = "json"
    description = "Read document metadata from JSON or JSONL files"

    # Default field names
    DEFAULT_PATH_FIELD = "file_path"
    DEFAULT_TITLE_FIELD = "title"
    DEFAULT_URL_FIELD = "source_url"

    def read(
        self,
        source: str,
        *,
        path_field: str | None = None,
        title_field: str | None = None,
        url_field: str | None = None,
        skip_missing: bool = True,
        **options: Any,
    ) -> Iterator[RawDocument]:
        """Read documents from a JSON or JSONL file.

        Args:
            source: Path to the JSON/JSONL file.
            path_field: Name of the field containing file paths.
            title_field: Name of the field containing titles.
            url_field: Name of the field containing source URLs.
            skip_missing: If True, skip entries with missing files.
            **options: Additional options (unused).

        Yields:
            RawDocument instances for each valid entry.

        Raises:
            FileNotFoundError: If the source file doesn't exist.
            ValueError: If the JSON format is invalid.
        """
        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(f"JSON file not found: {source}")

        path_fld = path_field or self.DEFAULT_PATH_FIELD
        title_fld = title_field or self.DEFAULT_TITLE_FIELD
        url_fld = url_field or self.DEFAULT_URL_FIELD

        logger.info(f"Reading documents from JSON: {source}")

        # Detect format and parse
        if self._is_jsonl(source_path):
            entries = self._parse_jsonl(source_path)
        else:
            entries = self._parse_json_array(source_path)

        for entry_num, entry in enumerate(entries, start=1):
            doc = self._process_entry(
                entry,
                entry_num,
                path_fld,
                title_fld,
                url_fld,
                skip_missing,
            )
            if doc is not None:
                yield doc

    @classmethod
    def validate_source(cls, source: str) -> bool:
        """Check if this reader can handle the given source.

        Args:
            source: The source path.

        Returns:
            True if the source is a JSON or JSONL file.
        """
        source_lower = source.lower()
        return source_lower.endswith((".json", ".jsonl"))

    def _is_jsonl(self, file_path: Path) -> bool:
        """Detect if the file is JSONL format.

        Reads the first non-empty line and checks if it's a
        valid JSON object (not an array).

        Args:
            file_path: Path to the file.

        Returns:
            True if the file appears to be JSONL format.
        """
        try:
            with file_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # If first non-empty char is '[', it's a JSON array
                    return not line.startswith("[")
        except (OSError, UnicodeDecodeError):
            return False
        return False

    def _parse_json_array(self, file_path: Path) -> Iterator[dict[str, Any]]:
        """Parse a JSON array file.

        Args:
            file_path: Path to the JSON file.

        Yields:
            Dictionary entries from the array.

        Raises:
            ValueError: If the JSON is invalid or not an array.
        """
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}") from e

        if not isinstance(data, list):
            raise ValueError(f"JSON file must contain an array, got {type(data).__name__}")

        yield from data

    def _parse_jsonl(self, file_path: Path) -> Iterator[dict[str, Any]]:
        """Parse a JSONL (newline-delimited JSON) file.

        Args:
            file_path: Path to the JSONL file.

        Yields:
            Dictionary entries from each line.
        """
        with file_path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                    if isinstance(entry, dict):
                        yield entry
                    else:
                        entry_type = type(entry).__name__
                        logger.warning(
                            f"Line {line_num}: Expected object, got {entry_type}, skipping"
                        )
                except json.JSONDecodeError as e:
                    logger.warning(f"Line {line_num}: Invalid JSON: {e}, skipping")

    def _process_entry(
        self,
        entry: Any,
        entry_num: int,
        path_field: str,
        title_field: str,
        url_field: str,
        skip_missing: bool,
    ) -> RawDocument | None:
        """Process a single JSON entry.

        Args:
            entry: The JSON entry (should be a dict).
            entry_num: Entry number for logging.
            path_field: Field name for file path.
            title_field: Field name for title.
            url_field: Field name for source URL.
            skip_missing: Whether to skip missing files.

        Returns:
            RawDocument if valid, None if should be skipped.
        """
        if not isinstance(entry, dict):
            entry_type = type(entry).__name__
            logger.warning(f"Entry {entry_num}: Expected object, got {entry_type}, skipping")
            return None

        file_path_str = entry.get(path_field)
        if not file_path_str:
            logger.warning(f"Entry {entry_num}: Missing '{path_field}' field, skipping")
            return None

        file_path = Path(file_path_str)

        # Check if file exists
        if not file_path.exists():
            if skip_missing:
                logger.warning(f"Entry {entry_num}: File not found: {file_path}, skipping")
                return None
            else:
                raise FileNotFoundError(f"File not found: {file_path}")

        # Extract known fields
        title = entry.get(title_field) or None
        source_url = entry.get(url_field) or None

        # Collect remaining fields as metadata
        metadata: dict[str, Any] = {}
        known_fields = {path_field, title_field, url_field}
        for key, value in entry.items():
            if key not in known_fields and value is not None:
                metadata[key] = value

        return RawDocument(
            file_path=file_path,
            title=title,
            source_url=source_url,
            metadata=metadata,
        )
