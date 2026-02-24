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

### Improved / Modified
- Moved the `visit_map` from the `visit_statement` function to a class level variable for improved efficiency. ([#279](https://github.com/qBraid/pyqasm/pull/279))
- Added SVG light and dark mode versions of PyQASM logo, with and without text, and added dynamic logo mode to `README.md` based on color palette used on user-side. ([#288](https://github.com/qBraid/pyqasm/pull/288))
- Updated docs with new logo, added v2 links, and applied minor Python formatting fixes for style consistency. ([#289](https://github.com/qBraid/pyqasm/pull/289))

### Deprecated

### Removed

### Fixed
- Added support for physical qubit identifiers (`$0`, `$1`, …) in plain QASM 3 programs, including gates, barriers, measurements, and duplicate-qubit detection. ([#PR_NUMBER](https://github.com/qBraid/pyqasm/pull/PR_NUMBER))
- Updated CI to use `macos-15-intel` image due to deprecation of `macos-13` image. ([#283](https://github.com/qBraid/pyqasm/pull/283))

### Dependencies
- Update `pillow` requirement from <11.4.0 to <12.1.0 ([#271](https://github.com/qBraid/pyqasm/pull/271))
- Bump `actions/download-artifact` from 5 to 6 ([#272](https://github.com/qBraid/pyqasm/pull/272))
- Bump `actions/upload-artifact` from 4 to 5 ([#273](https://github.com/qBraid/pyqasm/pull/273))

### Other

## Past Release Notes

Archive of changelog entries from previous releases:

- [v1.0.0](https://github.com/qBraid/pyqasm/releases/tag/v1.0.0)
- [v0.5.0](https://github.com/qBraid/pyqasm/releases/tag/v0.5.0)
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
