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
- Added `unroll` command support in PYQASM CLI with options skipping files, overwriting originals files, and specifying output paths.([#224](https://github.com/qBraid/pyqasm/pull/224))
- Added `.github/copilot-instructions.md` to the repository to document coding standards and design principles for pyqasm. This file provides detailed guidance on documentation, static typing, formatting, error handling, and adherence to the QASM specification for all code contributions. ([#234](https://github.com/qBraid/pyqasm/pull/234))
- Added support for `Angle`,`extern` and `Complex` type in `OPENQASM3` code in pyqasm. ([#239](https://github.com/qBraid/pyqasm/pull/239))

### Improved / Modified
- Added `slots=True` parameter to the data classes in `elements.py` to improve memory efficiency ([#218](https://github.com/qBraid/pyqasm/pull/218))
- Updated the documentation to include core features in the `README` ([#219](https://github.com/qBraid/pyqasm/pull/219))
- Added support to `device qubit` resgister consolidation.([#222](https://github.com/qBraid/pyqasm/pull/222))
- Updated the scoping of variables in `QasmVisitor` using a `ScopeManager`. This change is introduced to ensure that the `QasmVisitor` and the `PulseVisitor` can share the same `ScopeManager` instance, allowing for consistent variable scoping across different visitors. No change in the user API is expected. ([#232](https://github.com/qBraid/pyqasm/pull/232))
- Added `Duration`,`Stretch` type, `Delay` and `Box` support for `OPENQASM3` code in pyqasm. ([#231](https://github.com/qBraid/pyqasm/pull/231))
  ###### Example:
  ```qasm
  OPENQASM 3.0;
  include "stdgates.inc";
  qubit[3] q;
  duration t1 = 200dt;
  duration t2 = 300ns;
  stretch s1;
  delay[t1] q[0];
  delay[t2] q[1];
  delay[s1] q[0], q[2];
  box [t2] {
    h q[0];
    cx q[0], q[1];
    delay[100ns] q[2];
  }
  ```

### Deprecated

### Removed

### Fixed
- Fixed multiple axes error in circuit visualization of decomposable gates in `draw` method. ([#209](https://github.com/qBraid/pyqasm/pull/210))
- Fixed depth calculation for decomposable gates by computing depth of each constituent quantum gate.([#211](https://github.com/qBraid/pyqasm/pull/211))
- Optimized statement copying in `_visit_function_call` with shallow-copy fallback to deepcopy and added `max_loop_iters` loop‐limit check in for loops.([#223](https://github.com/qBraid/pyqasm/pull/223))

### Dependencies
- Add `pillow<11.3.0` dependency for test and visualization to avoid CI errors in Linux builds ([#226](https://github.com/qBraid/pyqasm/pull/226))

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
