"""CSV file reader for document metadata."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Iterator

from .base import BaseReader, RawDocument

logger = logging.getLogger(__name__)


class CSVReader(BaseReader):
    """Read documents from a CSV file.

    The CSV file should contain at least a column with file paths.
    Additional columns can be used for title, source URL, and
    custom metadata.

    Example CSV format:
        file_path,title,source_url,custom_field
        /path/to/doc1.pdf,Document One,https://example.com/doc1,value1
        /path/to/doc2.pdf,Document Two,https://example.com/doc2,value2

    Attributes:
        name: Reader identifier ("csv").
        description: Human-readable description.
    """

    name = "csv"
    description = "Read document paths and metadata from CSV files"

    # Default column names
    DEFAULT_PATH_COLUMN = "file_path"
    DEFAULT_TITLE_COLUMN = "title"
    DEFAULT_URL_COLUMN = "source_url"

    # Common delimiters for auto-detection
    DELIMITERS = [",", ";", "\t"]

    def read(
        self,
        source: str,
        *,
        path_column: str | None = None,
        title_column: str | None = None,
        url_column: str | None = None,
        skip_missing: bool = True,
        **options: Any,
    ) -> Iterator[RawDocument]:
        """Read documents from a CSV file.

        Args:
            source: Path to the CSV file.
            path_column: Name of the column containing file paths.
            title_column: Name of the column containing titles.
            url_column: Name of the column containing source URLs.
            skip_missing: If True, skip rows with missing files.
            **options: Additional options (unused).

        Yields:
            RawDocument instances for each valid row.

        Raises:
            FileNotFoundError: If the source CSV file doesn't exist.
        """
        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError(f"CSV file not found: {source}")

        path_col = path_column or self.DEFAULT_PATH_COLUMN
        title_col = title_column or self.DEFAULT_TITLE_COLUMN
        url_col = url_column or self.DEFAULT_URL_COLUMN

        logger.info(f"Reading documents from CSV: {source}")

        # Detect delimiter
        delimiter = self._detect_delimiter(source_path)
        logger.debug(f"Using delimiter: {delimiter!r}")

        with source_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)

            if reader.fieldnames is None:
                logger.warning(f"Empty CSV file: {source}")
                return

            # Validate required column exists
            if path_col not in reader.fieldnames:
                raise ValueError(
                    f"CSV file missing required column '{path_col}'. "
                    f"Available columns: {', '.join(reader.fieldnames)}"
                )

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                file_path_str = row.get(path_col, "").strip()

                if not file_path_str:
                    logger.warning(f"Row {row_num}: Empty file path, skipping")
                    continue

                file_path = Path(file_path_str)

                # Check if file exists
                if not file_path.exists():
                    if skip_missing:
                        logger.warning(f"Row {row_num}: File not found: {file_path}, skipping")
                        continue
                    else:
                        logger.error(f"Row {row_num}: File not found: {file_path}")
                        raise FileNotFoundError(f"File not found: {file_path}")

                # Extract known fields
                title = row.get(title_col, "").strip() or None
                source_url = row.get(url_col, "").strip() or None

                # Collect remaining fields as metadata
                metadata: dict[str, Any] = {}
                known_cols = {path_col, title_col, url_col}
                for col, value in row.items():
                    if col not in known_cols and value:
                        metadata[col] = value.strip()

                yield RawDocument(
                    file_path=file_path,
                    title=title,
                    source_url=source_url,
                    metadata=metadata,
                )

    @classmethod
    def validate_source(cls, source: str) -> bool:
        """Check if this reader can handle the given source.

        Args:
            source: The source path.

        Returns:
            True if the source is a CSV file.
        """
        source_lower = source.lower()
        return source_lower.endswith(".csv")

    def _detect_delimiter(self, file_path: Path) -> str:
        """Auto-detect the CSV delimiter.

        Reads the first line and uses csv.Sniffer to detect
        the delimiter. Falls back to comma if detection fails.

        Args:
            file_path: Path to the CSV file.

        Returns:
            The detected delimiter character.
        """
        try:
            with file_path.open("r", encoding="utf-8-sig") as f:
                # Read first few lines for detection
                sample = f.read(4096)

            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters="".join(self.DELIMITERS))
            return dialect.delimiter
        except (csv.Error, UnicodeDecodeError):
            logger.debug("Delimiter detection failed, using comma")
            return ","
