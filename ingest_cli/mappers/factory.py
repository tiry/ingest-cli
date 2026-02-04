"""Mapper factory for creating mapper instances.

Provides convenient functions for creating mappers by name or from config.
"""

import importlib.util
from pathlib import Path
from typing import Any

from .base import BaseMapper, MapperError
from .registry import get_mapper, list_mappers


class MapperLoadError(MapperError):
    """Raised when a custom mapper cannot be loaded."""

    pass


def create_mapper(
    name: str | None = None,
    module_path: str | None = None,
    config: dict[str, Any] | None = None,
) -> BaseMapper:
    """Create a mapper instance.

    Creates a mapper by name from the registry, or loads a custom mapper
    from a Python module path.

    Args:
        name: Registered mapper name (e.g., "identity", "field")
              Defaults to "identity" if neither name nor module_path provided.
        module_path: Path to custom mapper module (e.g., "./mappers/custom.py")
        config: Configuration for the mapper (e.g., field mappings)

    Returns:
        Mapper instance

    Raises:
        MapperNotFoundError: If name not found in registry
        MapperLoadError: If custom module cannot be loaded

    Examples:
        >>> # Create identity mapper
        >>> mapper = create_mapper("identity")

        >>> # Create field mapper with config
        >>> mapper = create_mapper("field", config={
        ...     "mapping": {"object_id": "id", "name": "title"},
        ...     "defaults": {"doc_type": "Document"}
        ... })

        >>> # Load custom mapper from file
        >>> mapper = create_mapper(module_path="./my_mapper.py")
    """
    config = config or {}

    # Load from module path if provided
    if module_path:
        return _load_from_module(module_path, config)

    # Default to identity mapper
    if name is None:
        name = "identity"

    # Get mapper class from registry
    mapper_class = get_mapper(name)

    # Create instance with config
    return _create_instance(mapper_class, config)


def _create_instance(
    mapper_class: type[BaseMapper],
    config: dict[str, Any],
) -> BaseMapper:
    """Create mapper instance with configuration.

    Args:
        mapper_class: Mapper class
        config: Configuration dict

    Returns:
        Mapper instance
    """
    # Check if mapper accepts config arguments
    try:
        # Try creating with config as kwargs
        return mapper_class(**config)
    except TypeError:
        # Mapper doesn't accept these args, create without
        return mapper_class()


def _load_from_module(module_path: str, config: dict[str, Any]) -> BaseMapper:
    """Load a custom mapper from a Python module.

    The module must contain a class that inherits from BaseMapper.
    If multiple classes exist, looks for one named 'Mapper' or 'CustomMapper'.

    Args:
        module_path: Path to Python module file
        config: Configuration for the mapper

    Returns:
        Mapper instance

    Raises:
        MapperLoadError: If module cannot be loaded or no mapper found
    """
    path = Path(module_path)

    # Check extension first (before existence check)
    if not path.suffix == ".py":
        raise MapperLoadError(f"Module must be a .py file: {module_path}")

    if not path.exists():
        raise MapperLoadError(f"Module not found: {module_path}")

    try:
        # Load module dynamically
        spec = importlib.util.spec_from_file_location("custom_mapper", path)
        if spec is None or spec.loader is None:
            raise MapperLoadError(f"Cannot load module spec: {module_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find mapper class in module
        mapper_class = _find_mapper_class(module)
        if mapper_class is None:
            raise MapperLoadError(
                f"No BaseMapper subclass found in {module_path}"
            )

        return _create_instance(mapper_class, config)

    except MapperLoadError:
        raise
    except Exception as e:
        raise MapperLoadError(f"Error loading module {module_path}: {e}") from e


def _find_mapper_class(module: Any) -> type[BaseMapper] | None:
    """Find a BaseMapper subclass in a module.

    Args:
        module: Loaded Python module

    Returns:
        Mapper class or None if not found
    """
    # Preferred class names
    preferred_names = ["Mapper", "CustomMapper", "DocumentMapper"]

    # First, look for preferred names
    for name in preferred_names:
        if hasattr(module, name):
            cls = getattr(module, name)
            if isinstance(cls, type) and issubclass(cls, BaseMapper):
                return cls

    # Otherwise, find any BaseMapper subclass
    for name in dir(module):
        if name.startswith("_"):
            continue
        obj = getattr(module, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, BaseMapper)
            and obj is not BaseMapper
        ):
            return obj

    return None


def get_available_mappers() -> list[dict[str, Any]]:
    """Get information about all available mappers.

    Returns:
        List of dicts with mapper info
    """
    from .registry import get_mapper_info

    return [get_mapper_info(name) for name in list_mappers()]
