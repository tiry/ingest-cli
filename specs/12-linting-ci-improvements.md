# Linting and CI Improvements for ingest-cli

## Overview

This specification documents improvements to the linting workflow and CI pipeline for ingest-cli, inspired by the more advanced setup in ab-cli.

## Current State

### Linting in ingest-cli
- **No unified linting script**: Developers must run individual commands
- **CI runs separate jobs**: Lint, typecheck, and test jobs are separate
- **Manual command execution**: Each tool (ruff, mypy) must be run manually
- **Inconsistent workflow**: Development and CI workflows differ

### CI Pipeline Issues
- **Jobs are separate**: Test, lint, and typecheck run as independent jobs
- **No lint.sh script**: CI duplicates command execution logic
- **Badge generation**: Uses coverage-badge library (can cause dependency issues)
- **Single coverage badge**: No separation of concerns for different modules

## Improvements from ab-cli

### 1. Unified Linting Script (`lint.sh`)

ab-cli provides a comprehensive bash script that:
- Runs all linting steps in sequence
- Provides clear, colored output for each step
- Supports two modes:
  - **Development mode**: Auto-fixes issues when possible
  - **CI mode** (`--check-only`): Only checks, doesn't modify files
- Runs three tools in order:
  1. **ruff format**: Code formatting
  2. **ruff check**: Linting with auto-fix capability
  3. **mypy**: Type checking
- Uses exit codes to indicate success/failure
- Provides helpful usage information

### 2. Enhanced Ruff Configuration

ab-cli has more comprehensive ruff rules in `pyproject.toml`:

```toml
[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "B008",   # do not perform function calls in argument defaults
    "B904",   # raise without from inside except
]
```

### 3. Better CI Pipeline Structure

ab-cli has:
- **Parallel execution**: Separate jobs for linting, CLI tests, and UI tests
- **Coverage separation**: Different badges for CLI vs UI code
- **Better badge generation**: Uses shields.io directly instead of coverage-badge
- **Dependencies between jobs**: Build job only runs if all tests pass
- **Dedicated badges branch**: Cleaner approach to storing badges
- **Better artifact handling**: Multiple artifacts for different purposes

### 4. Enhanced Mypy Configuration

ab-cli has stricter type checking:

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
strict_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
```

## Implementation Plan

### Phase 1: Create lint.sh Script

1. **Create the script**: `ingest-cli/lint.sh`
   - Adapt ab-cli's script for ingest-cli structure
   - Support both dev and CI modes
   - Provide colored output and clear error messages
   - Set proper exit codes

2. **Make it executable**:
   ```bash
   chmod +x ingest-cli/lint.sh
   ```

3. **Test locally**:
   ```bash
   ./lint.sh ingest_cli/          # Dev mode - auto-fix
   ./lint.sh ingest_cli/ true     # CI mode - check only
   ```

### Phase 2: Update pyproject.toml

1. **Enhance ruff configuration**:
   - Add more comprehensive linting rules
   - Configure ignore patterns appropriately
   - Add isort configuration

2. **Enhance mypy configuration**:
   - Add stricter type checking options
   - Configure module-specific overrides if needed

### Phase 3: Update CI Workflow

1. **Simplify lint job**:
   - Use `./lint.sh ingest_cli/ true` instead of separate commands
   - Remove redundant command duplication

2. **Consolidate jobs** (optional):
   - Consider merging lint and typecheck jobs
   - Use the unified script for consistency

3. **Improve badge generation**:
   - Switch from coverage-badge to shields.io
   - Add color-coding based on coverage percentage

### Phase 4: Documentation

1. **Update README.md**:
   - Document the lint.sh script
   - Provide examples for developers
   - Explain dev vs CI modes

2. **Update developer documentation**:
   - Add linting to the development workflow
   - Document how to run checks locally before pushing

## Benefits

### For Developers
- **Single command**: Run all checks with one script
- **Auto-fix capability**: Automatically fix common issues in dev mode
- **Clear feedback**: Colored output shows what passed/failed
- **Consistency**: Same workflow locally and in CI

### For CI/CD
- **Simplified workflow**: Single script call instead of multiple steps
- **Easier maintenance**: Changes to linting steps only need to update one place
- **Better reliability**: Tested script reduces CI configuration errors
- **Faster debugging**: Easier to reproduce CI issues locally

### For Code Quality
- **More comprehensive checks**: Additional ruff rules catch more issues
- **Stricter type checking**: Better type safety with enhanced mypy config
- **Consistent formatting**: Automatic formatting enforcement
- **Progressive enhancement**: Can be extended with more tools over time

## Script Structure

The lint.sh script will have this structure:

```bash
#!/bin/bash
# Script to run code quality tools on the ingest-cli codebase
# Usage: ./lint.sh [directory] [check_only]

set -e  # Exit on error

# Configuration
TARGET_DIR=${1:-ingest_cli}
CHECK_ONLY=${2:-false}

# Colors for output
YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m'

# Step 1: ruff format
# Step 2: ruff check (with --fix in dev mode)
# Step 3: mypy type checking

# Provide clear success/failure messages
# Exit with appropriate codes
```

## Testing Strategy

1. **Test in development mode**:
   - Run with files that have formatting issues
   - Verify auto-fixes are applied
   - Check that exit codes are correct

2. **Test in CI mode**:
   - Run with clean code
   - Run with code that has issues
   - Verify no files are modified
   - Check exit codes match expectations

3. **Test error scenarios**:
   - Invalid directory
   - Syntax errors in Python files
   - Type checking failures

## Rollout Plan

1. **Create and test locally**: Ensure script works in various scenarios
2. **Update CI workflow**: Switch to using the new script
3. **Document changes**: Update README and developer docs
4. **Team communication**: Inform team about new workflow
5. **Monitor CI**: Watch for any issues after rollout

## Future Enhancements

1. **Add more tools**:
   - pylint for additional checks
   - bandit for security scanning
   - safety for dependency vulnerability checking

2. **Configuration options**:
   - Support different strictness levels
   - Allow selective tool execution

3. **IDE integration**:
   - Document how to integrate with VS Code
   - Provide pre-commit hook examples

4. **Performance optimization**:
   - Run tools in parallel where possible
   - Cache results for unchanged files

## Success Metrics

- ✅ Script runs successfully in both modes
- ✅ CI uses the unified script
- ✅ All existing checks still pass
- ✅ Exit codes correctly indicate success/failure
- ✅ No files modified in CI mode
- ✅ Auto-fixes work in dev mode
- ✅ Documentation is updated
- ✅ Team is trained on new workflow

## References

- ab-cli/lint.sh - Source script for inspiration
- ab-cli/.github/workflows/ci.yml - CI integration example
- ab-cli/pyproject.toml - Enhanced configuration example
