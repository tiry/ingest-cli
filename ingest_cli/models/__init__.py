"""Data models for HxAI Ingestion API.

This package provides Pydantic models for:
- Property values (string, integer, float, boolean, date, datetime, currency, object)
- Required annotations (name, type, dateCreated, createdBy, dateModified, modifiedBy)
- File metadata and upload references
- Content events (createOrUpdate, delete)
- High-level Document model for the pipeline
"""

# Property value models
# Annotation models
from .annotations import (
    CreatedByAnnotation,
    DateCreatedAnnotation,
    DateModifiedAnnotation,
    ModifiedByAnnotation,
    NameAnnotation,
    RequiredAnnotation,
    TypeAnnotation,
)

# Document model
from .document import Document, format_datetime

# Event models
from .event import (
    ContentEvent,
    ContentEventBase,
    CreateOrUpdateEvent,
    DeleteEvent,
    PropertyValue,
)

# File models
from .file import (
    ContentMetadata,
    FileMetadataOnly,
    FileMetadataWithUpload,
    FileProperty,
    FileUpload,
)
from .properties import (
    BooleanValue,
    CurrencyValue,
    DatetimeValue,
    DateValue,
    FloatValue,
    IntegerValue,
    ObjectValue,
    StringValue,
    TypedPropertyValue,
)

__all__ = [
    # Property values
    "StringValue",
    "IntegerValue",
    "FloatValue",
    "BooleanValue",
    "DateValue",
    "DatetimeValue",
    "CurrencyValue",
    "ObjectValue",
    "TypedPropertyValue",
    # Annotations
    "NameAnnotation",
    "TypeAnnotation",
    "DateCreatedAnnotation",
    "CreatedByAnnotation",
    "DateModifiedAnnotation",
    "ModifiedByAnnotation",
    "RequiredAnnotation",
    # File models
    "ContentMetadata",
    "FileUpload",
    "FileMetadataOnly",
    "FileMetadataWithUpload",
    "FileProperty",
    # Event models
    "ContentEventBase",
    "CreateOrUpdateEvent",
    "DeleteEvent",
    "ContentEvent",
    "PropertyValue",
    # Document
    "Document",
    "format_datetime",
]
