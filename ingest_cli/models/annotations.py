"""Annotation models for HxAI Ingestion API v2.

Annotations are special property types required for createOrUpdate events.
Required: name, type, dateCreated, createdBy, dateModified, modifiedBy

These models ensure proper serialization with the 'annotation' field.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class NameAnnotation(BaseModel):
    """Document name annotation (required).

    The display name for the document in the HxAI system.

    Example:
        {"annotation": "name", "value": "Invoice-2024-001.pdf"}
    """

    model_config = ConfigDict(populate_by_name=True)

    annotation: Literal["name"] = "name"
    value: str


class TypeAnnotation(BaseModel):
    """Document type annotation (required).

    The content type classification within the source system.

    Example:
        {"annotation": "type", "type": "string", "value": "Invoice"}
    """

    model_config = ConfigDict(populate_by_name=True)

    annotation: Literal["type"] = "type"
    type: Literal["string"] = "string"
    value: str


class DateCreatedAnnotation(BaseModel):
    """Date created annotation (required).

    When the document was originally created (ISO 8601 with Z).

    Example:
        {"annotation": "dateCreated", "type": "datetime",
         "value": "2024-01-15T10:30:00.000Z"}
    """

    model_config = ConfigDict(populate_by_name=True)

    annotation: Literal["dateCreated"] = "dateCreated"
    type: Literal["datetime"] = "datetime"
    value: str  # ISO 8601 datetime format


class CreatedByAnnotation(BaseModel):
    """Created by user annotation (required).

    The user ID who created the document in the source system.

    Example:
        {"annotation": "createdBy", "type": "string", "value": "user-123"}
    """

    model_config = ConfigDict(populate_by_name=True)

    annotation: Literal["createdBy"] = "createdBy"
    type: Literal["string"] = "string"
    value: str


class DateModifiedAnnotation(BaseModel):
    """Date modified annotation (required).

    When the document was last modified (ISO 8601 with Z).

    Example:
        {"annotation": "dateModified", "type": "datetime",
         "value": "2024-01-16T14:20:00.000Z"}
    """

    model_config = ConfigDict(populate_by_name=True)

    annotation: Literal["dateModified"] = "dateModified"
    type: Literal["datetime"] = "datetime"
    value: str  # ISO 8601 datetime format


class ModifiedByAnnotation(BaseModel):
    """Modified by user annotation (required).

    The user ID who last modified the document. May be array for multi-user edits.

    Example:
        {"annotation": "modifiedBy", "type": "string", "value": "user-456"}
        {"annotation": "modifiedBy", "type": "string", "value": ["admin", "user"]}
    """

    model_config = ConfigDict(populate_by_name=True)

    annotation: Literal["modifiedBy"] = "modifiedBy"
    type: Literal["string"] = "string"
    value: str | list[str]


# Type alias for all required annotations
RequiredAnnotation = (
    NameAnnotation
    | TypeAnnotation
    | DateCreatedAnnotation
    | CreatedByAnnotation
    | DateModifiedAnnotation
    | ModifiedByAnnotation
)
