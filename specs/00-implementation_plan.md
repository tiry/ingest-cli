# Ingest CLI - Implementation Plan

## Overview

A Python CLI tool to import documents (files + metadata) from a local filesystem to the HxAI Ingestion REST API.

**Key Technologies:**
- Python 3, Click CLI framework, pytest, pyproject.toml
- Pluggable reader architecture (factory/registry pattern)
- Python-based mapping functions

**Reference Documents:**
- [seed.md](./seed.md) - Initial specification
- [OpenAPI](../openapi/insight-ingestion-merged-components.yaml) - API specification

---

## Implementation Steps

### Step 1: Project Foundation & CLI Setup ✅
**Status:** Complete (spec: `01-project-foundation-cli.md`)
**Goal:** Create the project structure with basic CLI skeleton

**Deliverables:**
- `pyproject.toml` with dependencies (click, pytest, requests, pyyaml)
- Package structure: `ingest_cli/` with `cli/`, `config/`, `readers/`, `mappers/`, `api/`, `models/`
- Basic CLI entry point with `--help`, `--version`, `--verbose`, `--config` options
- Configuration loader (YAML file with Environment, Source, Auth settings)
- Logging setup with verbose mode

**Testable Outcome:**
- `ingest --help` displays usage
- `ingest --version` displays version
- Configuration file loads and validates required fields

---

### Step 2: Configuration & Settings Module ✅
**Status:** Complete (spec: `02-configuration-settings.md`)
**Goal:** Implement robust configuration management

**Deliverables:**
- `config/settings.py` - Pydantic-based configuration model
- Support for YAML config file with all required fields:
  - EnvironmentID, SourceID, ClientID, ClientSecret, SystemIntegrationID
  - INGEST_ENDPOINT, AUTH_ENDPOINT
  - batch_size (default: 50)
  - retry_backoff (default: 2.0 seconds)
- Environment variable overrides for secrets
- Config validation with clear error messages

**Testable Outcome:**
- Valid config file loads successfully
- Missing required fields raise clear errors
- Environment variables override file values

---

### Step 3: Authentication Client ✅
**Status:** Complete (spec: `03-authentication-client.md`)
**Goal:** Implement OAuth2 client credentials flow

**Deliverables:**
- `api/auth.py` - Authentication client
- Token acquisition using ClientID/ClientSecret
- Token caching and refresh logic
- Bearer token header generation

**Testable Outcome:**
- Unit tests with mocked auth endpoint
- Token is cached and reused
- Expired token triggers refresh

---

### Step 4: Pluggable Reader Framework ✅
**Status:** Complete (spec: `04-pluggable-reader-framework.md`)
**Goal:** Create an extensible reader architecture

**Deliverables:**
- `readers/base.py` - Abstract base class `BaseReader`
- `readers/registry.py` - Reader factory/registry pattern
- `readers/csv_reader.py` - CSV file reader implementation
- Reader interface: `read() -> Iterator[dict]`
- Support for specifying file column as blob reference

**Testable Outcome:**
- CSV reader parses file and yields dicts
- Registry returns correct reader by name
- Unknown reader name raises clear error

---

### Step 5: Document Models ✅
**Status:** Complete (spec: `05-document-models.md`, 35 tests)
**Goal:** Define document and event data structures

**Deliverables:**
- `models/document.py` - Document model with metadata + optional file reference
- `models/event.py` - ContentEvent model matching API schema (createOrUpdate, delete)
- Required annotations: name, type, dateCreated, createdBy, dateModified, modifiedBy
- Property value types (string, integer, float, datetime, boolean, etc.)

**Testable Outcome:**
- Document model validates required fields
- Event serialization matches OpenAPI schema
- File metadata structure is correct

---

### Step 6: Mapper Framework 🔲
**Status:** Not started
**Goal:** Create Python-based document transformation

**Deliverables:**
- `mappers/base.py` - Abstract mapper interface `Mapper`
- `mappers/identity.py` - Identity mapper (passthrough)
- Mapper receives `dict`, returns transformed `dict`
- CLI option to specify mapper module path

**Testable Outcome:**
- Identity mapper returns input unchanged
- Custom mapper transforms document correctly
- Invalid mapper path raises clear error

---

### Step 7: Ingestion API Client 🔲
**Status:** Not started
**Goal:** Implement the HxAI Ingestion API client

**Deliverables:**
- `api/ingestion.py` - Ingestion client class
- `POST /v1/presigned-urls` - Get upload URLs for files
- `POST /v2/ingestion-events` - Send document events (batch)
- Required headers: authorization, content-type, hxp-environment, user-agent
- File upload to presigned URLs (PUT to S3)

**Testable Outcome:**
- Presigned URL request formats correctly
- Ingestion event request matches schema
- File upload to presigned URL works

---

### Step 8: Pipeline Orchestrator 🔲
**Status:** Not started
**Goal:** Implement the end-to-end pipeline

**Deliverables:**
- `pipeline/orchestrator.py` - Main pipeline logic
- Pipeline stages: Read → Map → Upload Files → Send Events
- Batch processing with configurable batch size
- Progress tracking with logging/print

**Testable Outcome:**
- Pipeline processes documents in batches
- Progress is logged after each batch
- Each stage receives correct input

---

### Step 9: Error Handling & Retry Logic 🔲
**Status:** Not started
**Goal:** Robust error handling with retry

**Deliverables:**
- `utils/retry.py` - Retry decorator with configurable backoff
- Automatic retry once on transient failures (5xx, network errors)
- Error logging with document context
- Continue processing after individual document failures
- Summary report at end (success/failure counts)

**Testable Outcome:**
- Transient error triggers retry with backoff
- Permanent error is logged and skipped
- Summary shows correct counts

---

### Step 10: CLI Commands Implementation 🔲
**Status:** Not started
**Goal:** Complete CLI interface

**Deliverables:**
- `ingest run` - Execute the import pipeline
  - `--config/-c` - Config file path
  - `--input/-i` - Input file path
  - `--reader/-r` - Reader class name (default: csv)
  - `--mapper/-m` - Mapper module path (optional)
  - `--batch-size/-b` - Override batch size
  - `--offset/-o` - Skip first N documents (resume)
  - `--dry-run` - Validate without sending
  - `--verbose/-v` - Enable verbose logging
- `ingest validate` - Validate config file
- `ingest readers` - List available readers

**Testable Outcome:**
- `ingest run --dry-run` validates without API calls
- `--offset 100` skips first 100 documents
- `--batch-size 10` overrides config value

---

### Step 11: Dry-Run Mode 🔲
**Status:** Not started
**Goal:** Complete dry-run implementation

**Deliverables:**
- Dry-run validates:
  - Config file
  - Input file readable
  - Reader can parse file
  - Mapper transforms correctly
  - Event structure is valid
- Print what would be sent (first N documents)
- No actual API calls

**Testable Outcome:**
- Dry-run catches invalid config
- Dry-run catches parse errors
- Dry-run outputs preview of events

---

### Step 12: Documentation & Examples 🔲
**Status:** Not started
**Goal:** Complete documentation

**Deliverables:**
- `README.md` - Project overview, installation, usage
- `config.example.yaml` - Example configuration file
- `examples/` folder with sample CSV and mapper
- Usage documentation for creating custom readers/mappers

**Testable Outcome:**
- README contains all required sections
- Example config is valid
- Examples run successfully

---

## Project Structure

```
ingest-cli/
├── pyproject.toml
├── README.md
├── config.example.yaml
├── ingest_cli/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py          # Click CLI
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py      # Configuration models
│   ├── readers/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract reader
│   │   ├── registry.py      # Factory/registry
│   │   └── csv_reader.py    # CSV implementation
│   ├── mappers/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract mapper
│   │   └── identity.py      # Identity mapper
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py          # OAuth client
│   │   └── ingestion.py     # Ingestion API client
│   ├── models/
│   │   ├── __init__.py
│   │   ├── document.py      # Document model
│   │   └── event.py         # ContentEvent model
│   ├── pipeline/
│   │   ├── __init__.py
│   │   └── orchestrator.py  # Pipeline logic
│   └── utils/
│       ├── __init__.py
│       ├── logging.py       # Logging setup
│       └── retry.py         # Retry decorator
├── tests/
│   ├── __init__.py
│   ├── test_config/
│   ├── test_readers/
│   ├── test_mappers/
│   ├── test_api/
│   ├── test_models/
│   ├── test_pipeline/
│   └── test_cli/
├── examples/
│   ├── sample.csv
│   └── custom_mapper.py
├── openapi/
│   └── insight-ingestion-merged-components.yaml
└── specs/
    ├── seed.md
    └── 00-implementation_plan.md
```

---

## Dependencies

```toml
[project]
name = "ingest-cli"
version = "0.1.0"
description = "CLI tool to import documents to HxAI Ingestion API"
requires-python = ">=3.10"
dependencies = [
    "click>=8.1.0",
    "pyyaml>=6.0",
    "pydantic>=2.0",
    "requests>=2.31.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "responses",
    "mypy",
]

[project.scripts]
ingest = "ingest_cli.cli.main:cli"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

---

## Configuration File Format

```yaml
# config.yaml
environment_id: "hxai-84fe439b-e9a0-44d0-84da-07235736707e"
source_id: "a52878a6-b459-4a13-bdd9-7d086f591d58"
system_integration_id: "your-system-integration-id"

# Authentication (can also use environment variables)
client_id: "${INGEST_CLIENT_ID}"
client_secret: "${INGEST_CLIENT_SECRET}"

# Endpoints
ingest_endpoint: "https://ingestion.insight.experience.hyland.com/"
auth_endpoint: "https://auth.hyland.com/connect/token"

# Processing options
batch_size: 50
retry_backoff: 2.0
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `INGEST_CLIENT_ID` | OAuth Client ID |
| `INGEST_CLIENT_SECRET` | OAuth Client Secret |
| `INGEST_CONFIG` | Default config file path |
| `INGEST_VERBOSE` | Enable verbose mode (1/true) |

---

## Notes

- Using v2/ingestion-events API (v1 is deprecated)
- Batch size limited to 100 by API
- Presigned URLs expire after 2 hours
- Required annotations for createOrUpdate: name, type, dateCreated, createdBy, dateModified, modifiedBy
