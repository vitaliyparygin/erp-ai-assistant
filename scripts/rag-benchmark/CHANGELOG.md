# Changelog

All notable changes to this project will be documented here.

The format is based on Keep a Changelog.
Versioning follows Semantic Versioning.

---

## [1.0.0] - 2026-07-15

### Added

- Document scanner
- Template-based document classifier
- Regex metadata extraction
- Template question generation
- Benchmark dataset generation
- Diagnostics engine
- Document inspection
- Markdown reports
- CLI commands
  - init
  - scan
  - generate
  - diagnose
  - inspect

### Changed

- Refactored BenchmarkPipeline API
- Added PipelineResult
- Added execute() pipeline API

### Fixed

- Diagnostics pipeline returning empty results
- Config override bug
- file=False CLI bug
- dataset path handling
- Pydantic config serialization issues