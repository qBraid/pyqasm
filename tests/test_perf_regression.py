# Copyright 2025 qBraid
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=redefined-outer-name

"""
Performance regression tests for the PyQASM statevector simulator.

These tests enforce time budgets to catch performance regressions. Each test
runs the simulator multiple times and checks that the median execution time
stays within a generous upper bound (3x the baseline measured on Apple Silicon).

Run with: pytest tests/test_perf_regression.py -v
Skip in CI: pytest -m "not benchmark"

Time budgets are intentionally loose (3x baseline) to avoid flakiness on
different hardware. The goal is catching order-of-magnitude regressions,
not enforcing tight timings.

Baselines (Apple Silicon M-series, March 2026):
  Random 16q/200d:   ~24 ms
  Random 20q/300d:  ~330 ms
  Random 22q/400d: ~1625 ms
  QFT 10q:           ~27 ms
  QFT 14q:           ~58 ms
"""

import random
import time

import numpy as np
import pytest

from pyqasm import loads as pyqasm_loads
from pyqasm.simulator.statevector import Simulator

SINGLE_QUBIT_GATES = ["h", "x", "y", "z", "s", "t", "rx(1.0)", "ry(0.5)", "rz(0.3)"]
TWO_QUBIT_GATES = ["cx", "cy", "cz", "swap"]

N_REPEATS = 5
BUDGET_MULTIPLIER = 3  # allow 3x baseline for portability across hardware


def generate_random_qasm(num_qubits: int, depth: int, seed: int = 42) -> str:
    rng = random.Random(seed)
    lines = [
        "OPENQASM 3;",
        'include "stdgates.inc";',
        f"qubit[{num_qubits}] q;",
    ]
    for _ in range(depth):
        if num_qubits >= 2 and rng.random() < 0.4:
            gate = rng.choice(TWO_QUBIT_GATES)
            q0, q1 = rng.sample(range(num_qubits), 2)
            lines.append(f"{gate} q[{q0}], q[{q1}];")
        else:
            gate = rng.choice(SINGLE_QUBIT_GATES)
            q = rng.randint(0, num_qubits - 1)
            lines.append(f"{gate} q[{q}];")
    return "\n".join(lines)


def generate_qft_qasm(num_qubits: int) -> str:
    lines = [
        "OPENQASM 3;",
        'include "stdgates.inc";',
        f"qubit[{num_qubits}] q;",
    ]
    for i in range(num_qubits):
        lines.append(f"h q[{i}];")
        for j in range(i + 1, num_qubits):
            k = j - i
            angle = f"pi/{2**k}"
            lines.append(f"crz({angle}) q[{j}], q[{i}];")
    for i in range(num_qubits // 2):
        lines.append(f"swap q[{i}], q[{num_qubits - 1 - i}];")
    return "\n".join(lines)


def median_sim_time(qasm: str, sim: Simulator, n_repeats: int = N_REPEATS) -> float:
    """Return the median wall-clock time (seconds) of sim.run() over n_repeats."""
    module = pyqasm_loads(qasm)
    module.unroll()
    module.remove_idle_qubits()
    times = []
    for _ in range(n_repeats):
        start = time.perf_counter()
        sim.run(module, shots=0)
        times.append(time.perf_counter() - start)
    return float(np.median(times))


@pytest.fixture
def sim():
    return Simulator(seed=0)


# ---------------------------------------------------------------------------
# Random circuit performance tests
# ---------------------------------------------------------------------------

@pytest.mark.benchmark
@pytest.mark.parametrize(
    "num_qubits, depth, baseline_ms",
    [
        (16, 200, 24),
        (20, 300, 330),
    ],
    ids=["random-16q", "random-20q"],
)
def test_random_circuit_perf(sim, num_qubits, depth, baseline_ms):
    """Median simulation time must stay within budget for random circuits."""
    qasm = generate_random_qasm(num_qubits, depth)
    elapsed = median_sim_time(qasm, sim)
    budget_ms = baseline_ms * BUDGET_MULTIPLIER
    elapsed_ms = elapsed * 1000
    assert elapsed_ms < budget_ms, (
        f"Random {num_qubits}q/{depth}d: {elapsed_ms:.1f} ms exceeded "
        f"budget {budget_ms:.0f} ms (baseline {baseline_ms} ms x{BUDGET_MULTIPLIER})"
    )


# ---------------------------------------------------------------------------
# QFT circuit performance tests
# ---------------------------------------------------------------------------

@pytest.mark.benchmark
@pytest.mark.parametrize(
    "num_qubits, baseline_ms",
    [
        (10, 27),
        (14, 58),
    ],
    ids=["qft-10q", "qft-14q"],
)
def test_qft_circuit_perf(sim, num_qubits, baseline_ms):
    """Median simulation time must stay within budget for QFT circuits."""
    qasm = generate_qft_qasm(num_qubits)
    elapsed = median_sim_time(qasm, sim)
    budget_ms = baseline_ms * BUDGET_MULTIPLIER
    elapsed_ms = elapsed * 1000
    assert elapsed_ms < budget_ms, (
        f"QFT {num_qubits}q: {elapsed_ms:.1f} ms exceeded "
        f"budget {budget_ms:.0f} ms (baseline {baseline_ms} ms x{BUDGET_MULTIPLIER})"
    )


# ---------------------------------------------------------------------------
# Scaling sanity check: ensure O(2^n) per gate, not worse
# ---------------------------------------------------------------------------

@pytest.mark.benchmark
def test_scaling_not_superexponential(sim):
    """Verify that doubling qubits roughly doubles per-gate time (not worse).

    Compares 14q vs 16q random circuits with the same gate count. The ratio
    of per-gate times should be near 4x (since state size quadruples with +2
    qubits). We allow up to 8x to account for cache effects and noise.
    """
    depth = 150
    qasm_14 = generate_random_qasm(14, depth)
    qasm_16 = generate_random_qasm(16, depth)

    t14 = median_sim_time(qasm_14, sim)
    t16 = median_sim_time(qasm_16, sim)

    ratio = t16 / t14
    # +2 qubits => 4x state size => expect ~4x time. Allow up to 8x.
    assert ratio < 8.0, (
        f"Scaling ratio 16q/14q = {ratio:.1f}x, expected <8x "
        f"(14q={t14*1000:.1f}ms, 16q={t16*1000:.1f}ms)"
    )
