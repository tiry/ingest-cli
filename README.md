# Ingest CLI

[![CI](https://github.com/tiry/ingest-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/tiry/ingest-cli/actions/workflows/ci.yml)
[![Coverage](https://raw.githubusercontent.com/tiry/ingest-cli/badges/.github/coverage.svg)](https://github.com/tiry/ingest-cli/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python command-line tool for importing documents (files + metadata) from a local filesystem to the HxAI Ingestion REST API.

## Features

- **Pluggable Readers**: Extensible architecture for reading documents from various sources (CSV, JSON, etc.)
- **Python-based Mappers**: Transform documents using custom Python functions
- **Batch Processing**: Configurable batch sizes for efficient API usage
- **Error Handling**: Automatic retry with configurable backoff, continues on individual failures
- **Dry-Run Mode**: Validate your import without making actual API calls
- **Resume Capability**: Continue from where you stopped using `--offset`

## Installation

### From Source

```bash
# Clone the repository
git clone <repository-url>
cd ingest-cli

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## Quick Start

```bash
# Display help
ingest --help

# List available readers
ingest readers

# Validate your configuration
ingest validate -c config.yaml

# Run import (dry-run first!)
ingest -c config.yaml run -i documents.csv --dry-run

# Run actual import
ingest -c config.yaml run -i documents.csv
```

## Configuration

Create a configuration file (e.g., `config.yaml`):

```yaml
# Required settings
environment_id: "your-environment-id"
source_id: "your-source-uuid"
system_integration_id: "your-integration-id"

# Authentication
client_id: "your-client-id"   # Or use INGEST_CLIENT_ID env var
client_secret: "your-secret"  # Or use INGEST_CLIENT_SECRET env var

# Endpoints
ingest_endpoint: "https://ingestion.insight.experience.hyland.com/"
auth_endpoint: "https://auth.hyland.com/connect/token"

# Optional processing settings
batch_size: 50        # Default: 50, max: 100
retry_backoff: 2.0    # Seconds to wait before retry
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `INGEST_CLIENT_ID` | OAuth Client ID |
| `INGEST_CLIENT_SECRET` | OAuth Client Secret |
| `INGEST_CONFIG` | Default config file path |
| `INGEST_VERBOSE` | Enable verbose mode (1/true) |

## CLI Commands

### `ingest run`

Execute the document ingestion pipeline.

```bash
ingest -c config.yaml run [OPTIONS] -i INPUT_FILE

Options:
  -i, --input PATH       Path to input file (required)
  -r, --reader TEXT      Reader to use (default: csv)
  -m, --mapper TEXT      Python module path for custom mapper
  -b, --batch-size INT   Override batch size from config
  -o, --offset INT       Skip first N documents (for resume)
  --dry-run              Validate without sending to API
```

### `ingest validate`

Validate your configuration file.

```bash
ingest validate -c config.yaml
```

### `ingest readers`

List all available document readers.

```bash
ingest readers
```

## Project Structure

```
ingest-cli/
├── pyproject.toml           # Project configuration
├── README.md                 # This file
├── config.example.yaml       # Example configuration
├── ingest_cli/               # Main package
│   ├── cli/                  # CLI commands
│   ├── config/               # Configuration management
│   ├── readers/              # Document readers
│   ├── mappers/              # Document transformers
│   ├── api/                  # API clients
│   ├── models/               # Data models
│   ├── pipeline/             # Pipeline orchestration
│   └── utils/                # Utilities
├── tests/                    # Unit tests
├── examples/                 # Example files
├── openapi/                  # API specifications
└── specs/                    # Implementation specs
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ingest_cli

# Run specific tests
pytest tests/test_cli/
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy ingest_cli/
```

## Documentation

- **[Usage Guide](Usage.md)** - Detailed CLI usage instructions and examples
- **[config.example.yaml](config.example.yaml)** - Example configuration file
- **[specs/](specs/)** - Implementation specifications

## License

MIT License
