"""Integration test for CSV Reader with complete_manifest.csv."""

from pathlib import Path

import pytest

from ingest_cli.readers.csv_reader import CSVReader


def test_load_complete_manifest(capsys):
    """Test loading and displaying documents from complete_manifest.csv.
    
    This test demonstrates loading a complete CSV manifest with all required fields
    and prints the resulting RawDocument objects for verification.
    """
    # Get path to test CSV
    test_data_dir = Path(__file__).parent.parent / "data"
    csv_path = test_data_dir / "complete_manifest.csv"
    
    assert csv_path.exists(), f"Test CSV not found: {csv_path}"
    
    # Create CSV reader
    reader = CSVReader()
    
    # Read documents
    documents = list(reader.read(str(csv_path)))
    
    # Verify we got documents
    assert len(documents) > 0, "No documents were read from CSV"
    
    # Print header
    print("\n" + "=" * 80)
    print(f"Loaded {len(documents)} documents from complete_manifest.csv")
    print("=" * 80)
    
    # Print each document
    for i, doc in enumerate(documents, 1):
        print(f"\n--- Document {i} ---")
        print(f"File Path: {doc.file_path}")
        print(f"Title: {doc.title}")
        print(f"Source URL: {doc.source_url}")
        print(f"Metadata:")
        for key, value in sorted(doc.metadata.items()):
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 80)
    
    # Verify document structure
    for doc in documents:
        # All documents should have a file_path
        assert doc.file_path is not None
        
        # Check that metadata contains expected fields
        assert "object_id" in doc.metadata
        assert "doc_type" in doc.metadata
        
        # Verify file paths are Path objects
        assert isinstance(doc.file_path, Path)


def test_complete_manifest_field_coverage():
    """Verify complete_manifest.csv contains all expected fields."""
    test_data_dir = Path(__file__).parent.parent / "data"
    csv_path = test_data_dir / "complete_manifest.csv"
    
    reader = CSVReader()
    documents = list(reader.read(str(csv_path)))
    
    # Expected fields in the CSV (based on actual CSV structure)
    expected_metadata_fields = {
        "object_id",
        "doc_type",
        "created_by",
        "modified_by",
        "category",
        "author",
    }
    
    # Check first document has all fields
    first_doc = documents[0]
    
    # file_path and title are direct attributes
    assert first_doc.file_path is not None
    assert first_doc.title is not None
    
    # Other fields should be in metadata
    metadata_fields = set(first_doc.metadata.keys())
    
    missing_fields = expected_metadata_fields - metadata_fields
    assert not missing_fields, f"Missing expected fields: {missing_fields}"
    
    print(f"\n✓ All expected fields present in CSV")
    print(f"  - file_path (attribute)")
    print(f"  - title (attribute)")
    print(f"  - Metadata fields: {', '.join(sorted(expected_metadata_fields))}")


def test_complete_manifest_data_types():
    """Verify data types of fields in complete_manifest.csv."""
    test_data_dir = Path(__file__).parent.parent / "data"
    csv_path = test_data_dir / "complete_manifest.csv"
    
    reader = CSVReader()
    documents = list(reader.read(str(csv_path)))
    
    for doc in documents:
        # File path should be a Path object
        assert isinstance(doc.file_path, Path)
        
        # Title should be present and be a string
        assert doc.title is not None
        assert isinstance(doc.title, str)
        
        # source_url can be None or str
        if doc.source_url is not None:
            assert isinstance(doc.source_url, str)
        
        # Metadata should be a dict
        assert isinstance(doc.metadata, dict)
        
        # Check specific metadata fields
        assert isinstance(doc.metadata["object_id"], str)
        assert isinstance(doc.metadata["doc_type"], str)
        assert isinstance(doc.metadata["created_by"], str)
        assert isinstance(doc.metadata["modified_by"], str)
        assert isinstance(doc.metadata["category"], str)
        assert isinstance(doc.metadata["author"], str)
        
    print(f"\n✓ All data types are correct for {len(documents)} documents")


if __name__ == "__main__":
    # Allow running this test directly to see output
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
