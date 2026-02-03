"""Configuration loader for loading and validating configuration files."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .exceptions import (
    ConfigFileNotFoundError,
    ConfigParseError,
    ConfigurationError,
    InvalidConfigError,
    MissingConfigError,
)
from .settings import IngestSettings, validate_settings


def load_yaml_file(config_path: str | Path) -> dict[str, Any]:
    """Load a YAML configuration file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Dictionary containing the configuration values.

    Raises:
        ConfigFileNotFoundError: If the file doesn't exist.
        ConfigParseError: If the file can't be parsed as YAML.
    """
    path = Path(config_path)

    if not path.exists():
        raise ConfigFileNotFoundError(str(path))

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigParseError(str(path), str(e)) from e
    except OSError as e:
        raise ConfigParseError(str(path), f"I/O error: {e}") from e

    # Handle empty YAML file
    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ConfigParseError(str(path), "Configuration file must contain a YAML mapping")

    return data


def load_config(config_path: str | Path) -> IngestSettings:
    """Load configuration from a YAML file with environment variable overrides.

    The loading process:
    1. Load values from the YAML configuration file
    2. Environment variables with INGEST_ prefix override file values
    3. Validate the final configuration

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Validated IngestSettings object.

    Raises:
        ConfigFileNotFoundError: If the configuration file doesn't exist.
        ConfigParseError: If the configuration file can't be parsed.
        MissingConfigError: If a required field is missing.
        InvalidConfigError: If a field value is invalid.
    """
    # Load YAML file
    yaml_config = load_yaml_file(config_path)

    # Create settings - pydantic-settings will merge with environment variables
    try:
        settings = IngestSettings(**yaml_config)
    except ValidationError as e:
        # Convert Pydantic validation errors to our custom exceptions
        _handle_validation_error(e)

    return settings


def load_config_from_env() -> IngestSettings:
    """Load configuration from environment variables only.

    This is useful when all configuration is provided via environment
    variables (e.g., in a container environment).

    Returns:
        Validated IngestSettings object.

    Raises:
        MissingConfigError: If a required field is missing.
        InvalidConfigError: If a field value is invalid.
    """
    try:
        settings = IngestSettings()  # type: ignore[call-arg]
    except ValidationError as e:
        _handle_validation_error(e)

    return settings


def _handle_validation_error(error: ValidationError) -> None:
    """Convert Pydantic ValidationError to our custom exceptions.

    Args:
        error: The Pydantic validation error.

    Raises:
        MissingConfigError: If a required field is missing.
        InvalidConfigError: If a field value is invalid.
    """
    for err in error.errors():
        field = ".".join(str(loc) for loc in err["loc"])
        msg = err["msg"]
        error_type = err["type"]

        if error_type == "missing":
            raise MissingConfigError(field)
        else:
            raise InvalidConfigError(field, message=f"{field}: {msg}")

    # Fallback if no errors found (shouldn't happen)
    raise ConfigurationError(str(error))


def validate_config_file(config_path: str | Path) -> tuple[IngestSettings, list[str]]:
    """Load and validate a configuration file, returning warnings.

    This is useful for the CLI validate command where we want to
    show both the validation result and any warnings.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Tuple of (validated settings, list of warning messages).

    Raises:
        ConfigurationError: If the configuration is invalid.
    """
    settings = load_config(config_path)
    warnings = validate_settings(settings)
    return settings, warnings


def get_config_summary(settings: IngestSettings) -> dict[str, str]:
    """Get a summary of configuration for display.

    Sensitive values like client_secret are redacted.

    Args:
        settings: The settings to summarize.

    Returns:
        Dictionary of field names to display values.
    """
    return {
        "environment_id": settings.environment_id,
        "source_id": settings.source_id,
        "system_integration_id": settings.system_integration_id,
        "client_id": settings.client_id,
        "client_secret": "***REDACTED***",
        "ingest_endpoint": settings.ingest_endpoint,
        "auth_endpoint": settings.auth_endpoint,
        "batch_size": str(settings.batch_size),
        "retry_backoff": str(settings.retry_backoff),
        "max_retries": str(settings.max_retries),
    }
