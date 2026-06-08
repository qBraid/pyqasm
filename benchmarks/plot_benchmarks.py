#!/usr/bin/env python3
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

"""Generate benchmark plots comparing PyQASM against other simulators.

Usage:
    python benchmarks/plot_benchmarks.py
"""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np

# Ensure we can import from the benchmarks directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bench_simulator import (
    N_REPEATS,
    bench_cirq,
    bench_pennylane,
    bench_pyqasm,
    bench_qiskit,
    generate_qft_gates,
    generate_random_gates,
    prepare_cirq,
    prepare_pennylane,
    prepare_pyqasm,
    prepare_qiskit,
)

RANDOM_CONFIGS = [
    (4, 20),
    (6, 40),
    (8, 60),
    (10, 80),
    (12, 100),
    (14, 150),
    (16, 200),
    (18, 250),
    (20, 300),
    (22, 400),
]

QFT_CONFIGS = [4, 6, 8, 10, 12, 14, 16, 18, 20]

SIMULATORS = {
    "PyQASM": (prepare_pyqasm, bench_pyqasm),
    "Qiskit Aer": (prepare_qiskit, bench_qiskit),
    "Cirq": (prepare_cirq, bench_cirq),
    "PennyLane Lightning": (prepare_pennylane, bench_pennylane),
}

COLORS = {
    "PyQASM": "#2563eb",
    "Qiskit Aer": "#16a34a",
    "Cirq": "#eab308",
    "PennyLane Lightning": "#dc2626",
}

MARKERS = {
    "PyQASM": "o",
    "Qiskit Aer": "s",
    "Cirq": "D",
    "PennyLane Lightning": "^",
}


def collect_times(circuit_type, configs):
    """Run benchmarks and return {simulator_name: ([qubits], [times_ms])}."""
    results = {name: ([], []) for name in SIMULATORS}

    for config in configs:
        if circuit_type == "random":
            nq, depth = config
            num_qubits, gates = generate_random_gates(nq, depth)
            label = f"n={nq}, d={depth}"
        else:
            nq = config
            num_qubits, gates = generate_qft_gates(nq)
            label = f"QFT n={nq}"

        print(f"  {label} ...", end="", flush=True)
        for name, (prepare_fn, bench_fn) in SIMULATORS.items():
            args = prepare_fn(num_qubits, gates)
            t, _ = bench_fn(*args)
            results[name][0].append(num_qubits)
            results[name][1].append(t * 1000)  # ms
            print(f"  {name}={t*1000:.1f}ms", end="", flush=True)
        print()

    return results


def plot_comparison(results, title, filename):
    """Create a log-scale line plot comparing simulators."""
    fig, ax = plt.subplots(figsize=(10, 6))

    for name in SIMULATORS:
        qubits, times = results[name]
        ax.plot(
            qubits, times,
            marker=MARKERS[name],
            color=COLORS[name],
            linewidth=2,
            markersize=7,
            label=name,
        )

    ax.set_yscale("log")
    ax.set_xlabel("Number of Qubits", fontsize=13)
    ax.set_ylabel("Simulation Time (ms)", fontsize=13)
    ax.set_title(title, fontsize=15)
    ax.legend(fontsize=11)
    ax.grid(True, which="both", ls="--", alpha=0.4)
    ax.set_xticks(results["PyQASM"][0])
    fig.tight_layout()
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    fig.savefig(out_path, dpi=150)
    print(f"  Saved: {out_path}")
    plt.close(fig)


def main():
    print(f"Running benchmarks (median of {N_REPEATS} runs each)\n")

    print("Random circuits:")
    random_results = collect_times("random", RANDOM_CONFIGS)
    plot_comparison(
        random_results,
        "Statevector Simulation Time — Random Circuits",
        "bench_random.png",
    )

    print("\nQFT circuits:")
    qft_results = collect_times("qft", QFT_CONFIGS)
    plot_comparison(
        qft_results,
        "Statevector Simulation Time — QFT Circuits",
        "bench_qft.png",
    )

    print("\nDone.")


if __name__ == "__main__":
    main()
