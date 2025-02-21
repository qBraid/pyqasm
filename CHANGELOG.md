# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Types of changes:
- `Added`: for new features.
- `Improved`: for improvements to existing functionality.
- `Deprecated`: for soon-to-be removed features.
- `Removed`: for now removed features.
- `Fixed`: for any bug fixes.
- `Dependencies`: for updates to external libraries or packages.

## Unreleased

### Added
- Added support for standalone measurements that do not store the result in a classical register ([#141](https://github.com/qBraid/pyqasm/pull/141)).
- Added logic to `bump-version.yml` workflow that automatically updates `CITATION.cff` upon new release ([#147](https://github.com/qBraid/pyqasm/pull/147))

### Improved / Modified
- Re-wrote the `QasmAnalyzer.extract_qasm_version` method so that it extracts the program version just by looking at the [first non-comment line](https://github.com/openqasm/openqasm/blob/bb923eb9a84fdffe1ba6fc3c20d0b47a131523d9/source/language/comments.rst#version-string), instead of parsing the entire program ([#140](https://github.com/qBraid/pyqasm/pull/140)).

### Deprecated

### Removed

### Fixed
- Fixed bug in release workflow(s) that caused discrepancy between `pyqasm.__version__` and `importlib.metadata.version` ([#147](https://github.com/qBraid/pyqasm/pull/147))

### Dependencies

## Past Release Notes

Archive of changelog entries from previous releases:

- [v0.2.1](https://github.com/qBraid/pyqasm/releases/tag/v0.2.1)
- [v0.2.0](https://github.com/qBraid/pyqasm/releases/tag/v0.2.0)
- [v0.1.0](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0)
- [v0.1.0-alpha](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0-alpha)
- [v0.0.3](https://github.com/qBraid/pyqasm/releases/tag/v0.0.3)
- [v0.0.2](https://github.com/qBraid/pyqasm/releases/tag/v0.0.2)
- [v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
