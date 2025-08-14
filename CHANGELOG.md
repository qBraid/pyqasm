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
- Added a new `QasmModule.compare` method to compare two QASM modules, providing a detailed report of differences in gates, qubits, and measurements. This method is useful for comparing two identifying differences in QASM programs, their structure and operations. ([#233](https://github.com/qBraid/pyqasm/pull/233)) 
- Added `.github/copilot-instructions.md` to the repository to document coding standards and design principles for pyqasm. This file provides detailed guidance on documentation, static typing, formatting, error handling, and adherence to the QASM specification for all code contributions. ([#234](https://github.com/qBraid/pyqasm/pull/234))
- Added support for custom include statements in `OPENQASM3` code in pyqasm. This allows users to include custom files or libraries in their QASM programs, enhancing modularity and reusability of code. ([#236](https://github.com/qBraid/pyqasm/pull/236))
- Added support for `Angle`,`extern` and `Complex` type in `OPENQASM3` code in pyqasm. ([#239](https://github.com/qBraid/pyqasm/pull/239))
  ###### Example:
  ```qasm
  OPENQASM 3.0;
  include "stdgates.inc";
  angle[8] ang1;
  ang1 = 9 * (pi / 8);
  angle[8] ang1 = 7 * (pi / 8);
  angle[8] ang3 = ang1 + ang2;

  complex c1 = -2.5 - 3.5im;
  const complex c2 = 2.0+arccos(π/2) + (3.1 * 5.5im);
  const complex c12 = c1 * c2;

  float a = 1.0;
  int b = 2;
  extern func1(float, int) -> bit;
  bit c = 2 * func1(a, b);
  bit fc = -func1(a, b);

  bit[4] bd = "0101";
  extern func6(bit[4]) -> bit[4];
  bit[4] be1 = func6(bd);
  ```
<<<<<<< HEAD
- Added a new `QasmModule.compare` method to compare two QASM modules, providing a detailed report of differences in gates, qubits, and measurements. This method is useful for comparing two identifying differences in QASM programs, their structure and operations. ([#233](https://github.com/qBraid/pyqasm/pull/233))
=======
>>>>>>> origin/main

### Improved / Modified
- Added `slots=True` parameter to the data classes in `elements.py` to improve memory efficiency ([#218](https://github.com/qBraid/pyqasm/pull/218))
- Updated the documentation to include core features in the `README` ([#219](https://github.com/qBraid/pyqasm/pull/219))
- Added support to `device qubit` resgister consolidation.([#222](https://github.com/qBraid/pyqasm/pull/222))
- Updated the scoping of variables in `QasmVisitor` using a `ScopeManager`. This change is introduced to ensure that the `QasmVisitor` and the `PulseVisitor` can share the same `ScopeManager` instance, allowing for consistent variable scoping across different visitors. No change in the user API is expected. ([#232](https://github.com/qBraid/pyqasm/pull/232))
- Enhance function call handling by adding support for nested functions. This change allows for more complex function definitions and calls, enabling better modularity and reusability of code within QASM programs. ([#245](https://github.com/qBraid/pyqasm/pull/245))

### Deprecated

### Removed

### Fixed
- Fixed multiple axes error in circuit visualization of decomposable gates in `draw` method. ([#209](https://github.com/qBraid/pyqasm/pull/210))
- Fixed depth calculation for decomposable gates by computing depth of each constituent quantum gate.([#211](https://github.com/qBraid/pyqasm/pull/211))
- Optimized statement copying in `_visit_function_call` with shallow-copy fallback to deepcopy and added `max_loop_iters` loop‐limit check in for loops.([#223](https://github.com/qBraid/pyqasm/pull/223))


### Dependencies
- Add `pillow<11.3.0` dependency for test and visualization to avoid CI errors in Linux builds ([#226](https://github.com/qBraid/pyqasm/pull/226))
- Added `tabulate` to the testing dependencies to support new comparison table tests. ([#216](https://github.com/qBraid/pyqasm/pull/216))
- Update `docutils` requirement from <0.22 to <0.23 ([#241](https://github.com/qBraid/pyqasm/pull/241))
- Bumps `actions/download-artifact` version from 4 to 5 ([#243](https://github.com/qBraid/pyqasm/pull/243))
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
