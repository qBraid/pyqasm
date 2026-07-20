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
- Added support for the `c3x` (3-controlled X) and `rc3x`/`rcccx` (relative-phase 3-controlled X) gates, decomposed into basis gates following qiskit's `C3XGate`/`RC3XGate` definitions. Also extended the `ctrl @` modifier chain so that 3- and 4-control stacks on `x` (e.g. `ctrl @ ctrl @ ctrl @ x`, `ctrl(4) @ x`) resolve to `c3x`/`c4x`. ([#320](https://github.com/qBraid/pyqasm/pull/320))

### Improved / Modified
- Consolidated the hardcoded `"__PYQASM_QUBITS__"` string literals scattered across `visitor.py`, `transformer.py` and `pulse/utils.py` into a single `INTERNAL_QUBIT_REGISTER` constant in `elements.py`, alongside an `is_internal_qubit_register()` helper that is now the one place the internal register is recognised. ([#325](https://github.com/qBraid/pyqasm/pull/325))

### Deprecated

### Removed

### Fixed
- Fixed `box` duration validation summing `delay` durations across all qubits instead of tracking each qubit's timeline. Delays on disjoint qubits run in parallel, so `box[300ns] { delay[200ns] q[0]; delay[200ns] q[1]; }` was rejected while the identical schedule written as a broadcast delay (`delay[200ns] q;`) was accepted. Delays are now accumulated per qubit and the box is validated against the busiest single timeline; the error message names the offending qubit. Nested boxes now also contribute their declared duration to the enclosing box's timelines (previously the accumulator was reset when an inner box closed, dropping all inner delay accounting). ([#330](https://github.com/qBraid/pyqasm/pull/330))
- Fixed `reset` on a physical qubit rewriting the operand to the internal pulse register, e.g. `reset $2;` unrolled to `reset __PYQASM_QUBITS__[2];`. That names a register the program never declares, so the unrolled output did not round-trip through `dumps()`/`loads()`, and the qubit was never registered (a program whose only operation was `reset $3;` reported `num_qubits == 0`). Physical qubits are now kept as-is in plain QASM programs, matching how gate and measurement operands already treat them; the rename is still applied for OpenPulse programs, where the pulse visitor expects it. ([#325](https://github.com/qBraid/pyqasm/pull/325))
- Fixed `measure` and `reset` on a user register whose name merely starts with the reserved internal register name (e.g. `__PYQASM_QUBITS__foo`) being mistaken for the internal register itself. Such statements were short-circuited out of unrolling and emitted verbatim, so `c = measure __PYQASM_QUBITS__foo;` was never expanded per qubit and `reset __PYQASM_QUBITS__foo;` silently reset nothing. The register is now matched on its exact name, or on the name followed by an index or slice. ([#325](https://github.com/qBraid/pyqasm/pull/325))
- Fixed the `c4x` (4-controlled X) gate, which previously raised `TypeError: c4x_gate() takes 4 positional arguments but 5 were given` because it was declared with four parameters for a five-qubit gate. It is now implemented via qiskit's structured `rc3x`/`c3sx`/`cphaseshift` decomposition. ([#320](https://github.com/qBraid/pyqasm/pull/320))
- Added `inv @` (inverse modifier) support for the multi-controlled-X family: `inv @ c3x` / `inv @ c4x` resolve to the (self-inverse) gate, and `inv @ rc3x` / `inv @ rcccx` resolve to the correct relative-phase dagger. These previously raised `Unsupported / undeclared QASM operation`. ([#320](https://github.com/qBraid/pyqasm/pull/320))
- Fixed the `ctrl @` modifier not resolving gate aliases: `ctrl @ toffoli` / `ctrl @ ccnot` (aliases of `ccx`) and `ctrl @ cnot` / `ctrl @ CX` (aliases of `cx`) now escalate controls identically to their canonical gate instead of raising `Unsupported controlled QASM operation`. ([#320](https://github.com/qBraid/pyqasm/pull/320))
- Fixed classical register declarations not being visible inside `box` scope, causing "Missing clbit register declaration" errors for measurement statements inside box blocks. ([#306](https://github.com/qBraid/pyqasm/pull/306))
- Fixed the backend-dependent `dt` duration unit being incorrectly relabeled as `ns` when unrolling `delay` and `box` statements without a `device_cycle_time`. Since `dt` cannot be converted to SI units without a sample rate, it is now preserved as `dt`. ([#317](https://github.com/qBraid/pyqasm/pull/317))

### Dependencies
- Migrated the Linux wheel *build container* from `manylinux2014` to `manylinux_2_28`. NumPy stopped publishing `manylinux2014` (glibc 2.17) wheels for CPython 3.12+, so `pip` fell back to building NumPy from source inside the build container, whose GCC is older than NumPy requires — failing every Linux wheel job for cp312/cp313/cp314. The published wheels are unaffected: auditwheel tags them from the extension's actual symbol requirements, so they remain `manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64` and still install on glibc 2.17 systems.
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
