# Step 1: Project Foundation & CLI Setup

**Status:** ✅ Completed

## Objective

Set up the foundational project structure, Python packaging configuration, and basic CLI entry point for the Ingest CLI tool.

## Deliverables

### 1. Python Project Configuration (`pyproject.toml`)

Standard modern Python project configuration using `pyproject.toml` with:

- **Build system**: setuptools
- **Package name**: `ingest-cli` (import as `ingest_cli`)
- **Python version**: >=3.10
- **Entry point**: `ingest` command via `ingest_cli.cli.main:cli`

**Dependencies:**
- `click>=8.1.0` - CLI framework
- `pyyaml>=6.0` - YAML configuration parsing
- `pydantic>=2.0` - Data validation and settings
- `pydantic-settings>=2.0` - Environment variable handling
- `requests>=2.31.0` - HTTP client

**Dev Dependencies:**
- `pytest>=7.0` - Testing framework
- `pytest-cov>=4.0` - Coverage reporting
- `responses>=0.23.0` - Mock HTTP responses
- `mypy>=1.0` - Type checking
- `ruff>=0.1.0` - Linting and formatting
- `types-PyYAML>=6.0`, `types-requests>=2.31.0` - Type stubs

### 2. Package Structure

```
ingest-cli/
├── ingest_cli/
│   ├── __init__.py        # Package root with __version__
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py        # CLI entry point and commands
│   ├── config/            # Configuration management (Step 2)
│   │   └── __init__.py
│   ├── readers/           # Document readers (Step 4)
│   │   └── __init__.py
│   ├── mappers/           # Document transformers (Step 6)
│   │   └── __init__.py
│   ├── api/               # API clients (Steps 3 & 7)
│   │   └── __init__.py
│   ├── models/            # Data models (Step 5)
│   │   └── __init__.py
│   ├── pipeline/          # Pipeline orchestration (Step 8)
│   │   └── __init__.py
│   └── utils/             # Utilities (Step 9)
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   └── test_cli/
│       ├── __init__.py
│       └── test_main.py   # CLI tests
├── specs/                 # Implementation specs
├── openapi/               # API specifications
├── pyproject.toml
├── .gitignore
└── README.md
```

### 3. CLI Entry Point (`ingest_cli/cli/main.py`)

Click-based CLI with the following structure:

```python
@click.group()
@click.version_option(version=__version__)
@click.option("-v", "--verbose", is_flag=True)
@click.option("-c", "--config", type=click.Path(exists=True))
@click.pass_context
def cli(ctx, verbose, config):
    """Main CLI entry point."""
```

**Commands Implemented:**

| Command | Description | Options |
|---------|-------------|---------|
| `version` | Display version info | - |
| `readers` | List available readers | - |
| `validate` | Validate config file | - |
| `run` | Execute ingestion pipeline | `-i/--input`, `-r/--reader`, `-m/--mapper`, `-b/--batch-size`, `-o/--offset`, `--dry-run` |

### 4. Git Configuration (`.gitignore`)

Python-specific ignores including:
- `__pycache__/`, `*.pyc`
- `venv/`, `.venv/`
- `*.egg-info/`, `dist/`, `build/`
- `.env`, `.env.local`
- IDE files (`.vscode/`, `.idea/`)
- Coverage files (`.coverage`, `htmlcov/`)

### 5. README Documentation

Comprehensive README with:
- Project description and features
- Installation instructions
- Quick start guide
- Configuration file format
- Environment variables reference
- CLI command documentation
- Project structure
- Development instructions

## Test Coverage

**Test file:** `tests/test_cli/test_main.py`

| Test | Description | Status |
|------|-------------|--------|
| `test_cli_help` | `--help` displays usage | ✅ |
| `test_cli_version` | `--version` displays version | ✅ |
| `test_version_command` | `version` command works | ✅ |
| `test_readers_command` | `readers` lists available readers | ✅ |
| `test_validate_command_no_config` | `validate` requires config | ✅ |
| `test_run_command_no_config` | `run` requires config | ✅ |
| `test_cli_verbose_flag` | `-v` flag is accepted | ✅ |
| `test_run_requires_input` | `run` requires `-i` option | ✅ |
| `test_run_dry_run_flag` | `--dry-run` works with config | ✅ |

**Test Results:** 9/9 passed

## Verification

```bash
# Install package
cd ingest-cli
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Verify CLI
ingest --help
ingest --version
ingest readers

# Run tests
pytest tests/ -v

# All 9 tests should pass
```

### 6. CI/CD with GitHub Actions

GitHub Actions workflow at `.github/workflows/ci.yml` with:

**Jobs:**
1. **test** - Run pytest with coverage, generate coverage badge
2. **lint** - Run ruff check and format verification
3. **typecheck** - Run mypy type checking

**Features:**
- Triggers on push/PR to main/master branches
- Python 3.12 with pip caching
- Coverage reports (XML, HTML) with badge generation
- Coverage badge stored on separate `badges` branch
- Coverage PR comments for PRs
- Coverage HTML report archived as artifact

**README Badges:**
- CI status badge (linked to workflow)
- Coverage badge (from badges branch)
- Python version badge
- License badge

---

## Files Created

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project configuration |
| `.gitignore` | Git ignores |
| `README.md` | Documentation with badges |
| `.github/workflows/ci.yml` | GitHub Actions CI workflow |
| `ingest_cli/__init__.py` | Package root |
| `ingest_cli/cli/__init__.py` | CLI module init |
| `ingest_cli/cli/main.py` | CLI implementation |
| `ingest_cli/config/__init__.py` | Config module placeholder |
| `ingest_cli/readers/__init__.py` | Readers module placeholder |
| `ingest_cli/mappers/__init__.py` | Mappers module placeholder |
| `ingest_cli/api/__init__.py` | API module placeholder |
| `ingest_cli/models/__init__.py` | Models module placeholder |
| `ingest_cli/pipeline/__init__.py` | Pipeline module placeholder |
| `ingest_cli/utils/__init__.py` | Utils module placeholder |
| `tests/__init__.py` | Tests package |
| `tests/test_cli/__init__.py` | CLI tests package |
| `tests/test_cli/test_main.py` | CLI tests |

## Next Steps

→ **Step 2: Configuration & Settings Module** - Implement Pydantic-based configuration with YAML file parsing and environment variable overrides.
