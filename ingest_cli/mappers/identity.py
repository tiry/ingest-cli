"""Identity mapper - pass-through transformation.

Maps RawDocument fields directly to Document fields with minimal transformation.
"""

from ingest_cli.models import Document
from ingest_cli.readers.base import RawDocument

from .base import BaseMapper


class IdentityMapper(BaseMapper):
    """Pass-through mapper for pre-formatted documents.

    Expects RawDocument data to contain fields matching Document:
    - object_id: str (required)
    - name: str (required)
    - doc_type: str (required)
    - date_created: datetime or ISO string (optional, defaults to now)
    - created_by: str (required)
    - date_modified: datetime or ISO string (optional, defaults to now)
    - modified_by: str or list[str] (required)
    - file_path: Path or str (optional)
    - file_content_type: str (optional, required if file_path)
    - properties: dict (optional, additional properties)

    Example:
        >>> mapper = IdentityMapper()
        >>> raw = RawDocument(data={
        ...     "object_id": "doc-123",
        ...     "name": "Test Document",
        ...     "doc_type": "Report",
        ...     "created_by": "user-1",
        ...     "modified_by": "user-2",
        ... })
        >>> doc = mapper.map(raw)
        >>> doc.object_id
        'doc-123'
    """

    @property
    def name(self) -> str:
        """Return mapper name."""
        return "identity"

    def map(self, raw: RawDocument) -> Document:
        """Transform raw document to API document.

        Args:
            raw: RawDocument from a reader

        Returns:
            Document ready for API submission

        Raises:
            MissingFieldError: If required fields are missing
        """
        data = raw.data

        # Validate required fields
        self.validate_required_fields(data)

        # Parse datetime values
        date_created = self.parse_datetime(data.get("date_created"))
        date_modified = self.parse_datetime(data.get("date_modified"))

        # Parse file path if present
        file_path = self.parse_path(data.get("file_path"))

        # Build Document
        return Document(
            object_id=str(data["object_id"]),
            name=str(data["name"]),
            doc_type=str(data["doc_type"]),
            date_created=date_created,
            created_by=str(data["created_by"]),
            date_modified=date_modified,
            modified_by=data["modified_by"],
            file_path=file_path,
            file_content_type=data.get("file_content_type"),
            properties=data.get("properties", {}),
        )
