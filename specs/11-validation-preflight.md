# Step 11: Validation & Pre-flight Checks

**Reference:** `specs/00-implementation_plan.md` - Step 11: Dry-Run Mode

## Overview

Implement a validation module that performs pre-flight checks to catch errors early before actual API calls. This supports:
1. The `--dry-run` CLI option
2. The `ingest validate` command
3. Input validation before pipeline execution

## Goals

1. Create a validation module for pre-flight checks
2. Validate configuration, input files, reader/mapper, and document structure
3. Provide clear error reporting with actionable messages
4. Support dry-run mode that previews what would be sent

## Deliverables

### 1. Validation Module (`validation/validator.py`)

```python
@dataclass
class ValidationResult:
    """Result of a validation check."""
    valid: bool
    errors: list[str]
    warnings: list[str]

class PipelineValidator:
    """Validates pipeline configuration and input."""
    
    def validate_config(self, config: Settings) -> ValidationResult:
        """Validate configuration settings."""
    
    def validate_input_file(self, input_path: Path) -> ValidationResult:
        """Validate input file exists and is readable."""
    
    def validate_reader(self, reader: BaseReader, input_path: Path) -> ValidationResult:
        """Validate reader can parse the input file."""
    
    def validate_mapper(self, mapper: BaseMapper, sample_docs: list[dict]) -> ValidationResult:
        """Validate mapper transforms documents correctly."""
    
    def validate_documents(self, documents: list[Document]) -> ValidationResult:
        """Validate document structure meets API requirements."""
    
    def validate_all(self, config: Settings, input_path: Path, 
                     reader: BaseReader, mapper: BaseMapper) -> ValidationResult:
        """Run all validation checks."""
```

### 2. Document Validation

Validate documents meet API requirements:
- Required annotations present (name, type, dateCreated, createdBy, dateModified, modifiedBy)
- Valid property types and values
- File references exist (if file_column specified)
- Property names follow conventions

### 3. Dry-Run Output

When `--dry-run` is specified:
- Show summary of what would be processed
- Preview first N documents (configurable, default 3)
- Show document count and batch count
- No API calls made

### 4. CLI Integration

Enhance existing CLI:
- Add `ingest validate CONFIG_FILE` command
- Ensure `--dry-run` performs validation preview

## Validation Checks

### Configuration Validation
- [ ] Required fields present
- [ ] Endpoints are valid URLs
- [ ] Batch size within limits (1-100)

### Input Validation
- [ ] Input file exists
- [ ] Input file is readable
- [ ] File extension matches reader type

### Reader Validation
- [ ] Reader can parse first few records
- [ ] Required columns exist (if specified)
- [ ] No parse errors in sample

### Mapper Validation
- [ ] Mapper runs without errors
- [ ] Output is valid document structure

### Document Validation
- [ ] Required annotations present
- [ ] Property values have valid types
- [ ] File paths exist (if specified)

## Test Cases

1. **Valid configuration passes** - All checks should pass
2. **Missing required field** - Clear error message
3. **Invalid input file** - File not found error
4. **Reader parse error** - Show parse error with line number
5. **Mapper error** - Show transformation error
6. **Missing required annotation** - Show which annotation is missing
7. **Invalid property type** - Show property name and expected type
8. **Dry-run preview** - Shows document preview without API calls

## Files to Create/Modify

- `ingest_cli/validation/__init__.py` - Module init
- `ingest_cli/validation/validator.py` - Validation logic
- `tests/test_validation/__init__.py` - Test module
- `tests/test_validation/test_validator.py` - Unit tests
- `ingest_cli/cli/main.py` - Add validate command

## Success Criteria

- [ ] All validation checks implemented
- [ ] Clear error messages with context
- [ ] Dry-run shows preview without API calls
- [ ] `ingest validate` command works
- [ ] All unit tests pass
