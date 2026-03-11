# Spec 13: Mixed Bug Fixes

## Overview

This specification documents six bugs that were identified and fixed during the restart of work on ingest-cli. These fixes improve the reliability, consistency, and correctness of the ingestion pipeline.

## Bug Fixes

### 1. Fixed `ingest mappers` Command TypeError

**Problem**: The `ingest mappers` CLI command was failing with:
```
TypeError: get_mapper_info() missing 1 required positional argument: 'name'
```

**Root Cause**: The CLI code was calling `get_mapper_info()` without arguments, but the function signature required a mapper name parameter to return information about a specific mapper.

**Solution**:
- Added new function `get_all_mapper_info()` to `mappers/registry.py` that returns a list of info dicts for all registered mappers
- Updated `mappers/__init__.py` to export the new function
- Modified CLI `mappers` command to use `get_all_mapper_info()` instead of `get_mapper_info()`
- Added unit test `test_mappers_command` to prevent regression

**Files Modified**:
- `ingest_cli/mappers/registry.py`
- `ingest_cli/mappers/__init__.py`
- `ingest_cli/cli/main.py`
- `tests/test_cli/test_main.py`

---

### 2. Made Config File Handling Consistent

**Problem**: Inconsistent behavior across commands:
- `ingest check` automatically found and used default `config.yaml`
- `ingest run` required explicit `-c` flag or raised an error

**Root Cause**: The `run` command didn't include fallback logic to check for default config file.

**Solution**: Updated `run` command to check for `config.yaml` in current directory if no config specified, matching the behavior of `check` command.

**Files Modified**:
- `ingest_cli/cli/main.py`

**Code Change**:
```python
# Check for default config.yaml if no config specified
if not config_path:
    default_config = Path("config.yaml")
    if default_config.exists():
        config_path = str(default_config)
```

---

### 3. Fixed AuthClient Instantiation Error

**Problem**: The `run` command attempted to instantiate `AuthClient` and `IngestionClient` directly, causing:
```
AuthClient.__init__() missing 2 required positional arguments: 'client_secret' and 'auth_endpoint'
```

**Root Cause**: Direct class instantiation with incomplete parameters instead of using factory functions.

**Solution**: Changed to use factory functions that properly construct clients from settings:
```python
from ingest_cli.api.auth import create_auth_client
from ingest_cli.api.ingestion import create_ingestion_client

auth_client = create_auth_client(settings)
ingestion_client = create_ingestion_client(settings, auth_client)
```

**Files Modified**:
- `ingest_cli/cli/main.py`

---

### 4. Fixed CSV Reader Path Resolution

**Problem**: File paths in CSV manifests were resolved relative to the current working directory instead of relative to the CSV file's location. This caused files to not be found when running from different directories.

**Example**:
- CSV at: `/project/data/manifest.csv`
- CSV contains: `documents/file.txt`
- Old behavior: looked for `/pwd/documents/file.txt`
- New behavior: looks for `/project/data/documents/file.txt`

**Solution**: Added logic to resolve relative paths relative to the CSV file's directory:

```python
file_path = Path(file_path_str)

# If path is relative, resolve it relative to CSV file's directory
if not file_path.is_absolute():
    file_path = (source_path.parent / file_path).resolve()
```

**Files Modified**:
- `ingest_cli/readers/csv_reader.py`

---

### 5. Fixed File Upload Key Not Stored in Event

**Problem**: After uploading files to S3, the returned object key was not being stored in the event that gets sent to the API. The comment said "Store uploaded key on event" but the code only logged it.

**Root Cause**: Missing code to update the event's file property with the S3 object key after successful upload.

**Solution**: Added code to update the event's file property with the uploaded object key:

```python
upload_result = self._client.upload_file(presigned_url, document.file_path)

# Update the event's file property with the uploaded key
if "file" in event.properties:
    file_prop = event.properties["file"]
    if hasattr(file_prop, "upload_id"):
        file_prop.upload_id = upload_result.object_key
    elif isinstance(file_prop, dict):
        file_prop["upload_id"] = upload_result.object_key
```

**Files Modified**:
- `ingest_cli/pipeline/orchestrator.py`

---

### 6. Fixed Hardcoded source_id

**Problem**: The pipeline was using a hardcoded `source_id` value of "ingest-cli" instead of using the configured value from `config.yaml`:

```python
return CreateOrUpdateEvent(
    objectId=document.object_id,
    sourceId="ingest-cli",  # Hardcoded!
    sourceTimestamp=timestamp_ms,
    properties=document.properties or {},
)
```

**Root Cause**: Pipeline didn't receive or store the `source_id` from settings.

**Solution**: 
1. Added `source_id` parameter to `IngestionPipeline.__init__`
2. Stored it as `self._source_id`
3. Used it in `_build_event()` instead of hardcoded value
4. Updated `create_pipeline()` factory to pass `settings.source_id`

**Files Modified**:
- `ingest_cli/pipeline/orchestrator.py`

**Code Changes**:
```python
def __init__(
    self,
    reader: BaseReader,
    source: str,
    ingestion_client: IngestionClient | None,
    source_id: str,  # Added parameter
    mapper: BaseMapper | None = None,
    config: PipelineConfig | None = None,
) -> None:
    # ...
    self._source_id = source_id

def _build_event(self, document: Document) -> CreateOrUpdateEvent:
    return CreateOrUpdateEvent(
        objectId=document.object_id,
        sourceId=self._source_id,  # Use configured value
        sourceTimestamp=timestamp_ms,
        properties=document.properties or {},
    )
```

---

## Testing

### Test CSV Created

Created `tests/data/complete_manifest.csv` with all required fields for end-to-end testing:
- `file_path` - relative paths to documents
- `object_id` - unique document identifier
- `title` - document title  
- `doc_type` - document type
- `created_by` - creator email
- `modified_by` - modifier email
- `category`, `author` - custom metadata

### Verification

All fixes were verified through:
- ✅ Unit test execution (10/10 tests pass in `test_main.py`)
- ✅ Manual CLI testing with dry-run mode
- ✅ Path resolution testing with relative paths
- ✅ No regressions introduced

## Impact

These fixes improve:
- **Usability**: Commands work consistently without always requiring explicit config
- **Correctness**: Files are found correctly regardless of working directory
- **Data Integrity**: S3 object keys properly linked to events
- **Configuration**: Settings from config file are respected

## Completion Date

March 10, 2026
