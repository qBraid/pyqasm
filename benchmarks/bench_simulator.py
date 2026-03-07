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

"""Benchmark: PyQASM statevector simulator vs Qiskit Aer, Cirq,
and PennyLane Lightning.

Each simulator builds circuits programmatically from a shared gate list so the
comparison is apples-to-apples. Timing covers only simulation (circuit
construction is excluded).

Usage:
    python benchmarks/bench_simulator.py
"""

import math
import random
import time

import numpy as np
from tabulate import tabulate

# ---------------------------------------------------------------------------
# Shared circuit representation
# ---------------------------------------------------------------------------

# Gate spec: (name, qubits_tuple, params_tuple)
#   name: "h", "x", "y", "z", "s", "t", "rx", "ry", "rz", "cx", "cy", "cz",
#         "swap", "crz"
# qubits_tuple: (target,) for 1q gates, (control, target) for 2q gates
# params_tuple: () or (angle,)

SINGLE_GATE_NAMES = ["h", "x", "y", "z", "s", "t", "rx", "ry", "rz"]
TWO_GATE_NAMES = ["cx", "cy", "cz", "swap"]


def generate_random_gates(num_qubits: int, depth: int, seed: int = 42):
    """Return (num_qubits, gate_list) for a random circuit."""
    rng = random.Random(seed)
    gates = []
    for _ in range(depth):
        if num_qubits >= 2 and rng.random() < 0.4:
            name = rng.choice(TWO_GATE_NAMES)
            q0, q1 = rng.sample(range(num_qubits), 2)
            gates.append((name, (q0, q1), ()))
        else:
            name = rng.choice(SINGLE_GATE_NAMES)
            q = rng.randint(0, num_qubits - 1)
            if name == "rx":
                gates.append((name, (q,), (1.0,)))
            elif name == "ry":
                gates.append((name, (q,), (0.5,)))
            elif name == "rz":
                gates.append((name, (q,), (0.3,)))
            else:
                gates.append((name, (q,), ()))
    return num_qubits, gates


def generate_qft_gates(num_qubits: int):
    """Return (num_qubits, gate_list) for a QFT circuit."""
    gates = []
    for i in range(num_qubits):
        gates.append(("h", (i,), ()))
        for j in range(i + 1, num_qubits):
            k = j - i
            angle = math.pi / (2**k)
            gates.append(("crz", (j, i), (angle,)))
    for i in range(num_qubits // 2):
        gates.append(("swap", (i, num_qubits - 1 - i), ()))
    return num_qubits, gates


# ---------------------------------------------------------------------------
# Gate-list → QASM 3 string (for PyQASM / Qiskit)
# ---------------------------------------------------------------------------

def gates_to_qasm(num_qubits, gates):
    lines = [
        "OPENQASM 3;",
        'include "stdgates.inc";',
        f"qubit[{num_qubits}] q;",
    ]
    for name, qubits, params in gates:
        if len(qubits) == 1:
            q = qubits[0]
            if params:
                lines.append(f"{name}({params[0]}) q[{q}];")
            else:
                lines.append(f"{name} q[{q}];")
        else:
            q0, q1 = qubits
            if params:
                lines.append(f"{name}({params[0]}) q[{q0}], q[{q1}];")
            else:
                lines.append(f"{name} q[{q0}], q[{q1}];")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Simulator wrappers
# ---------------------------------------------------------------------------

N_REPEATS = 5


def _median_time(fn, n_repeats=N_REPEATS):
    """Run fn() n_repeats times, return (median_seconds, last_result)."""
    times = []
    result = None
    for _ in range(n_repeats):
        start = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - start)
    return float(np.median(times)), result


# -- PyQASM ------------------------------------------------------------------

def prepare_pyqasm(num_qubits, gates):
    from pyqasm import loads as pyqasm_loads
    from pyqasm.simulator.statevector import Simulator

    qasm = gates_to_qasm(num_qubits, gates)
    module = pyqasm_loads(qasm)
    module.unroll()
    module.remove_idle_qubits()
    sim = Simulator(seed=0)
    return module, sim


def bench_pyqasm(module, sim):
    def run():
        return sim.run(module, shots=0).final_statevector
    return _median_time(run)


# -- Qiskit Aer ---------------------------------------------------------------

def prepare_qiskit(num_qubits, gates):
    from qiskit import transpile
    from qiskit.qasm3 import loads as qiskit_loads
    from qiskit_aer import AerSimulator

    qasm = gates_to_qasm(num_qubits, gates)
    backend = AerSimulator(method="statevector")
    circuit = qiskit_loads(qasm)
    circuit.save_statevector()
    compiled = transpile(circuit, backend, optimization_level=0)
    return compiled, backend


def bench_qiskit(compiled, backend):
    def run():
        job = backend.run(compiled)
        result = job.result()
        return np.asarray(result.get_statevector(compiled))
    return _median_time(run)


# -- Cirq ----------------------------------------------------------------------

def _build_cirq_circuit(num_qubits, gates):
    import cirq

    qubits = cirq.LineQubit.range(num_qubits)
    ops = []
    for name, qubit_indices, params in gates:
        if name == "h":
            ops.append(cirq.H(qubits[qubit_indices[0]]))
        elif name == "x":
            ops.append(cirq.X(qubits[qubit_indices[0]]))
        elif name == "y":
            ops.append(cirq.Y(qubits[qubit_indices[0]]))
        elif name == "z":
            ops.append(cirq.Z(qubits[qubit_indices[0]]))
        elif name == "s":
            ops.append(cirq.S(qubits[qubit_indices[0]]))
        elif name == "t":
            ops.append(cirq.T(qubits[qubit_indices[0]]))
        elif name == "rx":
            ops.append(cirq.rx(params[0])(qubits[qubit_indices[0]]))
        elif name == "ry":
            ops.append(cirq.ry(params[0])(qubits[qubit_indices[0]]))
        elif name == "rz":
            ops.append(cirq.rz(params[0])(qubits[qubit_indices[0]]))
        elif name == "cx":
            ops.append(cirq.CNOT(qubits[qubit_indices[0]], qubits[qubit_indices[1]]))
        elif name == "cy":
            ops.append(
                cirq.ControlledGate(cirq.Y).on(
                    qubits[qubit_indices[0]], qubits[qubit_indices[1]]
                )
            )
        elif name == "cz":
            ops.append(cirq.CZ(qubits[qubit_indices[0]], qubits[qubit_indices[1]]))
        elif name == "swap":
            ops.append(cirq.SWAP(qubits[qubit_indices[0]], qubits[qubit_indices[1]]))
        elif name == "crz":
            ops.append(
                cirq.ControlledGate(cirq.rz(params[0])).on(
                    qubits[qubit_indices[0]], qubits[qubit_indices[1]]
                )
            )
    return cirq.Circuit(ops), qubits


def prepare_cirq(num_qubits, gates):
    circuit, qubits = _build_cirq_circuit(num_qubits, gates)
    import cirq
    sim = cirq.Simulator(dtype=np.complex128)
    return circuit, sim, qubits


def bench_cirq(circuit, sim, qubits):
    def run():
        result = sim.simulate(circuit, qubit_order=qubits)
        return result.final_state_vector
    return _median_time(run)


# -- PennyLane Lightning -------------------------------------------------------

def _build_pennylane_fn(num_qubits, gates):
    import pennylane as qml

    dev = qml.device("lightning.qubit", wires=num_qubits)

    gate_list = list(gates)  # capture for closure

    @qml.qnode(dev)
    def circuit():
        for name, qubit_indices, params in gate_list:
            if name == "h":
                qml.Hadamard(qubit_indices[0])
            elif name == "x":
                qml.PauliX(qubit_indices[0])
            elif name == "y":
                qml.PauliY(qubit_indices[0])
            elif name == "z":
                qml.PauliZ(qubit_indices[0])
            elif name == "s":
                qml.S(qubit_indices[0])
            elif name == "t":
                qml.T(qubit_indices[0])
            elif name == "rx":
                qml.RX(params[0], qubit_indices[0])
            elif name == "ry":
                qml.RY(params[0], qubit_indices[0])
            elif name == "rz":
                qml.RZ(params[0], qubit_indices[0])
            elif name == "cx":
                qml.CNOT([qubit_indices[0], qubit_indices[1]])
            elif name == "cy":
                qml.CY([qubit_indices[0], qubit_indices[1]])
            elif name == "cz":
                qml.CZ([qubit_indices[0], qubit_indices[1]])
            elif name == "swap":
                qml.SWAP([qubit_indices[0], qubit_indices[1]])
            elif name == "crz":
                qml.CRZ(params[0], [qubit_indices[0], qubit_indices[1]])
        return qml.state()

    return circuit


def prepare_pennylane(num_qubits, gates):
    circuit_fn = _build_pennylane_fn(num_qubits, gates)
    return (circuit_fn,)


def bench_pennylane(circuit_fn):
    def run():
        return np.asarray(circuit_fn())
    return _median_time(run)


# ---------------------------------------------------------------------------
# Qubit ordering helpers
# ---------------------------------------------------------------------------

def _reverse_endian(sv, num_qubits):
    """Convert big-endian statevector to little-endian (or vice versa)."""
    return sv.reshape([2] * num_qubits).transpose(range(num_qubits - 1, -1, -1)).ravel()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_benchmarks(circuit_name, configs, generator_fn):
    """Run all simulators on a set of circuit configs."""
    headers = [
        "Qubits", "Depth",
        "PyQASM (ms)", "Qiskit (ms)", "Cirq (ms)", "Lightning (ms)",
        "Correct",
    ]
    rows = []

    print(f"\n{'='*90}")
    print(f"  {circuit_name} circuits  (median of {N_REPEATS} runs)")
    print(f"{'='*90}")

    for config in configs:
        if len(config) == 2:
            num_qubits, depth = config
            nq, gates = generator_fn(num_qubits, depth)
        else:
            num_qubits = config[0]
            depth = None
            nq, gates = generator_fn(num_qubits)

        depth_str = str(depth) if depth is not None else "QFT"

        # --- Prepare all simulators ---
        pyqasm_args = prepare_pyqasm(nq, gates)
        qiskit_args = prepare_qiskit(nq, gates)
        cirq_args = prepare_cirq(nq, gates)
        pl_args = prepare_pennylane(nq, gates)

        # --- Benchmark ---
        t_pyqasm, sv_pyqasm = bench_pyqasm(*pyqasm_args)
        t_qiskit, sv_qiskit = bench_qiskit(*qiskit_args)
        t_cirq, sv_cirq = bench_cirq(*cirq_args)
        t_pl, sv_pl = bench_pennylane(*pl_args)

        # --- Correctness: compare all against PyQASM (little-endian) ---
        # Qiskit Aer is little-endian like PyQASM
        # Cirq, PennyLane are big-endian → convert
        sv_cirq_le = _reverse_endian(sv_cirq, nq)
        sv_pl_le = _reverse_endian(sv_pl, nq)

        checks = {
            "qiskit": np.allclose(sv_pyqasm, sv_qiskit, atol=1e-10),
            "cirq": np.allclose(sv_pyqasm, sv_cirq_le, atol=1e-10),
            "lightning": np.allclose(sv_pyqasm, sv_pl_le, atol=1e-10),
        }
        all_pass = all(checks.values())
        status = "PASS" if all_pass else "FAIL " + ",".join(
            k for k, v in checks.items() if not v
        )

        rows.append([
            nq, depth_str,
            f"{t_pyqasm*1000:.2f}",
            f"{t_qiskit*1000:.2f}",
            f"{t_cirq*1000:.2f}",
            f"{t_pl*1000:.2f}",
            status,
        ])

        print(
            f"  n={nq:2d}  depth={depth_str:>4s}  "
            f"pyqasm={t_pyqasm*1000:8.2f}  "
            f"qiskit={t_qiskit*1000:8.2f}  "
            f"cirq={t_cirq*1000:8.2f}  "
            f"lightning={t_pl*1000:8.2f} ms  "
            f"{status}"
        )

    print()
    print(tabulate(rows, headers=headers, tablefmt="github"))
    return rows


def main():
    random_configs = [
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

    qft_configs = [
        (4,),
        (6,),
        (8,),
        (10,),
        (12,),
        (14,),
        (16,),
    ]

    run_benchmarks("Random", random_configs, generate_random_gates)
    run_benchmarks("QFT", qft_configs, generate_qft_gates)


if __name__ == "__main__":
    main()
