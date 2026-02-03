"""Configuration settings model using Pydantic."""

import re

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# UUID regex pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# URL regex pattern (simple validation)
URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")


class IngestSettings(BaseSettings):
    """Ingest CLI configuration settings.

    Settings can be loaded from:
    1. YAML configuration file
    2. Environment variables (with INGEST_ prefix)
    3. .env file

    Environment variables take precedence over file values.
    """

    model_config = SettingsConfigDict(
        env_prefix="INGEST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required identifiers
    environment_id: str = Field(
        ...,
        description="Target environment identifier",
        min_length=1,
    )
    source_id: str = Field(
        ...,
        description="Source UUID for document ingestion",
    )
    system_integration_id: str = Field(
        ...,
        description="System integration identifier",
        min_length=1,
    )

    # Authentication
    client_id: str = Field(
        ...,
        description="OAuth2 Client ID",
        min_length=1,
    )
    client_secret: str = Field(
        ...,
        description="OAuth2 Client Secret",
        min_length=1,
    )

    # API Endpoints
    ingest_endpoint: str = Field(
        default="https://ingestion.insight.experience.hyland.com/",
        description="Ingestion API base URL",
    )
    auth_endpoint: str = Field(
        default="https://auth.hyland.com/connect/token",
        description="OAuth2 token endpoint",
    )

    # Processing settings
    batch_size: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Number of documents per batch (1-100)",
    )
    retry_backoff: float = Field(
        default=2.0,
        ge=0.1,
        description="Seconds to wait between retries",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retry attempts",
    )

    @field_validator("source_id")
    @classmethod
    def validate_source_id_uuid(cls, v: str) -> str:
        """Validate that source_id is a valid UUID format."""
        if not UUID_PATTERN.match(v):
            raise ValueError(
                f"source_id must be a valid UUID format (got: {v}). "
                "Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )
        return v

    @field_validator("ingest_endpoint", "auth_endpoint")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that endpoints are valid URLs."""
        if not URL_PATTERN.match(v):
            raise ValueError(f"Invalid URL format: {v}")
        return v

    @model_validator(mode="after")
    def ensure_endpoints_have_protocol(self) -> "IngestSettings":
        """Ensure endpoint URLs are properly formatted."""
        # Ensure ingest_endpoint ends with /
        if not self.ingest_endpoint.endswith("/"):
            object.__setattr__(self, "ingest_endpoint", self.ingest_endpoint + "/")
        return self


def validate_settings(settings: IngestSettings) -> list[str]:
    """Validate settings and return list of warnings.

    Args:
        settings: The settings to validate.

    Returns:
        List of warning messages (empty if no warnings).
    """
    warnings: list[str] = []

    # Check for non-production endpoints
    if "localhost" in settings.ingest_endpoint or "127.0.0.1" in settings.ingest_endpoint:
        warnings.append("Using localhost for ingest_endpoint (development mode)")

    if "localhost" in settings.auth_endpoint or "127.0.0.1" in settings.auth_endpoint:
        warnings.append("Using localhost for auth_endpoint (development mode)")

    # Check batch size
    if settings.batch_size < 10:
        warnings.append(f"Small batch_size ({settings.batch_size}) may impact performance")

    if settings.batch_size > 75:
        warnings.append(f"Large batch_size ({settings.batch_size}) may cause timeout issues")

    # Check retry settings
    if settings.max_retries == 0:
        warnings.append("max_retries is 0 - no retries will be attempted on failures")

    return warnings
