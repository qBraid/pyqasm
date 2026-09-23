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
- Added support for OpenQASM 2 `opaque` declarations, which previously failed at parse time and blocked vendor include files such as Quantinuum's `hqslib1.inc`. An opaque gate is treated as a black box: emitted as written, counted as one layer of depth. `to_qasm3()` rejects such a program. ([#370](https://github.com/qBraid/pyqasm/issues/370))
- Added an `include_dir` kwarg to `loads()` and `load()`, naming the directory custom `include` statements resolve against. A program given as a string could not resolve includes at all, and failed later naming the gate rather than the include. Resolution is opt-in: without the kwarg, no files are read. ([#368](https://github.com/qBraid/pyqasm/issues/368))
- Added a `compact_gate_arguments` setting, passed to `loads()` or set on the module, which prints gate arguments without spaces around `*`, `/` and `**`: `rx(pi/2)` instead of `rx(pi / 2)`. Vendors such as Diraq match rotation angles textually and reject the spaced form. ([#427](https://github.com/qBraid/pyqasm/pull/427))

### Improved / Modified

### Deprecated

### Removed

### Fixed
- Fixed bare OpenQASM expression statements raising `AttributeError` or `KeyError`. Their values are now evaluated and discarded, and unknown gate errors name the gate using the original source line. ([#388](https://github.com/qBraid/pyqasm/issues/388))

### Dependencies

### Other
- Trimmed the wheel matrix on pull requests, and added a concurrency guard that cancels superseded runs. Every push to an open pull request used to start another full 20-job matrix while the previous one ran to completion. Pull requests now build Linux on every supported Python, plus macOS arm64, macOS x86_64 and Windows on 3.11, cutting macOS jobs from 10 to 2. Pushes to `main` and manual runs still build all 20 combinations, and published wheels are unaffected. ([#419](https://github.com/qBraid/pyqasm/pull/419))
- Raised the isort floor to 9.0.0 in `tox.ini` and the `lint` extra. Both allowed isort 6, which CI never installed, and the two versions demand opposite formatting of a wrapped import that fits on one line. `tox -e format-check` therefore passed locally and failed in CI. ([#419](https://github.com/qBraid/pyqasm/pull/419))

## Past Release Notes

Archive of changelog entries from previous releases:

- [v1.2.0](https://github.com/qBraid/pyqasm/releases/tag/v1.2.0)
- [v1.1.0](https://github.com/qBraid/pyqasm/releases/tag/v1.1.0)
- [v1.0.4](https://github.com/qBraid/pyqasm/releases/tag/v1.0.4)
- [v1.0.3](https://github.com/qBraid/pyqasm/releases/tag/v1.0.3)
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
