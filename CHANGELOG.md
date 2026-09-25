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
- Added a statevector simulator as a new `pyqasm.simulator` subpackage, backed by a Cython/OpenMP-capable kernel (`pyqasm.accelerate.sv_sim`). `Simulator.run()` accepts an OpenQASM 3 string or an already-unrolled `QasmModule` and returns a `SimulatorResult` carrying the final statevector, outcome probabilities, and sampled measurement counts, all indexed little-endian to match qiskit. Ships with cross-validation tests against qiskit (`test-sim` extra), an optional `simulation` extra (numba-accelerated preprocessing helpers), and a `benchmarks/` suite. ([#316](https://github.com/qBraid/pyqasm/pull/316))

  ```python
  from pyqasm.simulator import Simulator

  program = """
  OPENQASM 3.0;
  include "stdgates.inc";
  qubit[2] q;
  bit[2] c;
  h q[0];
  cx q[0], q[1];
  c = measure q;
  """

  result = Simulator(seed=42).run(program, shots=1000)

  print(result.measurement_counts)  # Counter({'00': 503, '11': 497})
  print(result.final_statevector)   # [0.70710678+0.j 0.+0.j 0.+0.j 0.70710678+0.j]
  ```
- Added support for OpenQASM 3 `end;` statements. Unrolling stops after an unconditional `end;` in global or nested scopes and keeps `end;` inside runtime-dependent branches. ([#396](https://github.com/qBraid/pyqasm/issues/396))

### Improved / Modified

### Deprecated

### Removed

### Fixed
- Fixed `cs` and `csdg` from `stdgates.inc` being rejected during unrolling. They now decompose to controlled phase shifts. ([#439](https://github.com/qBraid/pyqasm/issues/439))
- Fixed Clifford+T rebasing for exact `rx`, `ry`, and `rz` rotations at multiples of π/4. These gates now decompose instead of disappearing, while angles outside the exact basis raise `RebaseError` instead of producing an incorrect result. ([#428](https://github.com/qBraid/pyqasm/issues/428))

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
