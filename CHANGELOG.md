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
- Added support for OpenQASM 3 `end;` statements. Unrolling stops after an unconditional `end;` in global or nested scopes and keeps `end;` inside runtime-dependent branches. ([#396](https://github.com/qBraid/pyqasm/issues/396))

### Improved / Modified

### Deprecated

### Removed

### Fixed
- Fixed `cs` and `csdg` from `stdgates.inc` being rejected during unrolling. They now decompose to controlled phase shifts. ([#439](https://github.com/qBraid/pyqasm/issues/439))
- Fixed Clifford+T rebasing for exact `rx`, `ry`, and `rz` rotations at multiples of π/4. These gates now decompose instead of disappearing, while angles outside the exact basis raise `RebaseError` instead of producing an incorrect result. ([#428](https://github.com/qBraid/pyqasm/issues/428))
- Fixed a bare expression statement raising an `AttributeError` that escaped the public API. The expression-statement handler assumed every expression was a function call and dereferenced `.name`, so a statement such as `a * b;` (used throughout the spec's classical types examples) crashed with `'BinaryExpression' object has no attribute 'name'`. Such statements have no effect and are now rejected with a `ValidationError` reading `Expression statement has no effect`, carrying the source span. ([#388](https://github.com/qBraid/pyqasm/issues/388))

### Dependencies

### Other

## Past Release Notes

Archive of changelog entries from previous releases:

- [v1.2.1](https://github.com/qBraid/pyqasm/releases/tag/v1.2.1)
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
