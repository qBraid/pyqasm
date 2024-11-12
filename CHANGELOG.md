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
- Added a `dumps` and `formatted_qasm` method to the `QasmModule` class to allow for the conversion of a `QasmModule` object to a string representation of the QASM code ([#71](https://github.com/qBraid/pyqasm/pull/71))
- Added the `populate_idle_qubits` method to the `QasmModule` class to populate idle qubits with an `id` gate ([#72](https://github.com/qBraid/pyqasm/pull/72))
- Added gate definitions for "c3sqrtx", "u1", "rxx", "cu3", "csx", "rccx" , "ch" , "cry", "cp", "cu", "cu1", "rzz" in `maps.py` ([#74](https://github.com/qBraid/pyqasm/pull/74))

### Improved / Modified
- Changed the `__init__` method for the `QasmModule` class to only accept an `openqasm3.ast.Program` object as input ([#71](https://github.com/qBraid/pyqasm/pull/71))

### Deprecated

### Removed
- Removed the `from_program` method from the `QasmModule` class ([#71](https://github.com/qBraid/pyqasm/pull/71))

### Fixed

### Dependencies

## Past Release Notes

Archive of changelog entries from previous releases:

- [v0.0.1](https://github.com/qBraid/pyqasm/releases/tag/v0.0.1)
