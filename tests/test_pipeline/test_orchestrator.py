"""Tests for the pipeline orchestrator."""

from typing import Any, Iterator
from unittest.mock import MagicMock

import pytest

from ingest_cli.api import IngestionResponse
from ingest_cli.mappers import BaseMapper, IdentityMapper
from ingest_cli.models import Document
from ingest_cli.pipeline import (
    BatchResult,
    IngestionPipeline,
    PipelineConfig,
    PipelineError,
    PipelineResult,
    create_pipeline,
)
from ingest_cli.readers import BaseReader
from ingest_cli.readers.base import RawDocument


class MockReader(BaseReader):
    """Mock reader for testing."""

    name = "mock"
    description = "Mock reader for testing"

    def __init__(self, documents: list[RawDocument]) -> None:
        self._documents = documents
        self.read_called = False
        self.last_source: str | None = None

    @classmethod
    def validate_source(cls, source: str) -> bool:
        """Always valid for mock."""
        return True

    def read(self, source: str, **options: Any) -> Iterator[RawDocument]:
        self.read_called = True
        self.last_source = source
        yield from self._documents


class ErrorMapper(BaseMapper):
    """Mapper that raises errors for testing."""

    @property
    def name(self) -> str:
        return "error-mapper"

    def __init__(self, error_on_index: int = 1) -> None:
        self._error_index = error_on_index
        self._call_count = 0

    def map(self, raw: RawDocument) -> Document:
        from datetime import datetime

        self._call_count += 1
        if self._call_count == self._error_index:
            raise ValueError("Test mapping error")
        # Return a valid Document with all required fields
        data = raw.data
        now = datetime.now()
        return Document(
            object_id=data.get("object_id", f"doc-{self._call_count}"),
            name=data.get("name", "Test Doc"),
            doc_type=data.get("doc_type", "Test"),
            created_by=data.get("created_by", "test-user"),
            modified_by=data.get("modified_by", "test-user"),
            date_created=now,
            date_modified=now,
        )


def make_raw_documents(count: int) -> list[RawDocument]:
    """Create test RawDocument objects with required fields for mapping."""
    return [
        RawDocument(
            metadata={
                "object_id": f"doc-{i}",
                "name": f"Document {i}",
                "doc_type": "Test",
                "created_by": "test-user",
                "modified_by": "test-user",
            }
        )
        for i in range(count)
    ]


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = PipelineConfig()
        assert config.batch_size == 50
        assert config.dry_run is False
        assert config.offset == 0
        assert config.limit is None

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = PipelineConfig(
            batch_size=25,
            dry_run=True,
            offset=10,
            limit=100,
        )
        assert config.batch_size == 25
        assert config.dry_run is True
        assert config.offset == 10
        assert config.limit == 100

    def test_batch_size_validation_min(self) -> None:
        """Test batch_size minimum validation."""
        with pytest.raises(ValueError, match="batch_size must be between"):
            PipelineConfig(batch_size=0)

    def test_batch_size_validation_max(self) -> None:
        """Test batch_size maximum validation."""
        with pytest.raises(ValueError, match="batch_size must be between"):
            PipelineConfig(batch_size=101)

    def test_offset_validation(self) -> None:
        """Test offset non-negative validation."""
        with pytest.raises(ValueError, match="offset must be non-negative"):
            PipelineConfig(offset=-1)

    def test_limit_validation(self) -> None:
        """Test limit non-negative validation."""
        with pytest.raises(ValueError, match="limit must be non-negative"):
            PipelineConfig(limit=-1)


class TestPipelineResult:
    """Tests for PipelineResult."""

    def test_default_values(self) -> None:
        """Test default result values."""
        result = PipelineResult()
        assert result.total_read == 0
        assert result.total_mapped == 0
        assert result.total_uploaded == 0
        assert result.total_sent == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.duration_seconds == 0.0
        assert result.errors == []

    def test_success_property_no_failures(self) -> None:
        """Test success property with no failures."""
        result = PipelineResult(total_read=10, total_sent=10, failed=0)
        assert result.success is True

    def test_success_property_with_failures(self) -> None:
        """Test success property with failures."""
        result = PipelineResult(total_read=10, total_sent=8, failed=2)
        assert result.success is False


class TestPipelineError:
    """Tests for PipelineError."""

    def test_error_creation(self) -> None:
        """Test creating a pipeline error."""
        error = PipelineError(
            document_index=5,
            stage="map",
            message="Test error",
        )
        assert error.document_index == 5
        assert error.stage == "map"
        assert error.message == "Test error"
        assert error.details is None

    def test_error_with_details(self) -> None:
        """Test creating error with details."""
        error = PipelineError(
            document_index=10,
            stage="send",
            message="API error",
            details={"status_code": 500},
        )
        assert error.details == {"status_code": 500}


class TestIngestionPipelineInit:
    """Tests for IngestionPipeline initialization."""

    def test_init_minimal(self) -> None:
        """Test minimal initialization."""
        reader = MockReader([])
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
        )

        assert pipeline._reader is reader
        assert pipeline._source == "test.csv"
        assert pipeline._client is None
        assert pipeline._source_id == "test-source"
        assert isinstance(pipeline._mapper, IdentityMapper)
        assert pipeline.config.batch_size == 50

    def test_init_with_mapper(self) -> None:
        """Test initialization with custom mapper."""
        reader = MockReader([])
        mapper = IdentityMapper()
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
            mapper=mapper,
        )
        assert pipeline._mapper is mapper

    def test_init_with_config(self) -> None:
        """Test initialization with custom config."""
        reader = MockReader([])
        config = PipelineConfig(batch_size=10, dry_run=True)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
            config=config,
        )
        assert pipeline.config is config


class TestPipelineDryRun:
    """Tests for pipeline dry-run mode."""

    def test_dry_run_no_api_calls(self) -> None:
        """Test that dry-run doesn't make API calls."""
        documents = make_raw_documents(2)
        reader = MockReader(documents)

        # Mock client - should NOT be called
        mock_client = MagicMock()

        config = PipelineConfig(dry_run=True)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=mock_client,
            source_id="test-source",
            config=config,
        )

        result = pipeline.run()

        # Verify API was not called
        mock_client.send_events.assert_not_called()
        mock_client.get_presigned_urls.assert_not_called()

        # Verify results
        assert result.total_read == 2
        assert result.total_mapped == 2
        assert result.total_sent == 2  # "Would send" count

    def test_dry_run_reads_documents(self) -> None:
        """Test that dry-run still reads documents."""
        documents = make_raw_documents(5)
        reader = MockReader(documents)

        config = PipelineConfig(dry_run=True)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
            config=config,
        )

        result = pipeline.run()
        assert reader.read_called
        assert reader.last_source == "test.csv"
        assert result.total_read == 5


class TestPipelineBatching:
    """Tests for pipeline batching behavior."""

    def test_batch_size_respected(self) -> None:
        """Test documents are processed in correct batch sizes."""
        documents = make_raw_documents(25)
        reader = MockReader(documents)

        config = PipelineConfig(batch_size=10, dry_run=True)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
            config=config,
        )

        result = pipeline.run()
        assert result.total_read == 25

    def test_partial_batch(self) -> None:
        """Test handling of partial final batch."""
        documents = make_raw_documents(15)  # 10 + 5
        reader = MockReader(documents)

        config = PipelineConfig(batch_size=10, dry_run=True)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
            config=config,
        )

        result = pipeline.run()
        assert result.total_read == 15


class TestPipelineOffset:
    """Tests for pipeline offset handling."""

    def test_offset_skips_documents(self) -> None:
        """Test offset skips the correct number of documents."""
        documents = make_raw_documents(10)
        reader = MockReader(documents)

        config = PipelineConfig(offset=5, dry_run=True)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
            config=config,
        )

        result = pipeline.run()
        assert result.total_read == 5  # Only docs 5-9
        assert result.skipped == 5

    def test_offset_exceeds_document_count(self) -> None:
        """Test offset larger than document count."""
        documents = make_raw_documents(5)
        reader = MockReader(documents)

        config = PipelineConfig(offset=10, dry_run=True)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
            config=config,
        )

        result = pipeline.run()
        assert result.total_read == 0


class TestPipelineLimit:
    """Tests for pipeline limit handling."""

    def test_limit_stops_processing(self) -> None:
        """Test limit stops at correct count."""
        documents = make_raw_documents(20)
        reader = MockReader(documents)

        config = PipelineConfig(limit=10, dry_run=True)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
            config=config,
        )

        result = pipeline.run()
        assert result.total_read == 10

    def test_limit_with_offset(self) -> None:
        """Test limit combined with offset."""
        documents = make_raw_documents(20)
        reader = MockReader(documents)

        config = PipelineConfig(offset=5, limit=5, dry_run=True)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
            config=config,
        )

        result = pipeline.run()
        assert result.total_read == 5  # Docs 5-9
        assert result.skipped == 5


class TestPipelineErrorHandling:
    """Tests for pipeline error handling."""

    def test_mapping_errors_collected(self) -> None:
        """Test that mapping errors are collected."""
        documents = make_raw_documents(3)
        reader = MockReader(documents)
        mapper = ErrorMapper(error_on_index=2)  # Error on 2nd doc

        config = PipelineConfig(dry_run=True)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
            mapper=mapper,
            config=config,
        )

        result = pipeline.run()
        assert result.failed == 1
        assert len(result.errors) == 1
        assert result.errors[0].stage == "map"

    def test_pipeline_continues_after_error(self) -> None:
        """Test pipeline continues processing after error."""
        documents = make_raw_documents(5)
        reader = MockReader(documents)
        mapper = ErrorMapper(error_on_index=2)

        config = PipelineConfig(dry_run=True)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
            mapper=mapper,
            config=config,
        )

        result = pipeline.run()
        # 4 mapped successfully, 1 failed
        assert result.total_mapped == 4
        assert result.failed == 1


class TestPipelineWithClient:
    """Tests for pipeline with mocked ingestion client."""

    def test_send_events_called(self) -> None:
        """Test events are sent to client."""
        documents = make_raw_documents(1)
        reader = MockReader(documents)

        mock_client = MagicMock()
        mock_client.send_events.return_value = IngestionResponse(
            success=True, events_processed=1, errors=[]
        )

        config = PipelineConfig(dry_run=False)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=mock_client,
            source_id="test-source",
            config=config,
        )

        result = pipeline.run()

        mock_client.send_events.assert_called_once()
        assert result.total_sent == 1

    def test_send_error_collected(self) -> None:
        """Test send errors are collected."""
        documents = make_raw_documents(1)
        reader = MockReader(documents)

        mock_client = MagicMock()
        mock_client.send_events.side_effect = Exception("API error")

        config = PipelineConfig(dry_run=False)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=mock_client,
            source_id="test-source",
            config=config,
        )

        result = pipeline.run()

        assert result.failed > 0
        assert any(e.stage == "send" for e in result.errors)


class TestPipelineTiming:
    """Tests for pipeline timing."""

    def test_duration_recorded(self) -> None:
        """Test duration is recorded."""
        documents = make_raw_documents(1)
        reader = MockReader(documents)

        config = PipelineConfig(dry_run=True)
        pipeline = IngestionPipeline(
            reader=reader,
            source="test.csv",
            ingestion_client=None,
            source_id="test-source",
            config=config,
        )

        result = pipeline.run()
        assert result.duration_seconds >= 0


class TestCreatePipeline:
    """Tests for create_pipeline factory function."""

    def test_create_from_settings(self) -> None:
        """Test creating pipeline from settings."""
        mock_settings = MagicMock()
        mock_settings.batch_size = 25

        reader = MockReader([])

        pipeline = create_pipeline(
            settings=mock_settings,
            reader=reader,
            source="test.csv",
        )

        assert pipeline.config.batch_size == 25

    def test_create_with_overrides(self) -> None:
        """Test creating pipeline with overrides."""
        mock_settings = MagicMock()
        mock_settings.batch_size = 50

        reader = MockReader([])

        pipeline = create_pipeline(
            settings=mock_settings,
            reader=reader,
            source="test.csv",
            batch_size=10,
            dry_run=True,
            offset=5,
            limit=20,
        )

        assert pipeline.config.batch_size == 10
        assert pipeline.config.dry_run is True
        assert pipeline.config.offset == 5
        assert pipeline.config.limit == 20


class TestBatchResult:
    """Tests for BatchResult."""

    def test_default_values(self) -> None:
        """Test default batch result values."""
        result = BatchResult()
        assert result.processed == 0
        assert result.uploaded == 0
        assert result.sent == 0
        assert result.failed == 0
        assert result.errors == []
