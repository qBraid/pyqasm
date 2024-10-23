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
- Dependabot configuration file ([#37](https://github.com/qBraid/pyqasm/pull/37))
- Added better typing to linalg module + some tests ([#47](https://github.com/qBraid/pyqasm/pull/47))

### Improved / Modified
- Improved qubit declaration semantics by adding check for quantum registers being declared as predefined constants ([#44](https://github.com/qBraid/pyqasm/pull/44))
- Updated pre-release scripts + workflow ([#47](https://github.com/qBraid/pyqasm/pull/47))
- Moved pylint config from pyproject to rcfile, reduced disabled list, and moved disable flags to specific areas where applicable instead of over entire files ([#47](https://github.com/qBraid/pyqasm/pull/47))
- Consolidated duplicate code from `pyqasm.unroller.py` and `pyqasm.validate.py` into `pyqasm.entrypoint.py` with new `pyqasm.load()` function which returns a `Qasm3Module` ([#47](https://github.com/qBraid/pyqasm/pull/47))
- Updated examples in `README.md` to show outputs and explain in more detail what's happening in each example ([#47](https://github.com/qBraid/pyqasm/pull/47))

### Deprecated

### Removed

### Fixed
- Bug in initial sizes of classical registers. `bit c;` was being initialized with size `32` instead of `1` ([#43](https://github.com/qBraid/pyqasm/pull/43))
- Fixed bug in the handling of classical register type. Whenever a `bit` was referenced in an expression, it was treated as a scalar when it should be treated as an element of a 1D array with type `bit` ([#44](https://github.com/qBraid/pyqasm/pull/44))

### Dependencies
- Update sphinx-autodoc-typehints requirement from <2.5,>=1.24 to >=1.24,<2.6 ([#38](https://github.com/qBraid/pyqasm/pull/38))
- Update sphinx requirement from <8.1.0,>=7.3.7 to >=7.3.7,<8.2.0 ([#39](https://github.com/qBraid/pyqasm/pull/39))
- Update sphinx-rtd-theme requirement from <3.0.0,>=2.0.0 to >=2.0.0,<4.0.0 ([#40](https://github.com/qBraid/pyqasm/pull/40))

## Past Release Notes

Archive of changelog entries from previous releases:

- [v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
