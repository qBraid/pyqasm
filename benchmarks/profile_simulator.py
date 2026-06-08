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

"""Profiling script for PyQASM statevector simulator.

Three modes:
  1. cProfile function-level profiling
  2. Section timing (preprocess vs simulation vs post-processing)
  3. Per-kernel timing (accumulate time per opcode type)

Usage:
  python benchmarks/profile_simulator.py [--mode cprofile|section|kernel] [--qubits N] [--depth D]
"""

import argparse
import cProfile
import pstats
import random
import time
from io import StringIO

import numpy as np

from pyqasm import loads as pyqasm_loads
from pyqasm.simulator.statevector import (
    Simulator,
    _OP_CONTROLLED,
    _OP_CTRL_DIAGONAL,
    _OP_DIAGONAL,
    _OP_SINGLE,
    _OP_TWO_QUBIT,
    _fuse_gates,
    _preprocess,
)
from pyqasm.accelerate.sv_sim import (
    apply_circuit,
    apply_controlled_diagonal_gate,
    apply_controlled_gate,
    apply_diagonal_gate,
    apply_single_qubit_gate,
    apply_two_qubit_gate,
)


SINGLE_QUBIT_GATES = ["h", "x", "y", "z", "s", "t", "rx(1.0)", "ry(0.5)", "rz(0.3)"]
TWO_QUBIT_GATES = ["cx", "cy", "cz", "swap"]

OP_NAMES = {
    _OP_SINGLE: "single",
    _OP_CONTROLLED: "controlled",
    _OP_DIAGONAL: "diagonal",
    _OP_CTRL_DIAGONAL: "ctrl_diag",
    _OP_TWO_QUBIT: "two_qubit",
}


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


def mode_cprofile(num_qubits, depth):
    """Function-level profiling with cProfile."""
    qasm = generate_random_qasm(num_qubits, depth)
    sim = Simulator(seed=0)
    module = pyqasm_loads(qasm)

    print(f"\n=== cProfile: {num_qubits} qubits, depth {depth} ===\n")
    pr = cProfile.Profile()
    pr.enable()
    sim.run(module, shots=0)
    pr.disable()

    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("tottime")
    ps.print_stats(30)
    print(s.getvalue())


def mode_section(num_qubits, depth):
    """Section timing: preprocess vs simulation vs post-processing."""
    qasm = generate_random_qasm(num_qubits, depth)
    module = pyqasm_loads(qasm)
    module.unroll()
    module.remove_idle_qubits()
    nq = module.num_qubits

    print(f"\n=== Section timing: {num_qubits} qubits, depth {depth} ===\n")

    # Preprocess
    t0 = time.perf_counter_ns()
    n, opcodes, targets, controls, gate_params, diag_phases, tq_offsets, tq_gates = \
        _preprocess(module, nq)
    t1 = time.perf_counter_ns()

    # Fusion
    if n > 0:
        n, opcodes, targets, controls, gate_params, diag_phases, tq_offsets, tq_gates = \
            _fuse_gates(n, opcodes, targets, controls, gate_params, diag_phases,
                        tq_offsets, tq_gates)
    t2 = time.perf_counter_ns()

    # Simulation
    sv = np.zeros(2**nq, dtype=np.complex128)
    sv[0] = 1.0
    if n > 0:
        apply_circuit(sv, nq, opcodes, targets, controls, gate_params, diag_phases,
                      tq_offsets, tq_gates, n)
    t3 = time.perf_counter_ns()

    # Post-processing
    probabilities = np.abs(sv) ** 2
    t4 = time.perf_counter_ns()

    pre_us = (t1 - t0) / 1000
    fuse_us = (t2 - t1) / 1000
    sim_us = (t3 - t2) / 1000
    post_us = (t4 - t3) / 1000
    total_us = (t4 - t0) / 1000

    print(f"  Instructions:   {n}")
    print(f"  Preprocess:     {pre_us:10.1f} us  ({pre_us/total_us*100:5.1f}%)")
    print(f"  Gate fusion:    {fuse_us:10.1f} us  ({fuse_us/total_us*100:5.1f}%)")
    print(f"  Simulation:     {sim_us:10.1f} us  ({sim_us/total_us*100:5.1f}%)")
    print(f"  Post-process:   {post_us:10.1f} us  ({post_us/total_us*100:5.1f}%)")
    print(f"  Total:          {total_us:10.1f} us")


def mode_kernel(num_qubits, depth):
    """Per-kernel timing: accumulate time per opcode type."""
    qasm = generate_random_qasm(num_qubits, depth)
    module = pyqasm_loads(qasm)
    module.unroll()
    module.remove_idle_qubits()
    nq = module.num_qubits

    n, opcodes, targets, controls, gate_params, diag_phases, tq_offsets, tq_gates = \
        _preprocess(module, nq)
    if n > 0:
        n, opcodes, targets, controls, gate_params, diag_phases, tq_offsets, tq_gates = \
            _fuse_gates(n, opcodes, targets, controls, gate_params, diag_phases,
                        tq_offsets, tq_gates)

    sv = np.zeros(2**nq, dtype=np.complex128)
    sv[0] = 1.0

    kernel_times = {}
    kernel_counts = {}

    print(f"\n=== Per-kernel timing: {num_qubits} qubits, depth {depth} ===\n")

    for i in range(n):
        op = int(opcodes[i])
        tgt = int(targets[i])
        ctrl = int(controls[i])
        gp_off = i * 4
        dp_off = i * 2

        t0 = time.perf_counter_ns()
        if op == _OP_SINGLE:
            flat = gate_params[gp_off:gp_off + 4].copy()
            apply_single_qubit_gate(sv, nq, tgt, flat)
        elif op == _OP_CONTROLLED:
            flat = gate_params[gp_off:gp_off + 4].copy()
            apply_controlled_gate(sv, nq, ctrl, tgt, flat)
        elif op == _OP_DIAGONAL:
            apply_diagonal_gate(sv, nq, tgt, diag_phases[dp_off], diag_phases[dp_off + 1])
        elif op == _OP_CTRL_DIAGONAL:
            apply_controlled_diagonal_gate(sv, nq, ctrl, tgt, diag_phases[dp_off])
        elif op == _OP_TWO_QUBIT:
            tq_off = int(tq_offsets[i])
            flat = tq_gates[tq_off:tq_off + 16].copy()
            apply_two_qubit_gate(sv, nq, ctrl, tgt, flat)
        t1 = time.perf_counter_ns()

        name = OP_NAMES.get(op, f"op_{op}")
        kernel_times[name] = kernel_times.get(name, 0) + (t1 - t0)
        kernel_counts[name] = kernel_counts.get(name, 0) + 1

    total_ns = sum(kernel_times.values())
    for name in sorted(kernel_times.keys()):
        t_us = kernel_times[name] / 1000
        cnt = kernel_counts[name]
        pct = kernel_times[name] / total_ns * 100 if total_ns > 0 else 0
        print(f"  {name:15s}: {t_us:10.1f} us  ({pct:5.1f}%)  count={cnt}")
    print(f"  {'total':15s}: {total_ns/1000:10.1f} us")


def main():
    parser = argparse.ArgumentParser(description="Profile PyQASM simulator")
    parser.add_argument("--mode", choices=["cprofile", "section", "kernel"], default="section")
    parser.add_argument("--qubits", type=int, default=16)
    parser.add_argument("--depth", type=int, default=200)
    args = parser.parse_args()

    if args.mode == "cprofile":
        mode_cprofile(args.qubits, args.depth)
    elif args.mode == "section":
        mode_section(args.qubits, args.depth)
    elif args.mode == "kernel":
        mode_kernel(args.qubits, args.depth)


if __name__ == "__main__":
    main()
