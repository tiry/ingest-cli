"""Configuration-specific exceptions."""


class ConfigurationError(Exception):
    """Base exception for configuration errors.

    This is raised when there's any issue with the configuration
    that prevents the CLI from operating correctly.
    """

    pass


class MissingConfigError(ConfigurationError):
    """Required configuration field is missing.

    This is raised when a required field is not provided in the
    configuration file or environment variables.
    """

    def __init__(self, field: str, message: str | None = None) -> None:
        """Initialize the exception.

        Args:
            field: The name of the missing configuration field.
            message: Optional custom message.
        """
        self.field = field
        if message is None:
            message = f"Required configuration field '{field}' is missing"
        super().__init__(message)


class InvalidConfigError(ConfigurationError):
    """Configuration value is invalid.

    This is raised when a configuration value doesn't pass validation.
    """

    def __init__(self, field: str, value: str | None = None, message: str | None = None) -> None:
        """Initialize the exception.

        Args:
            field: The name of the invalid configuration field.
            value: The invalid value (optional, may be redacted for secrets).
            message: Optional custom message.
        """
        self.field = field
        self.value = value
        if message is None:
            if value is not None:
                message = f"Invalid value for configuration field '{field}': {value}"
            else:
                message = f"Invalid value for configuration field '{field}'"
        super().__init__(message)


class ConfigFileNotFoundError(ConfigurationError):
    """Configuration file was not found.

    This is raised when the specified configuration file doesn't exist.
    """

    def __init__(self, path: str, message: str | None = None) -> None:
        """Initialize the exception.

        Args:
            path: The path to the configuration file.
            message: Optional custom message.
        """
        self.path = path
        if message is None:
            message = f"Configuration file not found: {path}"
        super().__init__(message)


class ConfigParseError(ConfigurationError):
    """Configuration file could not be parsed.

    This is raised when the configuration file has syntax errors
    or is not valid YAML.
    """

    def __init__(self, path: str, detail: str | None = None) -> None:
        """Initialize the exception.

        Args:
            path: The path to the configuration file.
            detail: Details about the parse error.
        """
        self.path = path
        self.detail = detail
        message = f"Failed to parse configuration file: {path}"
        if detail:
            message = f"{message} - {detail}"
        super().__init__(message)
