"""Directory reader for scanning local file systems."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .base import BaseReader, RawDocument

logger = logging.getLogger(__name__)

# Default file extensions to include
DEFAULT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".rtf",
    ".odt",
    ".xls",
    ".xlsx",
    ".csv",
    ".ppt",
    ".pptx",
    ".html",
    ".htm",
    ".xml",
    ".json",
    ".md",
}


class DirectoryReader(BaseReader):
    """Read documents by scanning a directory.

    Scans a directory for document files, optionally recursively.
    Files can be filtered by extension or glob pattern.

    Attributes:
        name: Reader identifier ("directory").
        description: Human-readable description.
    """

    name = "directory"
    description = "Scan a directory for document files"

    def read(
        self,
        source: str,
        *,
        recursive: bool = True,
        extensions: list[str] | str | None = None,
        pattern: str | None = None,
        **options: Any,
    ) -> Iterator[RawDocument]:
        """Read documents from a directory.

        Args:
            source: Path to the directory to scan.
            recursive: If True, scan subdirectories recursively.
            extensions: File extensions to include (e.g., [".pdf", ".docx"]).
                       Can be a comma-separated string.
            pattern: Glob pattern for filtering files (e.g., "*.pdf").
            **options: Additional options (unused).

        Yields:
            RawDocument instances for each file found.

        Raises:
            FileNotFoundError: If the source directory doesn't exist.
            NotADirectoryError: If the source is not a directory.
        """
        source_path = Path(source)

        if not source_path.exists():
            raise FileNotFoundError(f"Directory not found: {source}")

        if not source_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {source}")

        # Parse extensions
        ext_set = self._parse_extensions(extensions)

        logger.info(f"Scanning directory: {source} (recursive={recursive})")
        if ext_set:
            logger.debug(f"Filtering by extensions: {sorted(ext_set)}")
        if pattern:
            logger.debug(f"Using glob pattern: {pattern}")

        # Get files based on pattern or walk directory
        if pattern:
            files = self._glob_files(source_path, pattern, recursive)
        else:
            files = self._walk_directory(source_path, recursive)

        # Filter and yield documents
        count = 0
        for file_path in files:
            # Skip if extension filter is active and file doesn't match
            if ext_set and file_path.suffix.lower() not in ext_set:
                continue

            # Skip hidden files
            if file_path.name.startswith("."):
                continue

            # Create document with title from filename
            title = file_path.stem  # Filename without extension

            yield RawDocument(
                file_path=file_path,
                title=title,
                metadata={"relative_path": str(file_path.relative_to(source_path))},
            )
            count += 1

        logger.info(f"Found {count} documents in {source}")

    @classmethod
    def validate_source(cls, source: str) -> bool:
        """Check if this reader can handle the given source.

        Args:
            source: The source path.

        Returns:
            True if the source is an existing directory.
        """
        source_path = Path(source)
        return source_path.exists() and source_path.is_dir()

    def _parse_extensions(self, extensions: list[str] | str | None) -> set[str]:
        """Parse extension filter into a set.

        Args:
            extensions: Extension list or comma-separated string.

        Returns:
            Set of lowercase extensions (with leading dots).
        """
        if extensions is None:
            return DEFAULT_EXTENSIONS.copy()

        if isinstance(extensions, str):
            # Parse comma-separated string
            parts = [e.strip() for e in extensions.split(",")]
        else:
            parts = list(extensions)

        # Normalize: ensure leading dot and lowercase
        result: set[str] = set()
        for ext in parts:
            ext = ext.strip()
            if not ext:
                continue
            if not ext.startswith("."):
                ext = "." + ext
            result.add(ext.lower())

        return result

    def _walk_directory(
        self,
        directory: Path,
        recursive: bool,
    ) -> Iterator[Path]:
        """Walk directory and yield file paths.

        Args:
            directory: Directory to walk.
            recursive: If True, recurse into subdirectories.

        Yields:
            Path objects for each file.
        """
        if recursive:
            for path in directory.rglob("*"):
                if path.is_file():
                    yield path
        else:
            for path in directory.iterdir():
                if path.is_file():
                    yield path

    def _glob_files(
        self,
        directory: Path,
        pattern: str,
        recursive: bool,
    ) -> Iterator[Path]:
        """Find files matching a glob pattern.

        Args:
            directory: Directory to search.
            pattern: Glob pattern (e.g., "*.pdf", "**/*.pdf").
            recursive: If True and pattern doesn't include **, prepend it.

        Yields:
            Path objects for matching files.
        """
        # If recursive and pattern doesn't include **, use rglob
        if recursive and "**" not in pattern:
            for path in directory.rglob(pattern):
                if path.is_file():
                    yield path
        else:
            for path in directory.glob(pattern):
                if path.is_file():
                    yield path
