# Benchmarks

Scripts and reference results for the PyQASM statevector simulator
(`pyqasm.simulator.Simulator`).

## Contents

| File | What it is |
| --- | --- |
| `bench_simulator.py` | Benchmarks PyQASM against Qiskit Aer, Cirq, and PennyLane Lightning on shared random and QFT circuits, with cross-simulator correctness checks. |
| `plot_benchmarks.py` | Runs the same benchmarks and renders log-scale comparison plots (`bench_random.png`, `bench_qft.png`). |
| `profile_simulator.py` | Profiles the PyQASM simulator itself: cProfile, section timing (preprocess vs simulation vs post-processing), or per-kernel timing. |
| `bench_random.png`, `bench_qft.png` | Committed comparison plots produced by `plot_benchmarks.py`. |
| `bench_evolved.json`, `bench_qft_evolved.png`, `bench_random_evolved.png` | Historical before/after results for the evolved preprocessing change (see provenance note below). |

## Requirements

All scripts need only `pyqasm` (installed from this repo) for the PyQASM
paths. Additional dependencies:

- `bench_simulator.py`: optionally `qiskit` + `qiskit-aer`, `cirq`, and
  `pennylane` (Lightning) for the comparison columns, and `tabulate` for the
  summary table. Every one of these is optional — missing simulators are
  reported as `skipped: <name> not installed` and the script runs the
  remaining backends (worst case, PyQASM only).
- `plot_benchmarks.py`: `matplotlib`, plus the same optional simulators as
  `bench_simulator.py`. Plots include only the installed backends.
- `profile_simulator.py`: no extra dependencies.

None of these are declared as a package extra; install them ad hoc, e.g.
`pip install qiskit qiskit-aer cirq pennylane tabulate matplotlib`.

## Running

From the repository root:

```bash
# Full benchmark table (up to 22 qubits; minutes of runtime)
python benchmarks/bench_simulator.py

# Smoke test: small circuits, 2 repeats
python benchmarks/bench_simulator.py --quick

# Regenerate bench_random.png / bench_qft.png in benchmarks/
python benchmarks/plot_benchmarks.py

# Quick plot run, writing PNGs somewhere else
python benchmarks/plot_benchmarks.py --quick --out-dir /tmp/bench-plots

# Profile the simulator (modes: section | cprofile | kernel)
python benchmarks/profile_simulator.py --mode section --qubits 16 --depth 200
python benchmarks/profile_simulator.py --mode cprofile --qubits 12 --depth 100
python benchmarks/profile_simulator.py --mode kernel --qubits 12 --depth 100
```

Timing covers simulation only; circuit construction/transpilation is done in
each backend's `prepare_*` step and excluded from the measured time. Reported
numbers are the median of `N_REPEATS` runs (default 5; `--quick` uses 2,
`--repeats N` overrides).

## Provenance of the `*_evolved` files

`bench_evolved.json`, `bench_qft_evolved.png`, and `bench_random_evolved.png`
were produced during development of the evolved no-cache preprocessing change
(PR #316). They compare two states of this branch:

- **baseline**: the branch state *before* the evolved-preprocessing commit
  (the previous statevector preprocessing implementation);
- **candidate**: the branch with the evolved no-cache preprocessing.

They are retained for historical reference only. They are **not** regenerated
by any script in this tree: the baseline implementation no longer exists in
the working tree, so the before/after comparison cannot be reproduced from
the current sources alone. To reproduce something comparable, check out the
commit preceding the evolved-preprocessing commit and benchmark both
revisions with `bench_simulator.py`. Current-code performance can always be
re-measured with `bench_simulator.py` / `plot_benchmarks.py`, which
regenerate `bench_random.png` and `bench_qft.png`.
