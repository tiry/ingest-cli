"""Field mapper - configurable field transformation.

Maps source fields to target Document fields based on configuration.
"""

from typing import Any

from ingest_cli.models import Document
from ingest_cli.readers.base import RawDocument

from .base import BaseMapper, MapperError


class FieldMapper(BaseMapper):
    """Configurable field mapper with mapping rules.

    Allows mapping source field names to Document field names,
    with optional default values for missing fields.

    Args:
        mapping: Dict mapping Document field names to source field names.
                 Keys are Document fields, values are source field names.
        defaults: Dict of default values for fields not in source data.

    Example:
        >>> mapper = FieldMapper(
        ...     mapping={
        ...         "object_id": "id",
        ...         "name": "title",
        ...         "doc_type": "category",
        ...         "created_by": "author",
        ...         "modified_by": "editor",
        ...     },
        ...     defaults={
        ...         "doc_type": "Document",
        ...     }
        ... )
        >>> raw = RawDocument(data={"id": "123", "title": "My Doc", "author": "me"})
        >>> doc = mapper.map(raw)
    """

    def __init__(
        self,
        mapping: dict[str, str] | None = None,
        defaults: dict[str, Any] | None = None,
    ) -> None:
        """Initialize field mapper.

        Args:
            mapping: Field name mapping (target -> source)
            defaults: Default values for missing fields
        """
        self._mapping = mapping or {}
        self._defaults = defaults or {}

    @property
    def name(self) -> str:
        """Return mapper name."""
        return "field"

    def _get_field(
        self,
        data: dict[str, Any],
        target_field: str,
        required: bool = False,
    ) -> Any:
        """Get field value from data using mapping.

        Args:
            data: Source data dictionary
            target_field: Target Document field name
            required: Whether field is required

        Returns:
            Field value from source, default, or None

        Raises:
            MapperError: If required field is missing
        """
        # Get source field name from mapping, or use target field name
        source_field = self._mapping.get(target_field, target_field)

        # Try to get value from data
        if source_field in data:
            return data[source_field]

        # Try default value
        if target_field in self._defaults:
            return self._defaults[target_field]

        # Check if required
        if required:
            msg = f"Required field '{target_field}' not found (mapped from '{source_field}')"
            raise MapperError(msg)

        return None

    def map(self, raw: RawDocument) -> Document:
        """Transform raw document to API document.

        Args:
            raw: RawDocument from a reader

        Returns:
            Document ready for API submission

        Raises:
            MapperError: If required fields are missing
        """
        data = raw.data

        # Get required fields
        object_id = self._get_field(data, "object_id", required=True)
        name = self._get_field(data, "name", required=True)
        doc_type = self._get_field(data, "doc_type", required=True)
        created_by = self._get_field(data, "created_by", required=True)
        modified_by = self._get_field(data, "modified_by", required=True)

        # Get optional fields
        date_created = self._get_field(data, "date_created")
        date_modified = self._get_field(data, "date_modified")
        file_path = self._get_field(data, "file_path")
        file_content_type = self._get_field(data, "file_content_type")
        properties = self._get_field(data, "properties") or {}

        # Parse datetime values
        date_created = self.parse_datetime(date_created)
        date_modified = self.parse_datetime(date_modified)

        # Parse file path
        file_path = self.parse_path(file_path)

        return Document(
            object_id=str(object_id),
            name=str(name),
            doc_type=str(doc_type),
            date_created=date_created,
            created_by=str(created_by),
            date_modified=date_modified,
            modified_by=modified_by,
            file_path=file_path,
            file_content_type=file_content_type,
            properties=properties,
        )
