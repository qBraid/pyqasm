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

Third-party simulators (qiskit + qiskit-aer, cirq, pennylane) are optional;
any that are not installed are skipped and the plots show only the available
backends. Requires matplotlib.

Usage:
    python benchmarks/plot_benchmarks.py [--quick] [--out-dir DIR]
"""

import argparse
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Ensure we can import from the benchmarks directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bench_simulator import (
    available_simulators,
    generate_qft_gates,
    generate_random_gates,
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

QUICK_RANDOM_CONFIGS = [(2, 10), (4, 20), (6, 30)]
QUICK_QFT_CONFIGS = [2, 4, 6]

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


def collect_times(circuit_type, configs, simulators):
    """Run benchmarks and return {simulator_name: ([qubits], [times_ms])}."""
    results = {name: ([], []) for name in simulators}

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
        for name, (prepare_fn, bench_fn, _big_endian) in simulators.items():
            args = prepare_fn(num_qubits, gates)
            t, _ = bench_fn(*args)
            results[name][0].append(num_qubits)
            results[name][1].append(t * 1000)  # ms
            print(f"  {name}={t*1000:.1f}ms", end="", flush=True)
        print()

    return results


def plot_comparison(results, title, out_path):
    """Create a log-scale line plot comparing simulators."""
    fig, ax = plt.subplots(figsize=(10, 6))

    for name, (qubits, times) in results.items():
        ax.plot(
            qubits,
            times,
            marker=MARKERS.get(name, "o"),
            color=COLORS.get(name),
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
    fig.savefig(out_path, dpi=150)
    print(f"  Saved: {out_path}")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Plot PyQASM simulator benchmarks")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Small qubit counts and fewer repeats (smoke test).",
    )
    parser.add_argument(
        "--out-dir",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Directory for the output PNGs (default: this benchmarks/ directory).",
    )
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    import bench_simulator

    if args.quick:
        bench_simulator.N_REPEATS = 2
        random_configs = QUICK_RANDOM_CONFIGS
        qft_configs = QUICK_QFT_CONFIGS
    else:
        random_configs = RANDOM_CONFIGS
        qft_configs = QFT_CONFIGS

    simulators = available_simulators(verbose=True)

    print(f"Running benchmarks (median of {bench_simulator.N_REPEATS} runs each)\n")

    print("Random circuits:")
    random_results = collect_times("random", random_configs, simulators)
    plot_comparison(
        random_results,
        "Statevector Simulation Time — Random Circuits",
        os.path.join(args.out_dir, "bench_random.png"),
    )

    print("\nQFT circuits:")
    qft_results = collect_times("qft", qft_configs, simulators)
    plot_comparison(
        qft_results,
        "Statevector Simulation Time — QFT Circuits",
        os.path.join(args.out_dir, "bench_qft.png"),
    )

    print("\nDone.")


if __name__ == "__main__":
    main()
