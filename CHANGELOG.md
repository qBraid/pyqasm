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
- Added support for `gphase`, `toffoli`, `not`, `c3sx` and `c4x` gates ([#86](https://github.com/qBraid/pyqasm/pull/86))

### Improved / Modified
 - Refactored the initialization of `QasmModule` to remove default include statements. Only user supplied include statements are now added to the generated QASM code ([#86](https://github.com/qBraid/pyqasm/pull/86))

### Deprecated

### Removed

### Fixed
- Fixed bugs in implementations of `gpi2` and `prx` gates ([#86](https://github.com/qBraid/pyqasm/pull/86))

### Dependencies

## Past Release Notes

Archive of changelog entries from previous releases:

- [v0.1.0-alpha](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0-alpha)
- [v0.0.3](https://github.com/qBraid/pyqasm/releases/tag/v0.0.3)
- [v0.0.2](https://github.com/qBraid/pyqasm/releases/tag/v0.0.2)
- [v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
