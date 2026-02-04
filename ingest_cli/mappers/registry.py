"""Mapper registry for managing mapper implementations.

Provides a central registry for discovering and retrieving mappers.
"""

from typing import Any

from .base import BaseMapper, MapperError


class MapperNotFoundError(MapperError):
    """Raised when a requested mapper is not found."""

    def __init__(self, name: str, available: list[str]) -> None:
        self.name = name
        self.available = available
        super().__init__(f"Mapper '{name}' not found. Available: {', '.join(available)}")


class MapperRegistry:
    """Registry for mapper implementations.

    Maintains a mapping from mapper names to mapper classes.
    Built-in mappers are registered automatically.

    Example:
        >>> registry = MapperRegistry()
        >>> mapper_class = registry.get("identity")
        >>> mapper = mapper_class()
    """

    _mappers: dict[str, type[BaseMapper]]

    def __init__(self) -> None:
        """Initialize registry with built-in mappers."""
        self._mappers = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in mapper implementations."""
        # Import here to avoid circular imports
        from .field_mapper import FieldMapper
        from .identity import IdentityMapper

        self.register(IdentityMapper)
        self.register(FieldMapper)

    def register(
        self,
        mapper_class: type[BaseMapper],
        name: str | None = None,
    ) -> None:
        """Register a mapper class.

        Args:
            mapper_class: Mapper class to register
            name: Override name (defaults to mapper.name property)
        """
        # Get name from class instance
        if name is None:
            # Create temporary instance to get name
            instance = mapper_class.__new__(mapper_class)
            # Initialize with empty args if needed
            try:
                instance.__init__()  # type: ignore
            except TypeError:
                # Mapper requires args, try to get name from property
                pass
            name = instance.name

        self._mappers[name] = mapper_class

    def get(self, name: str) -> type[BaseMapper]:
        """Get mapper class by name.

        Args:
            name: Mapper name

        Returns:
            Mapper class

        Raises:
            MapperNotFoundError: If mapper not found
        """
        if name not in self._mappers:
            raise MapperNotFoundError(name, self.list_mappers())
        return self._mappers[name]

    def list_mappers(self) -> list[str]:
        """List all registered mapper names.

        Returns:
            List of mapper names
        """
        return sorted(self._mappers.keys())

    def get_info(self, name: str) -> dict[str, Any]:
        """Get information about a registered mapper.

        Args:
            name: Mapper name

        Returns:
            Dict with mapper info (name, description)

        Raises:
            MapperNotFoundError: If mapper not found
        """
        mapper_class = self.get(name)
        return {
            "name": name,
            "class": mapper_class.__name__,
            "description": (mapper_class.__doc__ or "").split("\n")[0].strip(),
        }


# Global registry instance
_registry = MapperRegistry()


def get_mapper(name: str) -> type[BaseMapper]:
    """Get mapper class by name from global registry.

    Args:
        name: Mapper name

    Returns:
        Mapper class

    Raises:
        MapperNotFoundError: If mapper not found
    """
    return _registry.get(name)


def list_mappers() -> list[str]:
    """List all registered mapper names.

    Returns:
        List of mapper names
    """
    return _registry.list_mappers()


def get_mapper_info(name: str) -> dict[str, Any]:
    """Get information about a registered mapper.

    Args:
        name: Mapper name

    Returns:
        Dict with mapper info
    """
    return _registry.get_info(name)


def register_mapper(
    mapper_class: type[BaseMapper],
    name: str | None = None,
) -> None:
    """Register a mapper class in global registry.

    Args:
        mapper_class: Mapper class to register
        name: Override name
    """
    _registry.register(mapper_class, name)
