# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

"""
Module with analysis functions for QASM visitor

"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union
from pyqasm.maps import ONE_QUBIT_OP_MAP, ONE_QUBIT_ROTATION_MAP, TWO_QUBIT_OP_MAP, THREE_QUBIT_OP_MAP, FOUR_QUBIT_OP_MAP, FIVE_QUBIT_OP_MAP, REV_CTRL_GATE_MAP
from pyqasm.expressions import Qasm3ExprEvaluator
import matplotlib as mpl
from matplotlib import pyplot as plt
import openqasm3.ast as ast

if TYPE_CHECKING:
    from pyqasm.modules.base import Qasm3Module

DEFAULT_GATE_COLOR = '#d4b6e8'
HADAMARD_GATE_COLOR = '#f0a6a6'

def draw(module: Qasm3Module, output="mpl"):
    if output == "mpl":
        return _draw_mpl(module)
    else:
        raise NotImplementedError(f"{output} drawing for Qasm3Module is unsupported")

def _draw_mpl(module: Qasm3Module) -> plt.Figure:
    module.unroll()
    module.remove_includes()
    module.remove_barriers()
    module.remove_measurements()

    n_lines = module._num_qubits + module._num_clbits
    statements = module._statements
    
    line_nums = dict()
    line_num = -1
    max_depth = 0

    for clbit_reg in module._classical_registers.keys():
        size = module._classical_registers[clbit_reg]
        line_num += size
        for i in range(size):
            line_nums[(clbit_reg, i)] = line_num
            line_num -= 1
        line_num += size

    for qubit_reg in module._qubit_registers.keys():
        size = module._qubit_registers[qubit_reg]
        line_num += size
        for i in range(size):
            line_nums[(qubit_reg, i)] = line_num
            depth = module._qubit_depths[(qubit_reg, i)]._total_ops()
            max_depth = max(max_depth, depth)
            line_num -= 1
        line_num += size
    
    fig, ax = plt.subplots(figsize=(10, n_lines * 0.7))

    for qubit_reg in module._qubit_registers.keys():
        for i in range(size):
            line_num = line_nums[(qubit_reg, i)]
            depth = module._qubit_depths[(qubit_reg, i)]._total_ops()
            _draw_mpl_qubit((qubit_reg, i), ax, line_num, max_depth)

    for clbit_reg in module._classical_registers.keys():
        for i in range(size):
            line_num = line_nums[(clbit_reg, i)]
            _draw_mpl_bit((clbit_reg, i), ax, line_num, max_depth)
    
    depths = dict()
    for k in line_nums.keys():
        depths[k] = -1

    # Draw gates
    for i, statement in enumerate(statements):
        if "Declaration" in str(type(statement)): continue
        if isinstance(statement, ast.QuantumGate):     
            args = [Qasm3ExprEvaluator.evaluate_expression(arg)[0] for arg in statement.arguments]
            qubits = [_identifier_to_key(q) for q in statement.qubits]
            draw_depth = 1 + max([depths[q] for q in qubits])
            for q in qubits: 
                depths[q] = draw_depth
            _draw_mpl_gate(statement, ax, [line_nums[q] for q in qubits], draw_depth, args)
        elif isinstance(statement, ast.QuantumMeasurementStatement):
            qubit_key = _identifier_to_key(statement.measure.qubit)
            target_key = _identifier_to_key(statement.target)
            _draw_mpl_measurement(ax, line_nums[qubit_key], line_nums[target_key], draw_depth)
        elif isinstance(statement, ast.QuantumBarrier):
            pass
        elif isinstance(statement, ast.QuantumReset):
            pass
        else:
            raise NotImplementedError(f"Unsupported statement: {statement}")
    
    ax.set_ylim(-0.5, n_lines - 0.5)
    ax.set_xlim(-0.5, max_depth) 
    ax.axis('off')
    
    plt.tight_layout()
    return fig

def _identifier_to_key(identifier: ast.Identifier | ast.IndexedIdentifier) -> tuple[str, int]:
    if isinstance(identifier, ast.Identifier):
        return identifier.name, -1
    else:
        return identifier.name.name, Qasm3ExprEvaluator.evaluate_expression(identifier.indices[0][0])[0]

def _draw_mpl_bit(bit: tuple[str, int], ax: plt.Axes, line_num: int, max_depth: int):
    ax.hlines(y=line_num, xmin=-0.125, xmax=max_depth, color='gray', linestyle='-')
    ax.text(-0.25, line_num, f'{bit[0]}[{bit[1]}]', ha='right', va='center')

def _draw_mpl_qubit(qubit: tuple[str, int], ax: plt.Axes, line_num: int, max_depth: int):
    ax.hlines(y=line_num, xmin=-0.125, xmax=max_depth, color='black', linestyle='-')
    ax.text(-0.25, line_num, f'{qubit[0]}[{qubit[1]}]', ha='right', va='center')

def _draw_mpl_gate(gate: ast.QuantumGate, ax: plt.Axes, lines: list[int], depth: int, args: list[Any]):
    print("DRAW", gate.name.name, lines, depth)
    if gate.name.name in ONE_QUBIT_OP_MAP or gate.name.name in ONE_QUBIT_ROTATION_MAP:
        _draw_mpl_one_qubit_gate(gate, ax, lines[0], depth, args)
    elif gate.name.name in TWO_QUBIT_OP_MAP:
        if gate.name.name in REV_CTRL_GATE_MAP:
            gate.name.name = REV_CTRL_GATE_MAP[gate.name.name]
            _draw_mpl_one_qubit_gate(gate, ax, lines[1], depth, args)
            _draw_mpl_control(ax, lines[0], lines[1], depth)
        elif gate.name.name == 'swap':
            _draw_mpl_swap(ax, lines[0], lines[1], depth)
        else:
            raise NotImplementedError(f"Unsupported gate: {gate.name.name}")
    else:
        raise NotImplementedError(f"Unsupported gate: {gate.name.name}")
    
def _draw_mpl_one_qubit_gate(gate: ast.QuantumGate, ax: plt.Axes, line: int, depth: int, args: list[Any]):
    color = DEFAULT_GATE_COLOR
    if gate.name.name == 'h':
        color = HADAMARD_GATE_COLOR
    text = gate.name.name.upper()
    if len(args) > 0:
        text += f"\n({', '.join([f'{a:.3f}' if isinstance(a, float) else str(a) for a in args])})"
    ax.text(depth, line, text, ha='center', va='center',
        bbox=dict(facecolor=color, edgecolor='none'))

def _draw_mpl_control(ax: plt.Axes, ctrl_line: int, target_line: int, depth: int):
    ax.vlines(x=depth, ymin=min(ctrl_line, target_line), ymax=max(ctrl_line, target_line), color='black', linestyle='-')
    ax.plot(depth, ctrl_line, 'ko', markersize=8, markerfacecolor='black')
    
def _draw_mpl_swap(ax: plt.Axes, ctrl_line: int, target_line: int, depth: int):
    ax.vlines(x=depth, ymin=min(ctrl_line, target_line), ymax=max(ctrl_line, target_line), color='black', linestyle='-')
    ax.plot(depth, ctrl_line, 'x', markersize=8, color='black')
    ax.plot(depth, target_line, 'x', markersize=8, color='black')

def _draw_mpl_measurement(ax: plt.Axes, qbit_line: int, cbit_line: int, depth: int):
    ax.plot(depth, qbit_line, 'x', markersize=8, color='black')
    ax.plot(depth, cbit_line, 'x', markersize=8, color='black')
