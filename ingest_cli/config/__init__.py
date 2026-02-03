"""Configuration module for ingest-cli.

This module provides configuration management including:
- Pydantic-based settings model
- YAML configuration file loading
- Environment variable overrides
- Configuration validation
"""

from .exceptions import (
    ConfigFileNotFoundError,
    ConfigParseError,
    ConfigurationError,
    InvalidConfigError,
    MissingConfigError,
)
from .loader import (
    get_config_summary,
    load_config,
    load_config_from_env,
    load_yaml_file,
    validate_config_file,
)
from .settings import IngestSettings, validate_settings

__all__ = [
    # Settings model
    "IngestSettings",
    "validate_settings",
    # Loader functions
    "load_config",
    "load_config_from_env",
    "load_yaml_file",
    "validate_config_file",
    "get_config_summary",
    # Exceptions
    "ConfigurationError",
    "MissingConfigError",
    "InvalidConfigError",
    "ConfigFileNotFoundError",
    "ConfigParseError",
]
