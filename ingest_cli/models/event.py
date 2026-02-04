"""Content event models for HxAI Ingestion API v2.

These models represent the createOrUpdate and delete events
sent to the /v2/ingestion-events endpoint.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .annotations import (
    CreatedByAnnotation,
    DateCreatedAnnotation,
    DateModifiedAnnotation,
    ModifiedByAnnotation,
    NameAnnotation,
    TypeAnnotation,
)
from .file import FileProperty
from .properties import (
    BooleanValue,
    CurrencyValue,
    DatetimeValue,
    DateValue,
    FloatValue,
    IntegerValue,
    ObjectValue,
    StringValue,
)

# Union of all property value types
PropertyValue = (
    # Annotations
    NameAnnotation
    | TypeAnnotation
    | DateCreatedAnnotation
    | CreatedByAnnotation
    | DateModifiedAnnotation
    | ModifiedByAnnotation
    # Typed values
    | StringValue
    | IntegerValue
    | FloatValue
    | BooleanValue
    | DateValue
    | DatetimeValue
    | CurrencyValue
    | ObjectValue
    # File property
    | FileProperty
)


class ContentEventBase(BaseModel):
    """Base class for all content events.

    Contains the common fields required by all event types.

    Attributes:
        object_id: Unique ID of the content in source (1-128 chars, alphanumeric)
        source_id: UUID of the content source
        source_timestamp: Unix epoch timestamp in milliseconds
    """

    model_config = ConfigDict(populate_by_name=True)

    object_id: str = Field(
        alias="objectId",
        min_length=1,
        max_length=128,
        description="Unique content ID in source (pattern: ^[A-Za-z0-9._-]+$)",
    )
    source_id: str = Field(
        alias="sourceId",
        description="UUID of the content source",
    )
    source_timestamp: int = Field(
        alias="sourceTimestamp",
        description="Unix epoch timestamp in milliseconds",
    )

    @field_validator("object_id")
    @classmethod
    def validate_object_id(cls, v: str) -> str:
        """Validate objectId matches allowed pattern."""
        import re

        if not re.match(r"^[A-Za-z0-9._-]+$", v):
            msg = "objectId must match pattern ^[A-Za-z0-9._-]+$"
            raise ValueError(msg)
        return v


class CreateOrUpdateEvent(ContentEventBase):
    """Create or update content event for v2 API.

    Represents a document creation or update with all properties.
    Required annotations: name, type, dateCreated, createdBy, dateModified, modifiedBy

    Example:
        event = CreateOrUpdateEvent(
            object_id="doc-123",
            source_id="a52878a6-b459-4a13-bdd9-7d086f591d58",
            source_timestamp=1732022495428,
            properties={
                "name": NameAnnotation(value="My Document"),
                "type": TypeAnnotation(value="Invoice"),
                ...
            }
        )
    """

    event_type: Literal["createOrUpdate"] = Field(
        default="createOrUpdate",
        alias="eventType",
    )
    properties: dict[str, PropertyValue | dict[str, Any]] = Field(
        description="Document properties including required annotations"
    )

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Serialize model, converting nested objects properly."""
        kwargs.setdefault("by_alias", True)
        kwargs.setdefault("exclude_none", True)
        data = super().model_dump(**kwargs)

        # Convert properties to serialized form
        if "properties" in data:
            serialized_props: dict[str, Any] = {}
            for key, value in data["properties"].items():
                if isinstance(value, dict):
                    serialized_props[key] = value
                else:
                    serialized_props[key] = value
            data["properties"] = serialized_props

        return data


class DeleteEvent(ContentEventBase):
    """Delete content event.

    Signals that a document should be removed from the data lake.

    Example:
        event = DeleteEvent(
            object_id="doc-123",
            source_id="a52878a6-b459-4a13-bdd9-7d086f591d58",
            source_timestamp=1732022495428,
        )
    """

    event_type: Literal["delete"] = Field(
        default="delete",
        alias="eventType",
    )


# Type alias for all event types
ContentEvent = CreateOrUpdateEvent | DeleteEvent
