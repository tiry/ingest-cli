"""Tests for document readers."""

import json
from pathlib import Path
from textwrap import dedent

import pytest

from ingest_cli.readers import (
    CSVReader,
    DirectoryReader,
    JSONReader,
    RawDocument,
    ReaderNotFoundError,
    ReaderRegistry,
    create_reader,
    get_reader_info,
)


class TestRawDocument:
    """Tests for RawDocument dataclass."""

    def test_create_with_path(self, tmp_path: Path) -> None:
        """Create RawDocument with Path object."""
        file = tmp_path / "test.txt"
        file.write_text("content")

        doc = RawDocument(file_path=file)
        assert doc.file_path == file
        assert doc.title is None
        assert doc.source_url is None
        assert doc.metadata == {}

    def test_create_with_string_path(self, tmp_path: Path) -> None:
        """Path string is converted to Path object."""
        file = tmp_path / "test.txt"
        file.write_text("content")

        doc = RawDocument(file_path=str(file))
        assert isinstance(doc.file_path, Path)
        assert doc.file_path == file

    def test_exists_property(self, tmp_path: Path) -> None:
        """Exists property checks file existence."""
        existing = tmp_path / "exists.txt"
        existing.write_text("content")
        missing = tmp_path / "missing.txt"

        assert RawDocument(file_path=existing).exists is True
        assert RawDocument(file_path=missing).exists is False

    def test_filename_property(self, tmp_path: Path) -> None:
        """Filename property returns just the filename."""
        file = tmp_path / "subdir" / "test.txt"
        file.parent.mkdir()
        file.write_text("content")

        doc = RawDocument(file_path=file)
        assert doc.filename == "test.txt"

    def test_load_content(self, tmp_path: Path) -> None:
        """Load content from file."""
        file = tmp_path / "test.txt"
        file.write_bytes(b"binary content")

        doc = RawDocument(file_path=file)
        assert doc.content is None  # Not loaded yet
        content = doc.load_content()
        assert content == b"binary content"
        assert doc.content == b"binary content"

    def test_load_content_caches(self, tmp_path: Path) -> None:
        """Content is cached after loading."""
        file = tmp_path / "test.txt"
        file.write_text("original")

        doc = RawDocument(file_path=file)
        doc.load_content()

        # Modify file
        file.write_text("modified")

        # Should return cached content
        assert doc.load_content() == b"original"


class TestCSVReader:
    """Tests for CSV reader."""

    def test_read_basic_csv(self, tmp_path: Path) -> None:
        """Read simple CSV with default columns."""
        file = tmp_path / "doc.txt"
        file.write_text("test content")

        csv_file = tmp_path / "data.csv"
        csv_file.write_text(f"file_path,title\n{file},Document One\n")

        reader = CSVReader()
        docs = list(reader.read(str(csv_file)))

        assert len(docs) == 1
        assert docs[0].file_path == file
        assert docs[0].title == "Document One"

    def test_csv_custom_columns(self, tmp_path: Path) -> None:
        """Read CSV with custom column names."""
        file = tmp_path / "doc.txt"
        file.write_text("test")

        csv_file = tmp_path / "data.csv"
        csv_file.write_text(f"path,name\n{file},My Doc\n")

        reader = CSVReader()
        docs = list(
            reader.read(
                str(csv_file),
                path_column="path",
                title_column="name",
            )
        )

        assert len(docs) == 1
        assert docs[0].title == "My Doc"

    def test_csv_missing_file_skipped(self, tmp_path: Path) -> None:
        """Missing files are skipped with skip_missing=True."""
        existing = tmp_path / "exists.txt"
        existing.write_text("content")

        csv_file = tmp_path / "data.csv"
        csv_file.write_text(
            dedent(f"""\
            file_path,title
            {existing},Existing
            /nonexistent/file.txt,Missing
        """)
        )

        reader = CSVReader()
        docs = list(reader.read(str(csv_file)))

        assert len(docs) == 1
        assert docs[0].title == "Existing"

    def test_csv_extra_columns_as_metadata(self, tmp_path: Path) -> None:
        """Extra columns are stored as metadata."""
        file = tmp_path / "doc.txt"
        file.write_text("content")

        csv_file = tmp_path / "data.csv"
        csv_file.write_text(f"file_path,title,category,author\n{file},Doc,Reports,John\n")

        reader = CSVReader()
        docs = list(reader.read(str(csv_file)))

        assert len(docs) == 1
        assert docs[0].metadata["category"] == "Reports"
        assert docs[0].metadata["author"] == "John"

    def test_csv_semicolon_delimiter(self, tmp_path: Path) -> None:
        """Auto-detect semicolon delimiter."""
        file = tmp_path / "doc.txt"
        file.write_text("content")

        csv_file = tmp_path / "data.csv"
        csv_file.write_text(f"file_path;title\n{file};Document\n")

        reader = CSVReader()
        docs = list(reader.read(str(csv_file)))

        assert len(docs) == 1
        assert docs[0].title == "Document"

    def test_csv_file_not_found(self, tmp_path: Path) -> None:
        """Error when CSV file doesn't exist."""
        reader = CSVReader()
        with pytest.raises(FileNotFoundError):
            list(reader.read(str(tmp_path / "nonexistent.csv")))

    def test_csv_missing_required_column(self, tmp_path: Path) -> None:
        """Error when required column is missing."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name,value\na,1\n")

        reader = CSVReader()
        with pytest.raises(ValueError, match="missing required column"):
            list(reader.read(str(csv_file)))

    def test_csv_validate_source(self) -> None:
        """Validate source checks file extension."""
        assert CSVReader.validate_source("data.csv") is True
        assert CSVReader.validate_source("data.CSV") is True
        assert CSVReader.validate_source("data.json") is False
        assert CSVReader.validate_source("/path/to/file.csv") is True


class TestJSONReader:
    """Tests for JSON reader."""

    def test_json_read_array(self, tmp_path: Path) -> None:
        """Read JSON array format."""
        file = tmp_path / "doc.txt"
        file.write_text("content")

        json_file = tmp_path / "data.json"
        json_file.write_text(
            json.dumps(
                [
                    {"file_path": str(file), "title": "Document One"},
                ]
            )
        )

        reader = JSONReader()
        docs = list(reader.read(str(json_file)))

        assert len(docs) == 1
        assert docs[0].file_path == file
        assert docs[0].title == "Document One"

    def test_jsonl_read(self, tmp_path: Path) -> None:
        """Read JSONL format."""
        file1 = tmp_path / "doc1.txt"
        file2 = tmp_path / "doc2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        jsonl_file = tmp_path / "data.jsonl"
        jsonl_file.write_text(
            f'{{"file_path": "{file1}", "title": "Doc 1"}}\n'
            f'{{"file_path": "{file2}", "title": "Doc 2"}}\n'
        )

        reader = JSONReader()
        docs = list(reader.read(str(jsonl_file)))

        assert len(docs) == 2
        assert docs[0].title == "Doc 1"
        assert docs[1].title == "Doc 2"

    def test_json_extra_fields_as_metadata(self, tmp_path: Path) -> None:
        """Extra fields stored as metadata."""
        file = tmp_path / "doc.txt"
        file.write_text("content")

        json_file = tmp_path / "data.json"
        json_file.write_text(
            json.dumps(
                [
                    {"file_path": str(file), "category": "Reports", "priority": 1},
                ]
            )
        )

        reader = JSONReader()
        docs = list(reader.read(str(json_file)))

        assert docs[0].metadata["category"] == "Reports"
        assert docs[0].metadata["priority"] == 1

    def test_json_missing_file_skipped(self, tmp_path: Path) -> None:
        """Missing files are skipped."""
        json_file = tmp_path / "data.json"
        json_file.write_text(
            json.dumps(
                [
                    {"file_path": "/nonexistent/file.txt", "title": "Missing"},
                ]
            )
        )

        reader = JSONReader()
        docs = list(reader.read(str(json_file)))

        assert len(docs) == 0

    def test_json_invalid_entry_skipped(self, tmp_path: Path) -> None:
        """Invalid entries in JSONL are skipped."""
        file = tmp_path / "doc.txt"
        file.write_text("content")

        jsonl_file = tmp_path / "data.jsonl"
        jsonl_file.write_text(
            f'{{"file_path": "{file}", "title": "Valid"}}\n'
            "not valid json\n"
            '{"title": "Missing path"}\n'
        )

        reader = JSONReader()
        docs = list(reader.read(str(jsonl_file)))

        assert len(docs) == 1
        assert docs[0].title == "Valid"

    def test_json_validate_source(self) -> None:
        """Validate source checks file extension."""
        assert JSONReader.validate_source("data.json") is True
        assert JSONReader.validate_source("data.jsonl") is True
        assert JSONReader.validate_source("data.JSON") is True
        assert JSONReader.validate_source("data.csv") is False


class TestDirectoryReader:
    """Tests for directory reader."""

    def test_directory_read_flat(self, tmp_path: Path) -> None:
        """Read files from flat directory."""
        (tmp_path / "doc1.txt").write_text("content1")
        (tmp_path / "doc2.txt").write_text("content2")

        reader = DirectoryReader()
        docs = list(reader.read(str(tmp_path), recursive=False, extensions=[".txt"]))

        assert len(docs) == 2
        filenames = {d.filename for d in docs}
        assert "doc1.txt" in filenames
        assert "doc2.txt" in filenames

    def test_directory_read_recursive(self, tmp_path: Path) -> None:
        """Read files recursively."""
        (tmp_path / "doc1.txt").write_text("content1")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "doc2.txt").write_text("content2")

        reader = DirectoryReader()
        docs = list(reader.read(str(tmp_path), recursive=True, extensions=[".txt"]))

        assert len(docs) == 2
        filenames = {d.filename for d in docs}
        assert "doc1.txt" in filenames
        assert "doc2.txt" in filenames

    def test_directory_filter_extensions(self, tmp_path: Path) -> None:
        """Filter by file extension."""
        (tmp_path / "doc.txt").write_text("content")
        (tmp_path / "doc.pdf").write_text("pdf content")
        (tmp_path / "doc.docx").write_text("docx content")

        reader = DirectoryReader()
        docs = list(reader.read(str(tmp_path), extensions=[".txt", ".pdf"]))

        assert len(docs) == 2
        filenames = {d.filename for d in docs}
        assert "doc.txt" in filenames
        assert "doc.pdf" in filenames
        assert "doc.docx" not in filenames

    def test_directory_extension_string(self, tmp_path: Path) -> None:
        """Extension can be comma-separated string."""
        (tmp_path / "doc.txt").write_text("content")
        (tmp_path / "doc.md").write_text("markdown")

        reader = DirectoryReader()
        docs = list(reader.read(str(tmp_path), extensions="txt,md"))

        assert len(docs) == 2

    def test_directory_title_from_filename(self, tmp_path: Path) -> None:
        """Title is derived from filename."""
        (tmp_path / "My Document.txt").write_text("content")

        reader = DirectoryReader()
        docs = list(reader.read(str(tmp_path), extensions=[".txt"]))

        assert len(docs) == 1
        assert docs[0].title == "My Document"

    def test_directory_relative_path_in_metadata(self, tmp_path: Path) -> None:
        """Relative path stored in metadata."""
        subdir = tmp_path / "reports" / "2024"
        subdir.mkdir(parents=True)
        (subdir / "report.txt").write_text("content")

        reader = DirectoryReader()
        docs = list(reader.read(str(tmp_path), extensions=[".txt"]))

        assert len(docs) == 1
        assert docs[0].metadata["relative_path"] == "reports/2024/report.txt"

    def test_directory_skip_hidden_files(self, tmp_path: Path) -> None:
        """Hidden files are skipped."""
        (tmp_path / "visible.txt").write_text("visible")
        (tmp_path / ".hidden.txt").write_text("hidden")

        reader = DirectoryReader()
        docs = list(reader.read(str(tmp_path), extensions=[".txt"]))

        assert len(docs) == 1
        assert docs[0].filename == "visible.txt"

    def test_directory_not_found(self, tmp_path: Path) -> None:
        """Error when directory doesn't exist."""
        reader = DirectoryReader()
        with pytest.raises(FileNotFoundError):
            list(reader.read(str(tmp_path / "nonexistent")))

    def test_directory_not_a_directory(self, tmp_path: Path) -> None:
        """Error when path is not a directory."""
        file = tmp_path / "file.txt"
        file.write_text("content")

        reader = DirectoryReader()
        with pytest.raises(NotADirectoryError):
            list(reader.read(str(file)))

    def test_directory_validate_source(self, tmp_path: Path) -> None:
        """Validate source checks if path is directory."""
        (tmp_path / "file.txt").write_text("content")

        assert DirectoryReader.validate_source(str(tmp_path)) is True
        assert DirectoryReader.validate_source(str(tmp_path / "file.txt")) is False
        assert DirectoryReader.validate_source("/nonexistent") is False


class TestReaderRegistry:
    """Tests for reader registry."""

    def test_get_reader_by_name(self) -> None:
        """Get reader class by name."""
        csv_reader = ReaderRegistry.get("csv")
        assert csv_reader is CSVReader

        json_reader = ReaderRegistry.get("json")
        assert json_reader is JSONReader

        dir_reader = ReaderRegistry.get("directory")
        assert dir_reader is DirectoryReader

    def test_get_unknown_reader(self) -> None:
        """Unknown reader returns None."""
        assert ReaderRegistry.get("unknown") is None

    def test_list_all_readers(self) -> None:
        """List all registered readers."""
        readers = ReaderRegistry.list_all()
        names = [r.name for r in readers]

        assert "csv" in names
        assert "json" in names
        assert "directory" in names

    def test_auto_detect_csv(self, tmp_path: Path) -> None:
        """Auto-detect CSV reader."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("file_path\n")

        reader_class = ReaderRegistry.auto_detect(str(csv_file))
        assert reader_class is CSVReader

    def test_auto_detect_json(self, tmp_path: Path) -> None:
        """Auto-detect JSON reader."""
        json_file = tmp_path / "data.json"
        json_file.write_text("[]")

        reader_class = ReaderRegistry.auto_detect(str(json_file))
        assert reader_class is JSONReader

    def test_auto_detect_directory(self, tmp_path: Path) -> None:
        """Auto-detect directory reader."""
        reader_class = ReaderRegistry.auto_detect(str(tmp_path))
        assert reader_class is DirectoryReader


class TestCreateReader:
    """Tests for reader factory function."""

    def test_create_by_type(self) -> None:
        """Create reader by explicit type."""
        reader = create_reader(reader_type="csv")
        assert isinstance(reader, CSVReader)

    def test_create_unknown_type(self) -> None:
        """Error for unknown reader type."""
        with pytest.raises(ReaderNotFoundError, match="Unknown reader type"):
            create_reader(reader_type="unknown")

    def test_create_auto_detect(self, tmp_path: Path) -> None:
        """Create reader by auto-detection."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("file_path\n")

        reader = create_reader(source=str(csv_file))
        assert isinstance(reader, CSVReader)

    def test_create_no_args(self) -> None:
        """Error when no arguments provided."""
        with pytest.raises(ValueError):
            create_reader()


class TestGetReaderInfo:
    """Tests for get_reader_info function."""

    def test_returns_reader_info(self) -> None:
        """Returns info for all readers."""
        info = get_reader_info()

        assert len(info) >= 3  # At least csv, json, directory
        names = [r["name"] for r in info]
        assert "csv" in names
        assert "json" in names
        assert "directory" in names

        # Check structure
        for reader in info:
            assert "name" in reader
            assert "description" in reader
