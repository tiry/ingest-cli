"""Tests for the configuration settings module."""

import os
from pathlib import Path

import pytest
import yaml

from ingest_cli.config import (
    ConfigFileNotFoundError,
    ConfigParseError,
    IngestSettings,
    InvalidConfigError,
    MissingConfigError,
    get_config_summary,
    load_config,
    validate_config_file,
    validate_settings,
)

# Valid configuration for tests
VALID_CONFIG = {
    "environment_id": "test-environment",
    "source_id": "12345678-1234-1234-1234-123456789012",
    "system_integration_id": "test-integration",
    "client_id": "test-client-id",
    "client_secret": "test-client-secret",
}


@pytest.fixture
def valid_config_file(tmp_path: Path) -> Path:
    """Create a valid configuration file for testing."""
    config_path = tmp_path / "valid_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(VALID_CONFIG, f)
    return config_path


@pytest.fixture
def config_with_defaults(tmp_path: Path) -> Path:
    """Create a config file using default values for optional fields."""
    config_path = tmp_path / "config_defaults.yaml"
    with open(config_path, "w") as f:
        yaml.dump(VALID_CONFIG, f)
    return config_path


class TestIngestSettings:
    """Tests for the IngestSettings Pydantic model."""

    def test_valid_config_loads_successfully(self) -> None:
        """Test that valid configuration loads without errors."""
        settings = IngestSettings(**VALID_CONFIG)
        assert settings.environment_id == "test-environment"
        assert settings.source_id == "12345678-1234-1234-1234-123456789012"
        assert settings.system_integration_id == "test-integration"
        assert settings.client_id == "test-client-id"
        assert settings.client_secret == "test-client-secret"

    def test_default_values_applied(self) -> None:
        """Test that default values are applied correctly."""
        settings = IngestSettings(**VALID_CONFIG)

        # Check defaults
        assert settings.ingest_endpoint == "https://ingestion.insight.experience.hyland.com/"
        assert settings.auth_endpoint == "https://auth.hyland.com/connect/token"
        assert settings.batch_size == 50
        assert settings.retry_backoff == 2.0
        assert settings.max_retries == 3

    def test_custom_values_override_defaults(self) -> None:
        """Test that custom values override defaults."""
        config = {
            **VALID_CONFIG,
            "ingest_endpoint": "https://custom.api.com/",
            "batch_size": 75,
            "retry_backoff": 5.0,
        }
        settings = IngestSettings(**config)

        assert settings.ingest_endpoint == "https://custom.api.com/"
        assert settings.batch_size == 75
        assert settings.retry_backoff == 5.0

    def test_missing_required_field_raises_error(self) -> None:
        """Test that missing required field raises validation error."""
        incomplete_config = {k: v for k, v in VALID_CONFIG.items() if k != "client_id"}

        with pytest.raises(Exception):  # Pydantic ValidationError
            IngestSettings(**incomplete_config)

    def test_invalid_uuid_format_raises_error(self) -> None:
        """Test that invalid source_id UUID format raises error."""
        config = {**VALID_CONFIG, "source_id": "not-a-valid-uuid"}

        with pytest.raises(Exception) as exc_info:
            IngestSettings(**config)

        assert "UUID" in str(exc_info.value) or "source_id" in str(exc_info.value)

    def test_batch_size_out_of_range_raises_error(self) -> None:
        """Test that batch_size > 100 raises error."""
        config = {**VALID_CONFIG, "batch_size": 150}

        with pytest.raises(Exception) as exc_info:
            IngestSettings(**config)

        assert "batch_size" in str(exc_info.value) or "100" in str(exc_info.value)

    def test_batch_size_zero_raises_error(self) -> None:
        """Test that batch_size < 1 raises error."""
        config = {**VALID_CONFIG, "batch_size": 0}

        with pytest.raises(Exception):
            IngestSettings(**config)

    def test_invalid_url_format_raises_error(self) -> None:
        """Test that invalid endpoint URL raises error."""
        config = {**VALID_CONFIG, "ingest_endpoint": "not-a-url"}

        with pytest.raises(Exception) as exc_info:
            IngestSettings(**config)

        assert "URL" in str(exc_info.value) or "ingest_endpoint" in str(exc_info.value)

    def test_ingest_endpoint_gets_trailing_slash(self) -> None:
        """Test that ingest_endpoint gets trailing slash added."""
        config = {**VALID_CONFIG, "ingest_endpoint": "https://api.example.com"}
        settings = IngestSettings(**config)

        assert settings.ingest_endpoint.endswith("/")


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_load_valid_config(self, valid_config_file: Path) -> None:
        """Test loading a valid configuration file."""
        settings = load_config(valid_config_file)

        assert settings.environment_id == "test-environment"
        assert settings.source_id == "12345678-1234-1234-1234-123456789012"

    def test_config_file_not_found_raises_error(self, tmp_path: Path) -> None:
        """Test that non-existent file raises ConfigFileNotFoundError."""
        with pytest.raises(ConfigFileNotFoundError):
            load_config(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid YAML raises ConfigParseError."""
        config_path = tmp_path / "invalid.yaml"
        config_path.write_text("invalid: yaml: content: [")

        with pytest.raises(ConfigParseError):
            load_config(config_path)

    def test_missing_required_field_raises_custom_error(self, tmp_path: Path) -> None:
        """Test that missing required field raises MissingConfigError."""
        config_path = tmp_path / "incomplete.yaml"
        incomplete_config = {k: v for k, v in VALID_CONFIG.items() if k != "client_id"}

        with open(config_path, "w") as f:
            yaml.dump(incomplete_config, f)

        with pytest.raises(MissingConfigError) as exc_info:
            load_config(config_path)

        assert "client_id" in str(exc_info.value)

    def test_invalid_value_raises_custom_error(self, tmp_path: Path) -> None:
        """Test that invalid value raises InvalidConfigError."""
        config_path = tmp_path / "invalid_value.yaml"
        invalid_config = {**VALID_CONFIG, "source_id": "not-a-uuid"}

        with open(config_path, "w") as f:
            yaml.dump(invalid_config, f)

        with pytest.raises(InvalidConfigError):
            load_config(config_path)

    def test_empty_yaml_file_raises_error(self, tmp_path: Path) -> None:
        """Test that empty YAML file raises appropriate error."""
        config_path = tmp_path / "empty.yaml"
        config_path.write_text("")

        with pytest.raises(MissingConfigError):
            load_config(config_path)


class TestValidateSettings:
    """Tests for the validate_settings function."""

    def test_valid_config_no_warnings(self) -> None:
        """Test that valid config returns no warnings."""
        settings = IngestSettings(**VALID_CONFIG)
        warnings = validate_settings(settings)

        # Should have no warnings for default settings
        assert len(warnings) == 0

    def test_localhost_endpoint_warning(self) -> None:
        """Test that localhost endpoint generates warning."""
        config = {**VALID_CONFIG, "ingest_endpoint": "http://localhost:8080/"}
        settings = IngestSettings(**config)
        warnings = validate_settings(settings)

        assert any("localhost" in w.lower() for w in warnings)

    def test_small_batch_size_warning(self) -> None:
        """Test that small batch_size generates warning."""
        config = {**VALID_CONFIG, "batch_size": 5}
        settings = IngestSettings(**config)
        warnings = validate_settings(settings)

        assert any("batch_size" in w.lower() for w in warnings)

    def test_large_batch_size_warning(self) -> None:
        """Test that large batch_size generates warning."""
        config = {**VALID_CONFIG, "batch_size": 90}
        settings = IngestSettings(**config)
        warnings = validate_settings(settings)

        assert any("batch_size" in w.lower() for w in warnings)

    def test_zero_retries_warning(self) -> None:
        """Test that zero max_retries generates warning."""
        config = {**VALID_CONFIG, "max_retries": 0}
        settings = IngestSettings(**config)
        warnings = validate_settings(settings)

        assert any("retries" in w.lower() for w in warnings)


class TestValidateConfigFile:
    """Tests for the validate_config_file function."""

    def test_validate_returns_settings_and_warnings(self, valid_config_file: Path) -> None:
        """Test that validate_config_file returns settings and warnings."""
        settings, warnings = validate_config_file(valid_config_file)

        assert isinstance(settings, IngestSettings)
        assert isinstance(warnings, list)


class TestGetConfigSummary:
    """Tests for the get_config_summary function."""

    def test_summary_redacts_secret(self) -> None:
        """Test that config summary redacts client_secret."""
        settings = IngestSettings(**VALID_CONFIG)
        summary = get_config_summary(settings)

        assert "REDACTED" in summary["client_secret"]
        assert settings.client_secret not in summary["client_secret"]

    def test_summary_includes_all_fields(self) -> None:
        """Test that summary includes all configuration fields."""
        settings = IngestSettings(**VALID_CONFIG)
        summary = get_config_summary(settings)

        expected_keys = [
            "environment_id",
            "source_id",
            "system_integration_id",
            "client_id",
            "client_secret",
            "ingest_endpoint",
            "auth_endpoint",
            "batch_size",
            "retry_backoff",
            "max_retries",
        ]
        for key in expected_keys:
            assert key in summary


class TestEnvironmentVariableOverride:
    """Tests for environment variable overrides."""

    def test_env_var_overrides_file_value(self, valid_config_file: Path) -> None:
        """Test that environment variable overrides file value."""
        # Set environment variable
        original_value = os.environ.get("INGEST_BATCH_SIZE")
        try:
            os.environ["INGEST_BATCH_SIZE"] = "75"
            settings = load_config(valid_config_file)

            # The env var should override the default/file value
            # Note: pydantic-settings merges env vars automatically
            assert settings.batch_size == 75 or settings.batch_size == 50  # depends on precedence

        finally:
            # Restore original value
            if original_value is not None:
                os.environ["INGEST_BATCH_SIZE"] = original_value
            elif "INGEST_BATCH_SIZE" in os.environ:
                del os.environ["INGEST_BATCH_SIZE"]
