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
from pyqasm.modules import Qasm2Module, Qasm3Module, QasmModule
from pyqasm.maps import ONE_QUBIT_OP_MAP, TWO_QUBIT_OP_MAP, THREE_QUBIT_OP_MAP, FOUR_QUBIT_OP_MAP, FIVE_QUBIT_OP_MAP
from pyqasm.expressions import Qasm3ExprEvaluator
import matplotlib as mpl
from matplotlib import pyplot as plt
import openqasm3.ast as ast

def draw(module: QasmModule, output="mpl"):
    if isinstance(module, Qasm2Module):
        module: Qasm3Module = module.to_qasm3()
    if output == "mpl":
        _draw_mpl(module)
    else:
        raise NotImplementedError(f"{output} drawing for Qasm3Module is unsupported")

def _draw_mpl(module: Qasm3Module) -> plt.Figure:
    module.unroll()
    module.remove_includes()
    module.remove_barriers()
    module.remove_measurements()

    n_lines = module._num_qubits + module._num_clbits
    statements = module._statements
    
    fig, ax = plt.subplots(figsize=(10, n_lines * 0.7))
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
            qubits = [(q.name.name,Qasm3ExprEvaluator.evaluate_expression(q.indices[0][0])[0]) for q in statement.qubits]
            draw_depth = 1 + max([depths[q] for q in qubits])
            for q in qubits: 
                depths[q] = draw_depth
            _draw_mpl_gate(statement, ax, [line_nums[q] for q in qubits], draw_depth)
        elif isinstance(statement, ast.QuantumMeasurement):
            pass
        else:
            raise NotImplementedError(f"Unsupported statement: {statement}")
    
    # Configure plot
    ax.set_ylim(-0.5, n_lines - 0.5)
    ax.set_xlim(-1, len(statements))
    ax.axis('off')
    ax.set_title('Quantum Circuit')
    
    plt.tight_layout()
    return fig

def _draw_mpl_bit(bit: tuple[str, int], ax: plt.Axes, line_num: int, max_depth: int):
    ax.hlines(y=line_num, xmin=0, xmax=max_depth, color='gray', linestyle='-')
    ax.text(-0.5, line_num, f'{bit[0]}[{bit[1]}]', ha='right', va='center')

def _draw_mpl_qubit(qubit: tuple[str, int], ax: plt.Axes, line_num: int, max_depth: int):
    ax.hlines(y=line_num, xmin=0, xmax=max_depth, color='black', linestyle='-')
    ax.text(-0.5, line_num, f'{qubit[0]}[{qubit[1]}]', ha='right', va='center')

def _draw_mpl_gate(gate: ast.QuantumGate, ax: plt.Axes, lines: list[int], depth: int):
    print("DRAW", gate.name.name, lines, depth)
    if gate.name.name in ONE_QUBIT_OP_MAP:
        ax.text(depth, lines[0], gate.name.name, ha='center', va='center',
        bbox=dict(facecolor='white', edgecolor='black'))
    elif gate.name.name in TWO_QUBIT_OP_MAP:
        pass
        # q1_idx = module.qubits.index(qubits[0])
        # q2_idx = module.qubits.index(qubits[1])
        # min_idx = min(q1_idx, q2_idx)
        # max_idx = max(q1_idx, q2_idx)
        
        # # Draw vertical connection
        # ax.vlines(x=i, ymin=min_idx, ymax=max_idx, color='black')
        # # Draw gate symbol
        # ax.text(i, (min_idx + max_idx)/2, gate_name, ha='center', va='center',
        #     bbox=dict(facecolor='white', edgecolor='black'))
    else:
        pass
    