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
- A new discussion template for issues in pyqasm ([#213](https://github.com/qBraid/pyqasm/pull/213))
- A github workflow for validating `CHANGELOG` updates in a PR ([#214](https://github.com/qBraid/pyqasm/pull/214))

### Improved / Modified
- Added `slots=True` parameter to the data classes in `elements.py` to improve memory efficiency ([#218](https://github.com/qBraid/pyqasm/pull/218))
- Updated the documentation to include core features in the `README` ([#219](https://github.com/qBraid/pyqasm/pull/219))

### Deprecated

### Removed

### Fixed
- Fixed multiple axes error in circuit visualization of decomposable gates in `draw` method. ([#209](https://github.com/qBraid/pyqasm/pull/210))
- Fixed depth calculation for decomposable gates by computing depth of each constituent quantum gate.([#211](https://github.com/qBraid/pyqasm/pull/211))
- Optimized statement copying in `_visit_function_call` with shallow-copy fallback to deepcopy and added `max_loop_iters` loop‐limit check in for loops.([#223](https://github.com/qBraid/pyqasm/pull/223))
### Dependencies

### Other

## Past Release Notes

Archive of changelog entries from previous releases:

- [v0.4.0](https://github.com/qBraid/pyqasm/releases/tag/v0.4.0)
- [v0.3.2](https://github.com/qBraid/pyqasm/releases/tag/v0.3.2)
- [v0.3.1](https://github.com/qBraid/pyqasm/releases/tag/v0.3.1)
- [v0.3.0](https://github.com/qBraid/pyqasm/releases/tag/v0.3.0)
- [v0.2.1](https://github.com/qBraid/pyqasm/releases/tag/v0.2.1)
- [v0.2.0](https://github.com/qBraid/pyqasm/releases/tag/v0.2.0)
- [v0.1.0](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0)
- [v0.1.0-alpha](https://github.com/qBraid/pyqasm/releases/tag/v0.1.0-alpha)
- [v0.0.3](https://github.com/qBraid/pyqasm/releases/tag/v0.0.3)
- [v0.0.2](https://github.com/qBraid/pyqasm/releases/tag/v0.0.2)
- [v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
