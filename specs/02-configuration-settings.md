# Step 2: Configuration & Settings Module

**Status:** ✅ Completed

## Objective

Implement a robust configuration management system using Pydantic for validation, supporting YAML configuration files and environment variable overrides for sensitive values.

## Requirements

### From seed.md:
- Configuration file (YAML format) with API endpoints and authentication credentials
- Environment-based overrides for sensitive values (ClientID, ClientSecret)
- Required fields: EnvironmentID, SourceID, SystemIntegrationID
- API endpoints: INGEST_ENDPOINT, AUTH_ENDPOINT
- Batch size setting (default: 50, max: 100)

## Deliverables

### 1. Configuration Model (`ingest_cli/config/settings.py`)

Pydantic-based settings model with:

```python
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

class IngestSettings(BaseSettings):
    """Ingest CLI configuration settings."""
    
    # Required identifiers
    environment_id: str
    source_id: str  # UUID format
    system_integration_id: str
    
    # Authentication
    client_id: str
    client_secret: str
    
    # API Endpoints
    ingest_endpoint: str = "https://ingestion.insight.experience.hyland.com/"
    auth_endpoint: str = "https://auth.hyland.com/connect/token"
    
    # Processing settings
    batch_size: int = Field(default=50, ge=1, le=100)
    retry_backoff: float = Field(default=2.0, ge=0.1)
    max_retries: int = Field(default=3, ge=0)
    
    class Config:
        env_prefix = "INGEST_"
        env_file = ".env"
```

### 2. Configuration Loader (`ingest_cli/config/loader.py`)

Functions to load and validate configuration:

```python
def load_config(config_path: str | Path) -> IngestSettings:
    """Load configuration from YAML file with env var overrides."""

def validate_config(config: IngestSettings) -> list[str]:
    """Validate configuration and return list of warnings/issues."""
```

**Features:**
- Load YAML file
- Merge with environment variables (env vars take precedence)
- Validate required fields
- Validate UUID format for source_id
- Validate URL format for endpoints
- Clear error messages for missing/invalid fields

### 3. Configuration Validation

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `environment_id` | string | ✅ | Non-empty |
| `source_id` | string | ✅ | UUID format |
| `system_integration_id` | string | ✅ | Non-empty |
| `client_id` | string | ✅ | Non-empty |
| `client_secret` | string | ✅ | Non-empty |
| `ingest_endpoint` | string | ❌ (default) | Valid URL |
| `auth_endpoint` | string | ❌ (default) | Valid URL |
| `batch_size` | int | ❌ (default=50) | 1-100 |
| `retry_backoff` | float | ❌ (default=2.0) | >= 0.1 |
| `max_retries` | int | ❌ (default=3) | >= 0 |

### 4. Environment Variable Support

| Environment Variable | Config Field | Description |
|---------------------|--------------|-------------|
| `INGEST_CLIENT_ID` | `client_id` | OAuth Client ID |
| `INGEST_CLIENT_SECRET` | `client_secret` | OAuth Client Secret |
| `INGEST_ENVIRONMENT_ID` | `environment_id` | Target environment |
| `INGEST_SOURCE_ID` | `source_id` | Source UUID |
| `INGEST_BATCH_SIZE` | `batch_size` | Batch size override |

### 5. Example Configuration File

Create `config.example.yaml`:

```yaml
# Ingest CLI Configuration
# Copy this file to config.yaml and update with your values

# Required: Target Environment
environment_id: "your-environment-id"
source_id: "00000000-0000-0000-0000-000000000000"  # UUID format
system_integration_id: "your-integration-id"

# Authentication (recommend using environment variables instead)
# client_id: "your-client-id"       # Or set INGEST_CLIENT_ID
# client_secret: "your-secret"      # Or set INGEST_CLIENT_SECRET

# API Endpoints (defaults should work for production)
# ingest_endpoint: "https://ingestion.insight.experience.hyland.com/"
# auth_endpoint: "https://auth.hyland.com/connect/token"

# Processing Options
batch_size: 50          # Documents per batch (1-100)
retry_backoff: 2.0      # Seconds between retries
max_retries: 3          # Number of retry attempts
```

### 6. CLI Integration

Update `validate` command to use the new configuration:

```python
@cli.command()
def validate(ctx: click.Context, config: Optional[str]) -> None:
    """Validate configuration file."""
    try:
        settings = load_config(config_path)
        warnings = validate_config(settings)
        click.echo("✅ Configuration is valid!")
        for warning in warnings:
            click.echo(f"⚠️ {warning}")
    except ConfigurationError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        ctx.exit(1)
```

### 7. Exceptions (`ingest_cli/config/exceptions.py`)

```python
class ConfigurationError(Exception):
    """Base exception for configuration errors."""
    
class MissingConfigError(ConfigurationError):
    """Required configuration field is missing."""
    
class InvalidConfigError(ConfigurationError):
    """Configuration value is invalid."""
```

## Test Coverage

**Test file:** `tests/test_config/test_settings.py`

| Test | Description |
|------|-------------|
| `test_load_valid_config` | Valid YAML file loads successfully |
| `test_missing_required_field` | Missing required field raises error |
| `test_invalid_uuid_format` | Invalid source_id format raises error |
| `test_batch_size_out_of_range` | batch_size > 100 raises error |
| `test_env_var_override` | Environment variable overrides file value |
| `test_env_var_secrets` | Secrets can be loaded from env vars only |
| `test_default_endpoints` | Default endpoints are applied correctly |
| `test_invalid_url_format` | Invalid endpoint URL raises error |
| `test_validate_config_warnings` | Validation returns appropriate warnings |
| `test_cli_validate_command` | CLI validate command works with valid config |
| `test_cli_validate_invalid` | CLI validate command shows errors for invalid config |

## Files to Create

| File | Purpose |
|------|---------|
| `ingest_cli/config/settings.py` | Pydantic settings model |
| `ingest_cli/config/loader.py` | Configuration loading functions |
| `ingest_cli/config/exceptions.py` | Configuration-specific exceptions |
| `config.example.yaml` | Example configuration file |
| `tests/test_config/__init__.py` | Test package init |
| `tests/test_config/test_settings.py` | Configuration tests |

## Files to Modify

| File | Changes |
|------|---------|
| `ingest_cli/config/__init__.py` | Export public API |
| `ingest_cli/cli/main.py` | Integrate config loading in validate command |

## Verification

```bash
# Create a test config file
cat > test_config.yaml << EOF
environment_id: "test-env"
source_id: "12345678-1234-1234-1234-123456789012"
system_integration_id: "test-integration"
client_id: "test-client"
client_secret: "test-secret"
EOF

# Validate the config
ingest -c test_config.yaml validate

# Test with environment variable override
INGEST_BATCH_SIZE=75 ingest -c test_config.yaml validate

# Run tests
pytest tests/test_config/ -v
```

## Next Steps

→ **Step 3: Authentication Client** - Implement OAuth2 client credentials flow using the configuration settings.
