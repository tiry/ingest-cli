"""Mapper module for document transformation.

Mappers transform RawDocument (from readers) into Document (for API).

Available Mappers:
- identity: Pass-through mapper for pre-formatted documents
- field: Configurable field name mapping

Usage:
    >>> from ingest_cli.mappers import create_mapper, IdentityMapper
    >>> mapper = create_mapper("identity")
    >>> doc = mapper.map(raw_document)
"""

from .base import BaseMapper, MapperError, MissingFieldError
from .factory import (
    MapperLoadError,
    create_mapper,
    get_available_mappers,
)
from .field_mapper import FieldMapper
from .identity import IdentityMapper
from .registry import (
    MapperNotFoundError,
    get_mapper,
    get_mapper_info,
    list_mappers,
    register_mapper,
)

__all__ = [
    # Base
    "BaseMapper",
    "MapperError",
    "MissingFieldError",
    # Mappers
    "IdentityMapper",
    "FieldMapper",
    # Registry
    "get_mapper",
    "list_mappers",
    "get_mapper_info",
    "register_mapper",
    "MapperNotFoundError",
    # Factory
    "create_mapper",
    "get_available_mappers",
    "MapperLoadError",
]
