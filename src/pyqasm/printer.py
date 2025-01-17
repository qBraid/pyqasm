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

import openqasm3.ast as ast

from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.maps import (
    FIVE_QUBIT_OP_MAP,
    FOUR_QUBIT_OP_MAP,
    ONE_QUBIT_OP_MAP,
    ONE_QUBIT_ROTATION_MAP,
    REV_CTRL_GATE_MAP,
    THREE_QUBIT_OP_MAP,
    TWO_QUBIT_OP_MAP,
)

try:
    from matplotlib import pyplot as plt
    mpl_installed = True
except ImportError as e:
    mpl_installed = False

if TYPE_CHECKING:
    from pyqasm.modules.base import Qasm3Module
    


DEFAULT_GATE_COLOR = "#d4b6e8"
HADAMARD_GATE_COLOR = "#f0a6a6"

GATE_BOX_WIDTH, GATE_BOX_HEIGHT = 0.6, 0.6
GATE_SPACING = 0.2
LINE_SPACING = 0.6
TEXT_MARGIN = 0.6
FRAME_PADDING = 0.2


def draw(module: Qasm3Module, output="mpl", **kwargs):
    if not mpl_installed:
        raise ImportError("matplotlib needs to be installed prior to running pyqasm.draw(). You can install matplotlib with:\n'pip install pyqasm[visualization]'")

    if output == "mpl":
        plt.ioff()
        plt.close('all')
        return _draw_mpl(module, **kwargs)
    else:
        raise NotImplementedError(f"{output} drawing for Qasm3Module is unsupported")


def _draw_mpl(module: Qasm3Module, **kwargs) -> plt.Figure:
    module.unroll()
    module.remove_includes()
    
    idle_wires = kwargs.get("idle_wires", True)

    statements = module._statements

    # compute line numbers per qubit + max depth
    line_nums = dict()
    sizes = dict()
    line_num = -1
    max_depth = 0

    # classical registers are condensed into a single line
    for k in module._classical_registers.keys():
        line_num += 1
        line_nums[(k, -1)] = line_num
        sizes[(k, -1)] = module._classical_registers[k]

    for qubit_reg in module._qubit_registers.keys():
        size = module._qubit_registers[qubit_reg]
        line_num += size
        for i in range(size):
            line_nums[(qubit_reg, i)] = line_num
            depth = module._qubit_depths[(qubit_reg, i)]._total_ops()
            max_depth = max(max_depth, depth)
            line_num -= 1
        line_num += size

    # compute moments
    depths = dict()
    for k in line_nums.keys():
        depths[k] = -1

    moments = []
    for statement in statements:
        if "Declaration" in str(type(statement)):
            continue
        if isinstance(statement, ast.QuantumGate):
            qubits = [_identifier_to_key(q) for q in statement.qubits]
            depth = 1 + max([depths[q] for q in qubits])
            for q in qubits:
                depths[q] = depth
        elif isinstance(statement, ast.QuantumMeasurementStatement):
            qubit_key = _identifier_to_key(statement.measure.qubit)
            target_key = _identifier_to_key(statement.target)[0], -1
            depth = 1 + max(depths[qubit_key], depths[target_key])
            for k in [qubit_key, target_key]:
                depths[k] = depth
        elif isinstance(statement, ast.QuantumBarrier):
            qubits = [_identifier_to_key(q) for q in statement.qubits]
            depth = 1 + max([depths[q] for q in qubits])
            for q in qubits:
                depths[q] = depth
        elif isinstance(statement, ast.QuantumReset):
            pass
        else:
            raise NotImplementedError(f"Unsupported statement: {statement}")

        if depth >= len(moments):
            moments.append([])
        moments[depth].append(statement)

    width = 0
    for moment in moments:
        width += _mpl_get_moment_width(moment)
    width += TEXT_MARGIN

    if not idle_wires:
        # remove all lines that are not used            
        line_nums = {k: v for k, v in line_nums.items() if depths[k] >= 0}
        for i, k in enumerate(line_nums.keys()):
            line_nums[k] = i
    
    n_lines = max(line_nums.values()) + 1

    fig, ax = plt.subplots(
        figsize=(width, n_lines * GATE_BOX_HEIGHT + LINE_SPACING * (n_lines - 1))
    )
    ax.set_ylim(
        -GATE_BOX_HEIGHT / 2 - FRAME_PADDING / 2,
        n_lines * GATE_BOX_HEIGHT
        + LINE_SPACING * (n_lines - 1)
        - GATE_BOX_HEIGHT / 2
        + FRAME_PADDING / 2,
    )
    ax.set_xlim(-FRAME_PADDING / 2, width)
    ax.axis("off")
    # ax.set_aspect('equal')
    # plt.tight_layout()

    x = 0
    for k in module._qubit_registers.keys():
        for i in range(module._qubit_registers[k]):
            if (k, i) in line_nums:
                line_num = line_nums[(k, i)]
                _mpl_draw_qubit_label((k, i), line_num, ax, x)

    for k in module._classical_registers.keys():
        _mpl_draw_creg_label(k, module._classical_registers[k], line_nums[(k, -1)], ax, x)

    x += TEXT_MARGIN
    x0 = x
    for i,moment in enumerate(moments):
        dx = _mpl_get_moment_width(moment)
        _mpl_draw_lines(dx, line_nums, sizes, ax, x, start=i==0)
        x += dx
    x = x0
    for moment in moments:
        dx = _mpl_get_moment_width(moment)
        for statement in moment:
            _mpl_draw_statement(statement, line_nums, ax, x)
        x += dx

    return fig


def _identifier_to_key(identifier: ast.Identifier | ast.IndexedIdentifier) -> tuple[str, int]:
    if isinstance(identifier, ast.Identifier):
        return identifier.name, -1
    else:
        return (
            identifier.name.name,
            Qasm3ExprEvaluator.evaluate_expression(identifier.indices[0][0])[0],
        )


def _mpl_line_to_y(line_num: int) -> float:
    return line_num * (GATE_BOX_HEIGHT + LINE_SPACING)

def _mpl_draw_qubit_label(qubit: tuple[str, int], line_num: int, ax: plt.Axes, x: float):
    ax.text(x, _mpl_line_to_y(line_num), f"{qubit[0]}[{qubit[1]}]", ha="right", va="center")

def _mpl_draw_creg_label(creg: str, size: int, line_num: int, ax: plt.Axes, x: float):
    ax.text(x, _mpl_line_to_y(line_num), f"{creg[0]}", ha="right", va="center")

def _mpl_draw_lines(width, line_nums: dict[tuple[str, int], int], sizes: dict[tuple[str, int], int], ax: plt.Axes, x: float, start=True):
    for k in line_nums.keys():
        y = _mpl_line_to_y(line_nums[k])
        if k[1] == -1:
            gap = GATE_BOX_HEIGHT/15
            ax.hlines(
                xmin=x - width / 2, xmax=x + width / 2, y=y+gap/2, color="black", linestyle="-", zorder=-10
            )
            ax.hlines(
                xmin=x - width / 2, xmax=x + width / 2, y=y-gap/2, color="black", linestyle="-", zorder=-10
            )
            if start:
                ax.plot([x - width/2 + gap, x - width/2 + 2*gap], [y-2*gap, y+2*gap], color="black", zorder=-10)
                ax.text(x - width/2 + 3*gap, y+3*gap, f"{sizes[k]}", fontsize=8)
        else:
            ax.hlines(
                xmin=x - width / 2, xmax=x + width / 2, y=y, color="black", linestyle="-", zorder=-10
            )


def _mpl_get_moment_width(moment: list[ast.QuantumStatement]) -> float:
    return max([_mpl_get_statement_width(s) for s in moment])


def _mpl_get_statement_width(statement: ast.QuantumStatement) -> float:
    return GATE_BOX_WIDTH + GATE_SPACING


def _mpl_draw_statement(
    statement: ast.QuantumStatement, line_nums: dict[tuple[str, int], int], ax: plt.Axes, x: float
):
    if isinstance(statement, ast.QuantumGate):
        args = [Qasm3ExprEvaluator.evaluate_expression(arg)[0] for arg in statement.arguments]
        lines = [line_nums[_identifier_to_key(q)] for q in statement.qubits]
        _mpl_draw_gate(statement, args, lines, ax, x)
    elif isinstance(statement, ast.QuantumMeasurementStatement):
        qubit_key = _identifier_to_key(statement.measure.qubit)
        target_key = _identifier_to_key(statement.target)
        _mpl_draw_measurement(line_nums[qubit_key], line_nums[(target_key[0], -1)], target_key[1], ax, x)
    elif isinstance(statement, ast.QuantumBarrier):
        lines = [line_nums[_identifier_to_key(q)] for q in statement.qubits]
        _mpl_draw_barrier(lines, ax, x)
    else:
        raise NotImplementedError(f"Unsupported statement: {statement}")


def _mpl_draw_gate(
    gate: ast.QuantumGate, args: list[Any], lines: list[int], ax: plt.Axes, x: float
):
    name = gate.name.name
    if name in REV_CTRL_GATE_MAP:
        i = 0
        while name in REV_CTRL_GATE_MAP:
            name = REV_CTRL_GATE_MAP[name]
            _draw_mpl_control(lines[i], lines[-1], ax, x)
            i += 1
        lines = lines[i:]
        gate.name.name = name

    if name in ONE_QUBIT_OP_MAP or name in ONE_QUBIT_ROTATION_MAP:
        _draw_mpl_one_qubit_gate(gate, args, lines[0], ax, x)
    elif name in TWO_QUBIT_OP_MAP:
        if name == "swap":
            _draw_mpl_swap(lines[0], lines[1], ax, x)
        else:
            raise NotImplementedError(f"Unsupported gate: {name}")
    else:
        raise NotImplementedError(f"Unsupported gate: {name}")


# TODO: switch to moment based system. go progressively, calculating required width for each moment, center the rest. this makes position calculations not to bad. if we overflow, start a new figure.


def _draw_mpl_one_qubit_gate(
    gate: ast.QuantumGate, args: list[Any], line: int, ax: plt.Axes, x: float
):
    color = DEFAULT_GATE_COLOR
    if gate.name.name == "h":
        color = HADAMARD_GATE_COLOR
    text = gate.name.name.upper()
    

    y = _mpl_line_to_y(line)
    rect = plt.Rectangle(
        (x - GATE_BOX_WIDTH / 2, y - GATE_BOX_HEIGHT / 2),
        GATE_BOX_WIDTH,
        GATE_BOX_HEIGHT,
        facecolor=color,
        edgecolor="none",
    )
    ax.add_patch(rect)
    
    if len(args) > 0:
        args_text = f"{', '.join([f'{a:.3f}' if isinstance(a, float) else str(a) for a in args])}"
        ax.text(x, y + GATE_BOX_HEIGHT/8, text, ha="center", va="center", fontsize=12)
        ax.text(x, y - GATE_BOX_HEIGHT/4, args_text, ha="center", va="center", fontsize=8)
    else:
        ax.text(x, y, text, ha="center", va="center", fontsize=12)


def _draw_mpl_control(ctrl_line: int, target_line: int, ax: plt.Axes, x: float):
    y1 = _mpl_line_to_y(ctrl_line)
    y2 = _mpl_line_to_y(target_line)
    ax.vlines(x=x, ymin=min(y1, y2), ymax=max(y1, y2), color="black", linestyle="-", zorder=-1)
    ax.plot(x, y1, "ko", markersize=8, markerfacecolor="black")


def _draw_mpl_swap(line1: int, line2: int, ax: plt.Axes, x: float):
    y1 = _mpl_line_to_y(line1)
    y2 = _mpl_line_to_y(line2)
    ax.vlines(x=x, ymin=min(y1, y2), ymax=max(y1, y2), color="black", linestyle="-")
    ax.plot(x, y1, "x", markersize=8, color="black")
    ax.plot(x, y2, "x", markersize=8, color="black")


def _mpl_draw_measurement(qbit_line: int, cbit_line: int, idx: int, ax: plt.Axes, x: float):
    y1 = _mpl_line_to_y(qbit_line)
    y2 = _mpl_line_to_y(cbit_line)
    
    color = "#A0A0A0"
    gap = GATE_BOX_WIDTH/3
    rect = plt.Rectangle(
        (x - GATE_BOX_WIDTH / 2, y1 - GATE_BOX_HEIGHT / 2),
        GATE_BOX_WIDTH,
        GATE_BOX_HEIGHT,
        facecolor=color,
        edgecolor="none",
    )
    ax.add_patch(rect)
    ax.text(x, y1, "M", ha="center", va="center")
    ax.vlines(
        x=x - gap/10, ymin=min(y1, y2)+gap, ymax=max(y1, y2), color=color, linestyle="-", zorder=-1
    )
    ax.vlines(
        x=x + gap/10, ymin=min(y1, y2)+gap, ymax=max(y1, y2), color=color, linestyle="-", zorder=-1
    )
    ax.plot(x, y2 + gap, "v", markersize=12, color=color)
    ax.text(x + gap, y2 + gap, str(idx), color=color, ha="left", va="bottom", fontsize=8)


def _mpl_draw_barrier(lines: list[int], ax: plt.Axes, x: float):
    for line in lines:
        y = _mpl_line_to_y(line)
        ax.vlines(x=x, ymin=y - GATE_BOX_HEIGHT/2 - LINE_SPACING/2, ymax=y + GATE_BOX_HEIGHT/2 + LINE_SPACING/2, color="black", linestyle="--")
        rect = plt.Rectangle(
            (x - GATE_BOX_WIDTH / 4, y - GATE_BOX_HEIGHT / 2 - LINE_SPACING/2),
            GATE_BOX_WIDTH / 2,
            GATE_BOX_HEIGHT + LINE_SPACING,
            facecolor="lightgray",
            edgecolor="none",
            alpha=0.5,
            zorder=-1
        )
        ax.add_patch(rect)
