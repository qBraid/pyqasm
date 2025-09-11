# PyQASM Profiling

This directory contains profiling data for various PyQASM functions using [py-spy](https://github.com/benfred/py-spy).

## Profiled Functions

- **unroll** - QASM unrolling performance
- **validate** - QASM validation performance  
- **qreg_consolidation** - Qubit register consolidation performance
- **openpulse** - OpenPulse functionality performance

## Test Files

[`qft_n320`](https://github.com/Qiskit/benchpress/tree/main/benchpress/qasm/qasmbench-large/qft_n320) is used for `unroll`, `validate`, and `qubit register consolidation` profiling

[`neutral_atom_gate`](../benchmarks/qasm/neutral_atom_gate.qasm) is used for `OpenPulse` profiling


## Generated Data

Each profile directory contains:
- **Flamegraphs** (`.svg` files) - Visual representation of function call stacks
- **Speedscope data** (`.json` files) - Detailed profiling data for interactive analysis
  - Upload the `.json` files to [https://www.speedscope.app/](https://www.speedscope.app/) for interactive profiling analysis.
