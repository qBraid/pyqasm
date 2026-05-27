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

### Deprecated

### Removed

### Fixed
- Fixed classical register declarations not being visible inside `box` scope, causing "Missing clbit register declaration" errors for measurement statements inside box blocks. ([#306](https://github.com/qBraid/pyqasm/pull/306))
- Fixed the backend-dependent `dt` duration unit being incorrectly relabeled as `ns` when unrolling `delay` and `box` statements without a `device_cycle_time`. Since `dt` cannot be converted to SI units without a sample rate, it is now preserved as `dt`. ([#301](https://github.com/qBraid/pyqasm/issues/301))

### Dependencies
- Bumped `actions/configure-pages` from 5 to 6. ([#307](https://github.com/qBraid/pyqasm/pull/307))
- Bumped `codecov/codecov-action` from 5.5.2 to 6.0.0. ([#308](https://github.com/qBraid/pyqasm/pull/308))
- Bumped `actions/deploy-pages` from 4 to 5. ([#309](https://github.com/qBraid/pyqasm/pull/309))
- Updated `pillow` requirement from `<12.2.0` to `<12.3.0`. ([#310](https://github.com/qBraid/pyqasm/pull/310))

### Other

## Past Release Notes

Archive of changelog entries from previous releases:

- [v1.0.2](https://github.com/qBraid/pyqasm/releases/tag/v1.0.2)
- [v1.0.1](https://github.com/qBraid/pyqasm/releases/tag/v1.0.1)
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
