"""Ingestion pipeline orchestrator.

This module provides the IngestionPipeline class that orchestrates
the end-to-end document ingestion process: read, map, upload, send.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Iterator

from ingest_cli.mappers import BaseMapper, IdentityMapper
from ingest_cli.models import CreateOrUpdateEvent, Document
from ingest_cli.readers import BaseReader
from ingest_cli.readers.base import RawDocument

if TYPE_CHECKING:
    from ingest_cli.api import IngestionClient
    from ingest_cli.config import IngestSettings

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the ingestion pipeline.

    Attributes:
        batch_size: Number of documents per batch (1-100).
        dry_run: If True, validate without making API calls.
        offset: Number of documents to skip from start.
        limit: Maximum documents to process (None = all).
    """

    batch_size: int = 50
    dry_run: bool = False
    offset: int = 0
    limit: int | None = None

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not 1 <= self.batch_size <= 100:
            raise ValueError("batch_size must be between 1 and 100")
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        if self.limit is not None and self.limit < 0:
            raise ValueError("limit must be non-negative")


@dataclass
class PipelineError:
    """Tracks an error that occurred during pipeline execution.

    Attributes:
        document_index: Index of document that caused the error.
        stage: Pipeline stage where error occurred.
        message: Error message.
        details: Additional error details.
    """

    document_index: int
    stage: str  # "read", "map", "upload", "send"
    message: str
    details: dict[str, Any] | None = None


@dataclass
class BatchResult:
    """Result of processing a single batch.

    Attributes:
        processed: Number of documents successfully processed.
        uploaded: Number of files uploaded.
        sent: Number of events sent.
        failed: Number of failures.
        errors: List of errors from this batch.
    """

    processed: int = 0
    uploaded: int = 0
    sent: int = 0
    failed: int = 0
    errors: list[PipelineError] = field(default_factory=list)


@dataclass
class PipelineResult:
    """Result of the complete pipeline execution.

    Attributes:
        total_read: Total documents read from source.
        total_mapped: Total documents mapped.
        total_uploaded: Total files uploaded.
        total_sent: Total events sent to API.
        failed: Total failures.
        skipped: Documents skipped (due to offset).
        duration_seconds: Pipeline execution time.
        errors: All errors from pipeline.
    """

    total_read: int = 0
    total_mapped: int = 0
    total_uploaded: int = 0
    total_sent: int = 0
    failed: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    errors: list[PipelineError] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if pipeline completed without errors."""
        return self.failed == 0


class IngestionPipeline:
    """Orchestrates the document ingestion pipeline.

    The pipeline processes documents through these stages:
    1. Read: Get RawDocuments from reader
    2. Map: Transform RawDocument to Document using mapper
    3. Build: Convert Document to CreateOrUpdateEvent
    4. Upload: Upload files to S3 via presigned URLs
    5. Send: Send events to ingestion API

    Example:
        >>> pipeline = IngestionPipeline(
        ...     reader=CSVReader("documents.csv"),
        ...     mapper=IdentityMapper(),
        ...     ingestion_client=client,
        ...     config=PipelineConfig(batch_size=50),
        ... )
        >>> result = pipeline.run()
        >>> print(f"Processed {result.total_sent} documents")
    """

    def __init__(
        self,
        reader: BaseReader,
        source: str,
        ingestion_client: IngestionClient | None,
        mapper: BaseMapper | None = None,
        config: PipelineConfig | None = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            reader: Reader to get documents from.
            source: Source path for the reader.
            ingestion_client: Client for API calls (None for dry-run).
            mapper: Mapper to transform documents (default: IdentityMapper).
            config: Pipeline configuration.
        """
        self._reader = reader
        self._source = source
        self._client = ingestion_client
        self._mapper = mapper or IdentityMapper()
        self._config = config or PipelineConfig()

    @property
    def config(self) -> PipelineConfig:
        """Get pipeline configuration."""
        return self._config

    def run(self) -> PipelineResult:
        """Execute the full pipeline.

        Returns:
            PipelineResult with totals and errors.
        """
        start_time = time.time()
        result = PipelineResult()

        logger.info(
            f"Starting pipeline: batch_size={self._config.batch_size}, "
            f"dry_run={self._config.dry_run}, offset={self._config.offset}"
        )

        # Read and process in batches
        batch_num = 0
        documents_processed = 0

        for batch in self._read_batches():
            batch_num += 1

            # Log progress
            logger.info(f"Processing batch {batch_num} ({len(batch)} documents)")

            # Process the batch
            batch_result = self._process_batch(batch, documents_processed)

            # Update totals
            result.total_read += len(batch)
            result.total_mapped += batch_result.processed
            result.total_uploaded += batch_result.uploaded
            result.total_sent += batch_result.sent
            result.failed += batch_result.failed
            result.errors.extend(batch_result.errors)
            documents_processed += len(batch)

            # Check limit
            if self._config.limit and documents_processed >= self._config.limit:
                logger.info(f"Reached limit of {self._config.limit} documents")
                break

        result.skipped = self._config.offset
        result.duration_seconds = time.time() - start_time

        logger.info(
            f"Pipeline complete: read={result.total_read}, "
            f"sent={result.total_sent}, failed={result.failed}, "
            f"duration={result.duration_seconds:.2f}s"
        )

        return result

    def _read_batches(self) -> Iterator[list[RawDocument]]:
        """Read documents from reader in batches.

        Yields:
            Batches of RawDocument objects.
        """
        batch: list[RawDocument] = []
        documents_seen = 0
        documents_yielded = 0
        limit = self._config.limit

        for raw_doc in self._reader.read(self._source):
            documents_seen += 1

            # Skip if before offset
            if documents_seen <= self._config.offset:
                continue

            # Check if we've hit the limit before adding more
            if limit and documents_yielded >= limit:
                break

            batch.append(raw_doc)
            documents_yielded += 1

            # Yield when batch is full
            if len(batch) >= self._config.batch_size:
                yield batch
                batch = []

        # Yield remaining documents
        if batch:
            yield batch

    def _process_batch(
        self,
        raw_documents: list[RawDocument],
        start_index: int,
    ) -> BatchResult:
        """Process a batch of raw documents.

        Args:
            raw_documents: List of RawDocument objects.
            start_index: Starting index for error tracking.

        Returns:
            BatchResult with processing results.
        """
        result = BatchResult()
        events: list[CreateOrUpdateEvent] = []
        documents: list[Document] = []

        # Map each raw document to Document
        for i, raw_doc in enumerate(raw_documents):
            doc_index = start_index + i
            try:
                # Map RawDocument -> Document
                document = self._mapper.map(raw_doc)
                documents.append(document)
                result.processed += 1

            except Exception as e:
                logger.error(f"Error mapping document {doc_index}: {e}")
                result.failed += 1
                result.errors.append(
                    PipelineError(
                        document_index=doc_index,
                        stage="map",
                        message=str(e),
                    )
                )

        # Build events from Documents
        for i, document in enumerate(documents):
            doc_index = start_index + i
            try:
                event = self._build_event(document)
                events.append(event)
            except Exception as e:
                logger.error(f"Error building event {doc_index}: {e}")
                result.failed += 1
                result.errors.append(
                    PipelineError(
                        document_index=doc_index,
                        stage="build",
                        message=str(e),
                    )
                )

        # Skip API calls in dry-run mode
        if self._config.dry_run:
            logger.info(f"[DRY-RUN] Would send {len(events)} events")
            result.sent = len(events)
            return result

        # Upload files and send events
        if events and self._client:
            try:
                # Upload any files
                uploaded = self._upload_files(events, documents)
                result.uploaded = uploaded

                # Send events
                response = self._client.send_events(events)
                result.sent = response.events_processed

            except Exception as e:
                logger.error(f"Error sending batch: {e}")
                result.failed += len(events)
                result.errors.append(
                    PipelineError(
                        document_index=start_index,
                        stage="send",
                        message=str(e),
                    )
                )

        return result

    def _build_event(self, document: Document) -> CreateOrUpdateEvent:
        """Build a CreateOrUpdateEvent from a Document.

        Args:
            document: Mapped Document object.

        Returns:
            CreateOrUpdateEvent ready for API submission.
        """
        # Convert datetime to milliseconds since epoch
        ts = document.date_modified or datetime.now()
        timestamp_ms = int(ts.timestamp() * 1000)

        # Build the event with required fields from Document
        return CreateOrUpdateEvent(
            objectId=document.object_id,
            sourceId="ingest-cli",  # Default source
            sourceTimestamp=timestamp_ms,
            properties=document.properties or {},
        )

    def _upload_files(self, events: list[CreateOrUpdateEvent], documents: list[Document]) -> int:
        """Upload files for documents that have file references.

        Args:
            events: List of events.
            documents: List of corresponding documents.

        Returns:
            Number of files uploaded.
        """
        if not self._client:
            return 0

        # Find documents with files to upload
        docs_with_files = [
            (event, doc)
            for event, doc in zip(events, documents, strict=False)
            if doc.file_path and doc.file_path.exists()
        ]

        if not docs_with_files:
            return 0

        # Get presigned URLs
        logger.info(f"Requesting {len(docs_with_files)} presigned URLs")
        presigned_urls = self._client.get_presigned_urls(len(docs_with_files))

        # Upload each file
        uploaded = 0
        for (event, document), presigned_url in zip(docs_with_files, presigned_urls, strict=False):
            try:
                if document.file_path:
                    result = self._client.upload_file(presigned_url, document.file_path)
                    # Store uploaded key on event
                    logger.debug(f"Uploaded {document.file_path} -> {result.object_key}")
                    uploaded += 1
            except Exception as e:
                logger.error(f"Error uploading {document.file_path}: {e}")

        return uploaded


def create_pipeline(
    settings: IngestSettings,
    reader: BaseReader,
    source: str,
    ingestion_client: IngestionClient | None = None,
    mapper: BaseMapper | None = None,
    dry_run: bool = False,
    batch_size: int | None = None,
    offset: int = 0,
    limit: int | None = None,
) -> IngestionPipeline:
    """Create an IngestionPipeline from settings.

    Args:
        settings: Ingest configuration settings.
        reader: Reader to get documents from.
        source: Source path for the reader.
        ingestion_client: Client for API calls (None for dry-run).
        mapper: Mapper for transformations (default: IdentityMapper).
        dry_run: If True, don't make API calls.
        batch_size: Override settings batch_size.
        offset: Number of documents to skip.
        limit: Maximum documents to process.

    Returns:
        Configured IngestionPipeline instance.
    """
    config = PipelineConfig(
        batch_size=batch_size or settings.batch_size,
        dry_run=dry_run,
        offset=offset,
        limit=limit,
    )

    return IngestionPipeline(
        reader=reader,
        source=source,
        ingestion_client=ingestion_client,
        mapper=mapper,
        config=config,
    )
