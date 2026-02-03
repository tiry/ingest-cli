
The file ingest-cli/specs/seed.md is the initial specification for a new project that will be in the ingest-cli folder.
The initial specifiation should be used as a starting point to build a detailed implementation plan.
Each step of the implementation plan should have clear outcome that we can validate with unit tests.

Ask any clarifying questions when building the plan.

When we move to implementation, the first step will be to save the plan into specs/00-implementation_plan.md

------


Please provide your detailed requirements for each of the following:

__1. Input Format Support__

- Which file formats should the CLI support for reading documents?
- (CSV, JSON, NDJSON/JSON Lines, Excel, or others?)

__2. Mapping Strategy__

- How should users define transformations?

  - a) YAML/JSON configuration with field mappings and simple expressions?
  - b) Python functions/classes that users implement?
  - c) A built-in DSL (Domain Specific Language)?
  - d) Combination approach?

__3. Batch Processing__

- Should automatic batching be enabled by default?
- What default batch size (API supports 1-100)?
- Should there be rate limiting?

__4. Error Handling__

- What should happen when an individual document fails?
- Should there be retry logic for transient failures?
- How should errors be reported (log file, console, summary report)?

__5. Advanced Features__ - which are in scope for v1?

- [ ] Dry-run mode
- [ ] Progress tracking
- [ ] Resume capability (continue from where it stopped)
- [ ] Digest checking (skip unchanged files)
- [ ] Verbose/debug mode


1: CSV is enough as a start, but I want the implementation to be easily pluggable. Typically in the CLI I want to be able to define the read class. This implies some factory / registry pattern.
2: Python mapping is good enough for now.
3: batch processing should be possible: setting batch size via config and allowing to override via CLI parameter
4: Log error, and automatically retry once with configurable back-off
5: Dry-run is good, progress-tracking via logging/print, resume can rely on a --offset CLI parameter, no digest needed, verbose mode is good 

