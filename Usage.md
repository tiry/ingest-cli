# Ingest CLI Usage Guide

This guide provides detailed instructions for using the `ingest` CLI to import documents into the HxAI Ingestion API.

## Table of Contents

- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Commands](#commands)
- [Input Formats](#input-formats)
- [Custom Mappers](#custom-mappers)
- [Error Handling](#error-handling)
- [Examples](#examples)

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Valid OAuth credentials for the HxAI API
- A configured content source in your environment

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd ingest-cli

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the CLI
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Check version
ingest --version

# Display help
ingest --help
```

---

## Configuration

### Configuration File

Create a `config.yaml` file:

```yaml
# Required Settings
environment_id: "your-environment-uuid"
source_id: "your-content-source-uuid"
system_integration_id: "your-system-integration-uuid"

# Authentication (can also use environment variables)
client_id: "your-oauth-client-id"
client_secret: "your-oauth-client-secret"

# API Endpoints
ingest_endpoint: "https://ingestion.insight.experience.hyland.com/"
auth_endpoint: "https://auth.hyland.com/connect/token"

# Optional Settings
batch_size: 50          # Documents per batch (1-100, default: 50)
retry_max_attempts: 3   # Max retries on failure
retry_backoff: 2.0      # Seconds between retries
verbose: false          # Enable verbose logging
```

### Environment Variables

You can override config values with environment variables:

| Variable | Description |
|----------|-------------|
| `INGEST_CLIENT_ID` | OAuth Client ID (overrides config) |
| `INGEST_CLIENT_SECRET` | OAuth Client Secret (overrides config) |
| `INGEST_CONFIG` | Default config file path |
| `INGEST_VERBOSE` | Enable verbose mode (1/true) |

### Example: Using Environment Variables

```bash
# Set credentials via environment
export INGEST_CLIENT_ID="my-client-id"
export INGEST_CLIENT_SECRET="my-secret"

# Run without credentials in config file
ingest -c config.yaml run -i documents.csv
```

---

## Commands

### `ingest run`

Execute the document ingestion pipeline.

```bash
ingest run [OPTIONS] -i INPUT_FILE

Options:
  -c, --config PATH       Path to config file (required)
  -i, --input PATH        Path to input file (required)
  -r, --reader TEXT       Reader type (default: auto-detect from extension)
  -m, --mapper TEXT       Python mapper module path
  -b, --batch-size INT    Override batch size from config
  -o, --offset INT        Skip first N documents (for resume)
  --dry-run               Validate without making API calls
  -v, --verbose           Enable verbose output
  -h, --help              Show this help message
```

#### Examples

```bash
# Basic usage with CSV file
ingest -c config.yaml run -i documents.csv

# Dry-run to validate without making API calls
ingest -c config.yaml run -i documents.csv --dry-run

# Use a specific reader
ingest -c config.yaml run -i documents.json -r json

# Use custom batch size
ingest -c config.yaml run -i documents.csv -b 25

# Resume from document 100
ingest -c config.yaml run -i documents.csv -o 100

# Combine options
ingest -c config.yaml run -i documents.csv -b 20 -o 50 -v
```

### `ingest validate`

Validate configuration without running the pipeline.

```bash
ingest validate [OPTIONS]

Options:
  -c, --config PATH    Path to config file (required)
  -h, --help           Show this help message
```

#### Example

```bash
ingest -c config.yaml validate
```

Output:
```
✓ Configuration is valid

Settings:
  Environment ID:    abc123...
  Source ID:         def456...
  Ingest Endpoint:   https://ingestion.insight.experience.hyland.com/
  Auth Endpoint:     https://auth.hyland.com/connect/token
  Batch Size:        50
```

### `ingest readers`

List all available input readers.

```bash
ingest readers
```

Output:
```
Available readers:
  csv      - Read documents from CSV manifest files
  json     - Read documents from JSON or JSONL files
  dir      - Read documents from directory structure
```

---

## Input Formats

### CSV Reader

The CSV reader expects a manifest file with document metadata:

```csv
object_id,name,doc_type,file_path,date_created,created_by,date_modified,modified_by
doc-001,Invoice_2024.pdf,Invoice,/data/invoices/inv-001.pdf,2024-01-15T10:30:00Z,user1,2024-01-15T10:30:00Z,user1
doc-002,Contract.docx,Contract,/data/contracts/contract-001.docx,2024-01-20T14:00:00Z,user2,2024-01-22T09:00:00Z,user2
```

**Required columns:**
- `object_id` - Unique identifier for the document
- `name` - Display name
- `doc_type` - Document type classification

**Optional columns:**
- `file_path` - Path to file content (if ingesting files)
- `date_created`, `date_modified` - Timestamps
- `created_by`, `modified_by` - User identifiers
- Custom metadata columns

### JSON Reader

The JSON reader supports both single JSON objects and arrays:

```json
[
  {
    "object_id": "doc-001",
    "name": "Invoice 2024.pdf",
    "doc_type": "Invoice",
    "file_path": "/data/invoices/inv-001.pdf",
    "date_created": "2024-01-15T10:30:00Z",
    "created_by": "user1",
    "date_modified": "2024-01-15T10:30:00Z",
    "modified_by": "user1",
    "metadata": {
      "department": "Finance",
      "amount": 1500.00
    }
  }
]
```

**JSON Lines (JSONL)** - one JSON object per line:

```json
{"object_id": "doc-001", "name": "Invoice 1", "doc_type": "Invoice"}
{"object_id": "doc-002", "name": "Invoice 2", "doc_type": "Invoice"}
```

### Directory Reader

Reads documents directly from a directory structure:

```bash
# Ingest all files from a directory
ingest -c config.yaml run -i /path/to/documents -r dir
```

---

## Custom Mappers

Mappers transform documents before sending to the API. You can create custom Python mappers.

### Creating a Custom Mapper

Create a Python file with a `Mapper` class:

```python
# my_mapper.py
from ingest_cli.mappers.base import BaseMapper

class Mapper(BaseMapper):
    """Custom mapper for transforming documents."""
    
    def map(self, doc: dict) -> dict:
        """Transform a document.
        
        Args:
            doc: Input document dictionary
            
        Returns:
            Transformed document dictionary
        """
        # Add custom transformations
        return {
            "object_id": doc["id"],
            "name": doc["title"],
            "doc_type": self.classify_type(doc),
            "date_created": doc.get("created_at"),
            "created_by": doc.get("author", "unknown"),
            "date_modified": doc.get("updated_at"),
            "modified_by": doc.get("editor", "unknown"),
            "file_path": doc.get("file"),
        }
    
    def classify_type(self, doc: dict) -> str:
        """Classify document type based on content."""
        title = doc.get("title", "").lower()
        if "invoice" in title:
            return "Invoice"
        elif "contract" in title:
            return "Contract"
        return "Document"
```

### Using a Custom Mapper

```bash
# Use mapper from a Python file
ingest -c config.yaml run -i documents.csv -m ./my_mapper.py
```

### Built-in Mappers

| Mapper | Description |
|--------|-------------|
| `identity` | Pass-through mapper (default) |
| `field_mapper` | Map fields using configuration |

---

## Error Handling

### Retry Behavior

The CLI automatically retries failed API calls with exponential backoff:

- Default: 3 retry attempts
- Backoff: Starts at 2 seconds, doubles each attempt
- Configure in `config.yaml`:

```yaml
retry_max_attempts: 5
retry_backoff: 1.0
```

### Continuing After Errors

Individual document failures don't stop the pipeline. The CLI:
1. Logs the error with document ID
2. Continues processing remaining documents
3. Reports summary at the end

### Resume After Interruption

Use `--offset` to resume from a specific document:

```bash
# Resume from document 500
ingest -c config.yaml run -i documents.csv -o 500
```

### Dry-Run Validation

Always test with `--dry-run` first:

```bash
# Validate everything before actual import
ingest -c config.yaml run -i documents.csv --dry-run
```

This checks:
- Configuration validity
- Input file readability
- File paths existence (if referenced)
- API authentication (without sending data)

---

## Examples

### Example 1: Basic CSV Import

```bash
# 1. Create input CSV
cat > documents.csv << 'EOF'
object_id,name,doc_type,date_created,created_by,date_modified,modified_by
doc-001,Annual Report 2024,Report,2024-01-01T00:00:00Z,admin,2024-01-15T00:00:00Z,admin
doc-002,Q1 Financial Summary,Report,2024-04-01T00:00:00Z,finance,2024-04-05T00:00:00Z,finance
EOF

# 2. Test with dry-run
ingest -c config.yaml run -i documents.csv --dry-run

# 3. Run actual import
ingest -c config.yaml run -i documents.csv
```

### Example 2: Import with File Content

```bash
# CSV with file references
cat > manifest.csv << 'EOF'
object_id,name,doc_type,file_path
doc-001,Invoice.pdf,Invoice,/data/invoices/invoice-001.pdf
doc-002,Contract.docx,Contract,/data/contracts/contract-001.docx
EOF

# Import with file uploads
ingest -c config.yaml run -i manifest.csv
```

### Example 3: Batch Processing Large Dataset

```bash
# Process 10,000 documents in batches of 25
ingest -c config.yaml run -i large_dataset.csv -b 25 -v

# If interrupted at document 3550, resume:
ingest -c config.yaml run -i large_dataset.csv -b 25 -o 3550
```

### Example 4: JSON Import

```bash
# Create JSON input
cat > documents.json << 'EOF'
[
  {"object_id": "inv-001", "name": "Invoice 1", "doc_type": "Invoice"},
  {"object_id": "inv-002", "name": "Invoice 2", "doc_type": "Invoice"}
]
EOF

# Import JSON
ingest -c config.yaml run -i documents.json -r json
```

### Example 5: Using Environment for Credentials

```bash
# Set credentials securely
export INGEST_CLIENT_ID="$(cat /secrets/client_id)"
export INGEST_CLIENT_SECRET="$(cat /secrets/client_secret)"

# Config without secrets
cat > config.yaml << 'EOF'
environment_id: "abc-123-def"
source_id: "00000000-0000-0000-0000-000000000001"
system_integration_id: "system-001"
ingest_endpoint: "https://ingestion.insight.experience.hyland.com/"
auth_endpoint: "https://auth.hyland.com/connect/token"
batch_size: 50
EOF

# Run with env credentials
ingest -c config.yaml run -i documents.csv
```

---

## Troubleshooting

### Common Issues

**Authentication Error (401)**
```
Error: Authentication failed: Invalid credentials
```
- Check `client_id` and `client_secret`
- Verify credentials are valid for the environment
- Check if token has expired

**Source Not Found (404)**
```
Error: Source not found: abc123...
```
- Verify `source_id` is correct
- Check if content source exists in your environment

**File Not Found**
```
Error: File not found: /path/to/file.pdf
```
- Verify file paths in your input file are absolute
- Check file permissions

**Rate Limited (429)**
```
Warning: Rate limited, retrying in 5 seconds...
```
- Reduce batch size with `-b` option
- The CLI will automatically retry

### Debug Mode

Enable verbose output for debugging:

```bash
# Via command line
ingest -c config.yaml run -i documents.csv -v

# Via environment
export INGEST_VERBOSE=1
ingest -c config.yaml run -i documents.csv
```

---

## See Also

- [README.md](README.md) - Project overview
- [config.example.yaml](config.example.yaml) - Example configuration
- [specs/](specs/) - Implementation specifications
