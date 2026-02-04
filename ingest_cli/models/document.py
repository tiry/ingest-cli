"""High-level Document model for the ingestion pipeline.

This model provides a user-friendly interface for building documents
that can be converted to API event format.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .annotations import (
    CreatedByAnnotation,
    DateCreatedAnnotation,
    DateModifiedAnnotation,
    ModifiedByAnnotation,
    NameAnnotation,
    TypeAnnotation,
)
from .event import CreateOrUpdateEvent, DeleteEvent, PropertyValue
from .file import FileProperty
from .properties import StringValue


def format_datetime(dt: datetime) -> str:
    """Format datetime to ISO 8601 with Z suffix.

    Args:
        dt: Datetime object to format

    Returns:
        String in format: YYYY-MM-DDTHH:MM:SS.sssZ
    """
    # Convert to UTC if timezone aware, otherwise assume UTC
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)  # Strip timezone for formatting
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


@dataclass
class Document:
    """High-level document model for the ingestion pipeline.

    Provides a cleaner interface for creating documents with required
    annotations and optional file attachments.

    Attributes:
        object_id: Unique identifier for this document in the source
        name: Display name for the document
        doc_type: Content type classification
        date_created: When the document was created
        created_by: User ID who created the document
        date_modified: When the document was last modified
        modified_by: User ID who last modified the document
        file_path: Optional path to file attachment
        file_content_type: MIME type of the file (required if file_path set)
        file_size: Size of the file in bytes (optional, computed if not provided)
        properties: Additional custom properties

    Example:
        doc = Document(
            object_id="invoice-2024-001",
            name="Invoice 2024-001.pdf",
            doc_type="Invoice",
            date_created=datetime.now(),
            created_by="system",
            date_modified=datetime.now(),
            modified_by="admin",
            file_path=Path("/data/invoices/inv-001.pdf"),
            file_content_type="application/pdf",
        )
        event = doc.to_event(source_id="uuid-...", upload_id="uuid-...")
    """

    # Required identifiers
    object_id: str

    # Required annotations
    name: str
    doc_type: str
    date_created: datetime
    created_by: str
    date_modified: datetime
    modified_by: str | list[str]

    # Optional file attachment
    file_path: Path | None = None
    file_content_type: str | None = None
    file_size: int | None = None

    # Additional custom properties
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate document after initialization."""
        if self.file_path is not None and self.file_content_type is None:
            msg = "file_content_type is required when file_path is provided"
            raise ValueError(msg)

    def get_file_size(self) -> int:
        """Get file size, computing from path if necessary.

        Returns:
            File size in bytes

        Raises:
            ValueError: If no file is attached
            FileNotFoundError: If file doesn't exist
        """
        if self.file_path is None:
            msg = "No file attached to this document"
            raise ValueError(msg)

        if self.file_size is not None:
            return self.file_size

        return self.file_path.stat().st_size

    def has_file(self) -> bool:
        """Check if document has a file attachment.

        Returns:
            True if file_path is set, False otherwise
        """
        return self.file_path is not None

    def to_event(
        self,
        source_id: str,
        upload_id: str | None = None,
        source_timestamp: int | None = None,
    ) -> CreateOrUpdateEvent:
        """Convert document to API event format.

        Args:
            source_id: UUID of the content source
            upload_id: Upload ID from presigned URL (required if has file)
            source_timestamp: Unix epoch milliseconds (defaults to now)

        Returns:
            CreateOrUpdateEvent ready for API submission

        Raises:
            ValueError: If document has file but no upload_id provided
        """
        if self.has_file() and upload_id is None:
            msg = "upload_id is required when document has a file attachment"
            raise ValueError(msg)

        # Default timestamp to now
        if source_timestamp is None:
            source_timestamp = int(datetime.now().timestamp() * 1000)

        # Build properties dict with required annotations
        props: dict[str, PropertyValue] = {
            "name": NameAnnotation(value=self.name),
            "type": TypeAnnotation(value=self.doc_type),
            "dateCreated": DateCreatedAnnotation(value=format_datetime(self.date_created)),
            "createdBy": CreatedByAnnotation(value=self.created_by),
            "dateModified": DateModifiedAnnotation(value=format_datetime(self.date_modified)),
            "modifiedBy": ModifiedByAnnotation(value=self.modified_by),
        }

        # Add file property if we have a file
        if self.has_file() and upload_id is not None:
            assert self.file_path is not None
            assert self.file_content_type is not None
            props["file"] = FileProperty.with_upload(
                upload_id=upload_id,
                content_type=self.file_content_type,
                size=self.get_file_size(),
                name=self.file_path.name,
            )

        # Add custom properties (convert to StringValue if simple strings)
        for key, value in self.properties.items():
            if isinstance(value, str):
                props[key] = StringValue(value=value)
            elif hasattr(value, "model_dump"):
                # Already a Pydantic model (PropertyValue)
                props[key] = value
            elif isinstance(value, dict) and "type" in value:
                # Raw dict with type field - pass through
                props[key] = value  # type: ignore
            else:
                # Convert to string
                props[key] = StringValue(value=str(value))

        return CreateOrUpdateEvent(
            object_id=self.object_id,
            source_id=source_id,
            source_timestamp=source_timestamp,
            properties=props,
        )

    def to_delete_event(
        self,
        source_id: str,
        source_timestamp: int | None = None,
    ) -> DeleteEvent:
        """Create a delete event for this document.

        Args:
            source_id: UUID of the content source
            source_timestamp: Unix epoch milliseconds (defaults to now)

        Returns:
            DeleteEvent for API submission
        """
        if source_timestamp is None:
            source_timestamp = int(datetime.now().timestamp() * 1000)

        return DeleteEvent(
            object_id=self.object_id,
            source_id=source_id,
            source_timestamp=source_timestamp,
        )
