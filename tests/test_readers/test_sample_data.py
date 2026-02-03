"""Integration tests using the sample test dataset."""

from pathlib import Path

import pytest

from ingest_cli.readers import CSVReader, DirectoryReader, create_reader

# Path to test data directory
TEST_DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture
def absolute_csv_manifest(tmp_path: Path) -> Path:
    """Create a CSV manifest with absolute paths to test documents.

    Returns:
        Path to the temporary CSV file.
    """
    docs_dir = TEST_DATA_DIR / "documents"

    csv_content = f"""file_path,title,category,author
{docs_dir}/report_q1_2024.txt,Q1 2024 Quarterly Report,Reports,Finance Team
{docs_dir}/user_guide_v2.txt,Product User Guide v2.0,Documentation,Technical Writing
{docs_dir}/technical_spec.txt,System Architecture Specification,Technical,Engineering Team
"""
    csv_file = tmp_path / "test_manifest.csv"
    csv_file.write_text(csv_content)
    return csv_file


class TestSampleDataset:
    """Integration tests using tests/data sample files."""

    def test_csv_reader_loads_sample_manifest(
        self, absolute_csv_manifest: Path
    ) -> None:
        """CSV reader correctly loads the sample manifest."""
        reader = CSVReader()
        docs = list(reader.read(str(absolute_csv_manifest)))

        # Should load all 3 documents
        assert len(docs) == 3

        # Check first document (Q1 Report)
        report = next(d for d in docs if "report" in d.filename.lower())
        assert report.title == "Q1 2024 Quarterly Report"
        assert report.metadata["category"] == "Reports"
        assert report.metadata["author"] == "Finance Team"
        assert report.exists

        # Check second document (User Guide)
        guide = next(d for d in docs if "user_guide" in d.filename.lower())
        assert guide.title == "Product User Guide v2.0"
        assert guide.metadata["category"] == "Documentation"
        assert guide.metadata["author"] == "Technical Writing"
        assert guide.exists

        # Check third document (Technical Spec)
        spec = next(d for d in docs if "technical" in d.filename.lower())
        assert spec.title == "System Architecture Specification"
        assert spec.metadata["category"] == "Technical"
        assert spec.metadata["author"] == "Engineering Team"
        assert spec.exists

    def test_csv_reader_loads_content_correctly(
        self, absolute_csv_manifest: Path
    ) -> None:
        """CSV reader can load file content."""
        reader = CSVReader()
        docs = list(reader.read(str(absolute_csv_manifest)))

        # Load content from the report
        report = next(d for d in docs if "report" in d.filename.lower())
        content = report.load_content()

        assert content is not None
        assert b"Quarterly Report" in content
        assert b"Q1 2024" in content
        assert b"Executive Summary" in content

    def test_directory_reader_scans_documents(self) -> None:
        """Directory reader correctly scans the documents folder."""
        docs_dir = TEST_DATA_DIR / "documents"

        reader = DirectoryReader()
        docs = list(reader.read(str(docs_dir), extensions=[".txt"]))

        # Should find all 3 documents
        assert len(docs) == 3

        filenames = {d.filename for d in docs}
        assert "report_q1_2024.txt" in filenames
        assert "user_guide_v2.txt" in filenames
        assert "technical_spec.txt" in filenames

        # Title should be derived from filename
        report = next(d for d in docs if "report" in d.filename)
        assert report.title == "report_q1_2024"

    def test_directory_reader_includes_relative_path(self) -> None:
        """Directory reader stores relative path in metadata."""
        docs_dir = TEST_DATA_DIR / "documents"

        reader = DirectoryReader()
        docs = list(reader.read(str(docs_dir), extensions=[".txt"]))

        for doc in docs:
            assert "relative_path" in doc.metadata
            # Relative path should just be the filename for flat directory
            assert doc.metadata["relative_path"] == doc.filename

    def test_auto_detect_csv_reader(self, absolute_csv_manifest: Path) -> None:
        """Factory auto-detects CSV reader from manifest file."""
        reader = create_reader(source=str(absolute_csv_manifest))
        assert isinstance(reader, CSVReader)

    def test_auto_detect_directory_reader(self) -> None:
        """Factory auto-detects directory reader from folder."""
        docs_dir = str(TEST_DATA_DIR / "documents")

        reader = create_reader(source=docs_dir)
        assert isinstance(reader, DirectoryReader)

    def test_all_documents_exist_and_readable(
        self, absolute_csv_manifest: Path
    ) -> None:
        """All documents in the sample dataset exist and are readable."""
        reader = CSVReader()
        docs = list(reader.read(str(absolute_csv_manifest)))

        for doc in docs:
            # Check file exists
            assert doc.exists, f"File does not exist: {doc.file_path}"

            # Check file is readable
            content = doc.load_content()
            assert content is not None
            assert len(content) > 0, f"File is empty: {doc.file_path}"

    def test_metadata_preservation(self, absolute_csv_manifest: Path) -> None:
        """Extra CSV columns are preserved as metadata."""
        reader = CSVReader()
        docs = list(reader.read(str(absolute_csv_manifest)))

        # All docs should have category and author metadata
        for doc in docs:
            assert "category" in doc.metadata
            assert "author" in doc.metadata
            assert doc.metadata["category"] in ["Reports", "Documentation", "Technical"]

    def test_content_verification(self, absolute_csv_manifest: Path) -> None:
        """Verify specific content in each document."""
        reader = CSVReader()
        docs = list(reader.read(str(absolute_csv_manifest)))

        # Check report content
        report = next(d for d in docs if "report" in d.filename.lower())
        content = report.load_content().decode("utf-8")
        assert "Executive Summary" in content
        assert "Revenue increased by 15%" in content

        # Check user guide content
        guide = next(d for d in docs if "user_guide" in d.filename.lower())
        content = guide.load_content().decode("utf-8")
        assert "Getting Started" in content
        assert "Dark mode theme support" in content

        # Check technical spec content
        spec = next(d for d in docs if "technical" in d.filename.lower())
        content = spec.load_content().decode("utf-8")
        assert "System Architecture" in content
        assert "Reader Module" in content
