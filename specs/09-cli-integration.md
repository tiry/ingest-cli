# Step 9: CLI Integration

## Overview

Integrate all components into a working `ingest run` command that executes the full pipeline.

## Deliverables

### 1. CLI `run` Command Enhancement (`cli/main.py`)

Complete the `run` command to:
- Load configuration from YAML file
- Create reader from factory by name
- Create mapper (optional, defaults to IdentityMapper)
- Create auth client and ingestion client
- Create and execute the pipeline
- Display results summary

### 2. CLI Options

```bash
ingest run \
  --config/-c    Config file path (required)
  --input/-i     Input path for reader (required)
  --reader/-r    Reader name (default: csv)
  --mapper/-m    Mapper name (optional)
  --batch-size   Override config batch_size
  --offset       Skip first N documents
  --limit        Process at most N documents
  --dry-run      Validate without API calls
  --verbose      Enable debug logging
```

### 3. Pipeline Execution Logic

```python
def execute_run_command(ctx, input_file, reader_name, mapper_name, 
                         batch_size, offset, limit, dry_run):
    # 1. Load configuration
    settings = load_config(config_path)
    
    # 2. Create reader
    reader = create_reader(reader_name, settings)
    
    # 3. Create mapper (optional)
    mapper = create_mapper(mapper_name) if mapper_name else IdentityMapper()
    
    # 4. Create clients (skip if dry-run)
    ingestion_client = None
    if not dry_run:
        auth_client = AuthClient(settings)
        ingestion_client = IngestionClient(settings, auth_client)
    
    # 5. Create and run pipeline
    pipeline = create_pipeline(
        settings=settings,
        reader=reader,
        source=input_file,
        ingestion_client=ingestion_client,
        mapper=mapper,
        dry_run=dry_run,
        batch_size=batch_size,
        offset=offset,
        limit=limit,
    )
    
    result = pipeline.run()
    
    # 6. Display results
    display_results(result)
```

### 4. Results Display

```
=== Pipeline Results ===
Documents read:    100
Documents mapped:  100
Files uploaded:    50
Events sent:       100
Failed:           0
Skipped (offset): 0
Duration:         5.23s

Status: ✅ Success
```

### 5. Error Display

```
=== Pipeline Results ===
Documents read:    100
Documents mapped:  98
Files uploaded:    48
Events sent:       98
Failed:           2
Skipped (offset): 0
Duration:         5.23s

Errors:
  - Document 42: [map] Invalid field 'date_created'
  - Document 78: [send] API error 500

Status: ❌ Completed with 2 errors
```

## Tests (`tests/test_cli/test_run.py`)

### Test Cases

1. **test_run_help** - Verify help text displays all options
2. **test_run_requires_config** - Error without config
3. **test_run_requires_input** - Error without input
4. **test_run_dry_run_no_api** - Dry-run doesn't call API
5. **test_run_with_reader_option** - Reader selection works
6. **test_run_with_mapper_option** - Mapper selection works
7. **test_run_offset_and_limit** - Pagination options work
8. **test_run_results_display** - Success result output
9. **test_run_error_display** - Error result output

## Implementation Notes

- Use Click's `ctx.obj` to pass configuration between commands
- Create a `cli/run.py` module for the run-specific logic (separation of concerns)
- Handle ConfigurationError gracefully with user-friendly message
- Handle reader/mapper not found with user-friendly message
- Display progress during execution with logger.info
