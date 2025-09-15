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

# pylint: disable=import-outside-toplevel

"""
Functions for drawing quantum circuits.

"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from openqasm3 import ast

from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.maps.gates import (
    ONE_QUBIT_OP_MAP,
    ONE_QUBIT_ROTATION_MAP,
    REV_CTRL_GATE_MAP,
    TWO_QUBIT_OP_MAP,
)

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

    from pyqasm.modules.base import QasmModule


# Constants
DEFAULT_GATE_COLOR = "#d4b6e8"
HADAMARD_GATE_COLOR = "#f0a6a6"

FIG_MAX_WIDTH = 12
GATE_BOX_WIDTH = 0.6
GATE_BOX_HEIGHT = 0.6
GATE_SPACING = 0.2
LINE_SPACING = 0.6
TEXT_MARGIN = 0.6
FRAME_PADDING = 0.2
BOX_STYLE = "round,pad=0.02,rounding_size=0.05"

Declaration = (
    ast.CalibrationGrammarDeclaration
    | ast.ClassicalDeclaration
    | ast.ConstantDeclaration
    | ast.ExternDeclaration
    | ast.IODeclaration
    | ast.QubitDeclaration
)
QuantumStatement = (
    ast.QuantumGate | ast.QuantumMeasurementStatement | ast.QuantumBarrier | ast.QuantumReset
)

QubitIdentifier = ast.Identifier | ast.IndexedIdentifier


def draw(
    program: str | QasmModule,
    output: Literal["mpl"] = "mpl",
    idle_wires: bool = True,
    **kwargs: Any,
) -> None:
    """Draw the quantum circuit.

    Args:
        module (QasmModule): The quantum module to draw
        output (str): The output format. Defaults to "mpl".
        idle_wires (bool): Whether to show idle wires. Defaults to True.

    Returns:
        None: The drawing is displayed or saved to a file.
    """
    if isinstance(program, str):
        from pyqasm.entrypoint import loads

        program = loads(program)

    if output == "mpl":
        _ = mpl_draw(program, idle_wires=idle_wires, external_draw=False, **kwargs)

        import matplotlib.pyplot as plt

        if not plt.isinteractive():
            plt.show()
    else:
        raise ValueError(f"Unsupported output format: {output}")


def mpl_draw(  # pylint: disable=too-many-locals
    program: str | QasmModule,
    idle_wires: bool = True,
    filename: str | Path | None = None,
    external_draw: bool = True,
) -> plt.Figure:
    """Internal matplotlib drawing implementation."""
    if isinstance(program, str):
        from pyqasm.entrypoint import loads

        program = loads(program)

    try:
        # pylint: disable-next=unused-import
        import matplotlib.pyplot as plt

        plt.ioff()
    except ImportError as e:
        raise ImportError(
            "matplotlib needs to be installed prior to running pyqasm.mpl_draw(). "
            "You can install matplotlib with:\n'pip install matplotlib'"
        ) from e

    program.unroll()
    program.remove_includes()

    line_nums, sizes = _compute_line_nums(program)

    global_phase = 0
    statements: list[ast.Statement | ast.Pragma] = []

    for s in program._statements:
        if isinstance(s, ast.QuantumPhase):
            global_phase += Qasm3ExprEvaluator.evaluate_expression(s.argument)[0]
        else:
            statements.append(s)

    # Compute moments
    moments, depths = _compute_moments(statements, line_nums)

    if not idle_wires:
        # remove all lines that are not used
        ks = sorted(line_nums.keys(), key=lambda k: line_nums[k])
        ks = [k for k in ks if depths[k] > 0]
        line_nums = {k: i for i, k in enumerate(ks)}

    fig = _mpl_draw(program, moments, line_nums, sizes, global_phase)

    if filename is not None:
        plt.savefig(filename, bbox_inches="tight", dpi=300)

    if external_draw:
        plt.close(fig)

    return fig


def _compute_line_nums(
    module: QasmModule,
) -> tuple[dict[tuple[str, int], int], dict[tuple[str, int], int]]:
    """Compute line number and register size lookup table for the circuit."""
    line_nums = {}
    sizes = {}
    line_num = -1
    max_depth = 0

    # Classical registers condensed to single line
    for k in module._classical_registers:
        line_num += 1
        line_nums[(k, -1)] = line_num
        sizes[(k, -1)] = module._classical_registers[k]

    # Calculate qubit lines and depths
    for qubit_reg in module._qubit_registers:
        size = module._qubit_registers[qubit_reg]
        line_num += size
        for i in range(size):
            line_nums[(qubit_reg, i)] = line_num
            depth = module._qubit_depths[(qubit_reg, i)]._total_ops()
            max_depth = max(max_depth, depth)
            line_num -= 1
        line_num += size

    return line_nums, sizes


def _get_line_keys(
    all_keys: list[tuple[str, int]], line_nums: dict[tuple[str, int], int]
) -> list[tuple[str, int]]:
    if not all_keys:
        return []

    # Get line numbers for the given keys and find min/max
    key_line_nums = [line_nums[key] for key in all_keys]
    start_key, end_key = min(key_line_nums), max(key_line_nums)

    # Return all keys within the range
    return [key for key, line_num in line_nums.items() if start_key <= line_num <= end_key]


# pylint: disable-next=too-many-branches,too-many-locals
def _compute_moments(
    statements: list[ast.Statement | ast.Pragma], line_nums: dict[tuple[str, int], int]
) -> tuple[list[list[QuantumStatement]], dict[tuple[str, int], int]]:
    depths = {}
    for k in line_nums:
        depths[k] = -1

    moments: list[list[QuantumStatement]] = []
    # Find and remove final measurements (measurements at the end of the statements list)
    final_measurements: list[ast.QuantumMeasurementStatement] = []
    seen_keys = set[tuple[str, int]]()

    for stmt in reversed(statements):
        if not isinstance(stmt, ast.QuantumMeasurementStatement):
            break
        control_key = _identifier_to_key(stmt.measure.qubit)
        if control_key not in seen_keys:
            seen_keys.add(control_key)
            final_measurements.append(stmt)

    # Remove the final measurements from the end of statements list
    statements = statements[: -len(final_measurements)] if final_measurements else statements

    for statement in statements:
        if isinstance(statement, Declaration):
            continue
        if not isinstance(statement, QuantumStatement):
            raise ValueError(f"Unsupported statement: {statement}")
        if isinstance(statement, ast.QuantumGate):
            qubits = [_identifier_to_key(q) for q in statement.qubits]
            # Get line keys for multi-qubit gates, otherwise use qubits directly
            target_keys = _get_line_keys(qubits, line_nums) if len(qubits) > 1 else qubits
            # Calculate new depth and update all affected keys
            depth = 1 + max(depths[key] for key in target_keys)
            for key in target_keys:
                depths[key] = depth
        elif isinstance(statement, ast.QuantumMeasurementStatement):
            keys = [_identifier_to_key(statement.measure.qubit)]
            if statement.target:
                target_key = _identifier_to_key(statement.target)[0], -1
                keys.append(target_key)
            line_keys = _get_line_keys(keys, line_nums)
            # Calculate new depth and update all affected keys
            depth = 1 + max(depths[key] for key in line_keys)
            for key in line_keys:
                depths[key] = depth
        elif isinstance(statement, ast.QuantumBarrier):
            qubits = []
            for expr in statement.qubits:
                # https://github.com/openqasm/openqasm/issues/461
                if not isinstance(expr, QubitIdentifier):
                    raise ValueError(
                        f"Unsupported qubit type '{type(expr).__name__}' in "
                        f"'{type(statement).__name__}' statement. "
                        f"Expected a qubit of type {QubitIdentifier}."
                    )
                qubits.append(_identifier_to_key(expr))
            depth = 1 + max(depths[q] for q in qubits)
            for q in qubits:
                depths[q] = depth
        elif isinstance(statement, ast.QuantumReset):
            qubit_key = _identifier_to_key(statement.qubits)
            depth = 1 + depths[qubit_key]
            depths[qubit_key] = depth

        if depth >= len(moments):
            moments.append([])

        moments[depth].append(statement)

    depth = max(depths.values())
    for measurement in final_measurements:
        depth += 1
        if depth >= len(moments):
            moments.append([])
        moments[depth].append(measurement)

    return moments, depths


def _identifier_to_key(identifier: ast.Identifier | ast.IndexedIdentifier) -> tuple[str, int]:
    if isinstance(identifier, ast.Identifier):
        return identifier.name, -1

    indices = identifier.indices
    if len(indices) >= 1 and isinstance(indices[0], list) and len(indices[0]) >= 1:
        return (
            identifier.name.name,
            Qasm3ExprEvaluator.evaluate_expression(indices[0][0])[0],
        )

    raise ValueError(f"Unsupported identifier: {identifier}")


def _compute_sections(
    moments: list[list[QuantumStatement]],
) -> tuple[list[list[list[QuantumStatement]]], float]:
    sections: list[list[list[QuantumStatement]]] = [[]]

    width = TEXT_MARGIN
    for moment in moments:
        w = _mpl_get_moment_width(moment)
        if width + w < FIG_MAX_WIDTH:
            width += w
        else:
            width = TEXT_MARGIN
            width = w
            sections.append([])
        sections[-1].append(moment)

    if len(sections) > 1:
        width = FIG_MAX_WIDTH

    return sections, width


def _mpl_draw(
    module: QasmModule,
    moments: list[list[QuantumStatement]],
    line_nums: dict[tuple[str, int], int],
    sizes: dict[tuple[str, int], int],
    global_phase: float,
):
    sections, width = _compute_sections(moments)
    n_lines = max(line_nums.values()) + 1
    fig, axs = _mpl_setup_figure(sections, width, n_lines)

    for sidx, ms in enumerate(sections):
        ax = axs[sidx]
        _mpl_draw_section(module, ms, line_nums, sizes, ax, global_phase)

    return fig


def _mpl_setup_figure(
    sections: list[list[list[QuantumStatement]]], width: float, n_lines: int
) -> tuple[plt.Figure, list[plt.Axes]]:
    import matplotlib.pyplot as plt
    import numpy as np

    fig_ax_tuple: tuple[plt.Figure, list[plt.Axes] | plt.Axes] = plt.subplots(
        len(sections),
        1,
        sharex=True,
        figsize=(width, len(sections) * (n_lines * GATE_BOX_HEIGHT + LINE_SPACING * (n_lines - 1))),
    )

    fig, axs = fig_ax_tuple
    axs = (
        axs.flatten().tolist()
        if isinstance(axs, np.ndarray)
        else [axs] if isinstance(axs, plt.Axes) else axs
    )

    for ax in axs:
        ax.set_ylim(
            -GATE_BOX_HEIGHT / 2 - FRAME_PADDING / 2,
            n_lines * GATE_BOX_HEIGHT
            + LINE_SPACING * (n_lines - 1)
            - GATE_BOX_HEIGHT / 2
            + FRAME_PADDING / 2,
        )
        ax.set_xlim(-FRAME_PADDING / 2, width)
        ax.axis("off")

    return fig, axs


# pylint: disable-next=too-many-arguments
def _mpl_draw_section(
    module: QasmModule,
    moments: list[list[QuantumStatement]],
    line_nums: dict[tuple[str, int], int],
    sizes: dict[tuple[str, int], int],
    ax: plt.Axes,
    global_phase: float,
):
    x = 0.0
    if global_phase != 0:
        _mpl_draw_global_phase(global_phase, ax, x)
    for k in module._qubit_registers.keys():
        for i in range(module._qubit_registers[k]):
            if (k, i) in line_nums:
                line_num = line_nums[(k, i)]
                _mpl_draw_qubit_label((k, i), line_num, ax, x)

    for k in module._classical_registers.keys():
        _mpl_draw_creg_label(k, line_nums[(k, -1)], ax, x)

    x += TEXT_MARGIN
    x0 = x
    for i, moment in enumerate(moments):
        dx = _mpl_get_moment_width(moment)
        _mpl_draw_lines(dx, line_nums, sizes, ax, x, start=i == 0)
        x += dx
    x = x0
    for moment in moments:
        dx = _mpl_get_moment_width(moment)
        for statement in moment:
            _mpl_draw_statement(statement, line_nums, ax, x)
        x += dx


def _mpl_line_to_y(line_num: int) -> float:
    return line_num * (GATE_BOX_HEIGHT + LINE_SPACING)


def _mpl_draw_global_phase(global_phase: float, ax: plt.Axes, x: float):
    ax.text(x, -0.75, f"Global Phase: {global_phase:.3f}", ha="left", va="center")


def _mpl_draw_qubit_label(qubit: tuple[str, int], line_num: int, ax: plt.Axes, x: float):
    ax.text(x, _mpl_line_to_y(line_num), f"{qubit[0]}[{qubit[1]}]", ha="right", va="center")


def _mpl_draw_creg_label(creg: str, line_num: int, ax: plt.Axes, x: float):
    ax.text(x, _mpl_line_to_y(line_num), f"{creg[0]}", ha="right", va="center")


# pylint: disable-next=too-many-arguments
def _mpl_draw_lines(
    width,
    line_nums: dict[tuple[str, int], int],
    sizes: dict[tuple[str, int], int],
    ax: plt.Axes,
    x: float,
    start=True,
):
    for k in line_nums.keys():
        y = _mpl_line_to_y(line_nums[k])
        if k[1] == -1:
            gap = GATE_BOX_HEIGHT / 15
            ax.hlines(
                xmin=x - width / 2,
                xmax=x + width / 2,
                y=y + gap / 2,
                color="black",
                linestyle="-",
                zorder=-10,
            )
            ax.hlines(
                xmin=x - width / 2,
                xmax=x + width / 2,
                y=y - gap / 2,
                color="black",
                linestyle="-",
                zorder=-10,
            )
            if start:
                ax.plot(
                    [x - width / 2 + gap, x - width / 2 + 2 * gap],
                    [y - 2 * gap, y + 2 * gap],
                    color="black",
                    zorder=-10,
                )
                ax.text(x - width / 2 + 3 * gap, y + 3 * gap, f"{sizes[k]}", fontsize=8)
        else:
            ax.hlines(
                xmin=x - width / 2,
                xmax=x + width / 2,
                y=y,
                color="black",
                linestyle="-",
                zorder=-10,
            )


def _mpl_get_moment_width(moment: list[QuantumStatement]) -> float:
    return max(_mpl_get_statement_width(s) for s in moment)


def _mpl_get_statement_width(_: QuantumStatement) -> float:
    return GATE_BOX_WIDTH + GATE_SPACING


def _mpl_draw_statement(
    statement: QuantumStatement, line_nums: dict[tuple[str, int], int], ax: plt.Axes, x: float
):
    if isinstance(statement, ast.QuantumGate):
        args = [Qasm3ExprEvaluator.evaluate_expression(arg)[0] for arg in statement.arguments]
        lines = [line_nums[_identifier_to_key(q)] for q in statement.qubits]
        _mpl_draw_gate(statement, args, lines, ax, x)
    elif isinstance(statement, ast.QuantumMeasurementStatement):
        qubit_key = _identifier_to_key(statement.measure.qubit)
        if statement.target is None:
            _mpl_draw_measurement(line_nums[qubit_key], -1, -1, ax, x)
            return
        name, idx = _identifier_to_key(statement.target)
        _mpl_draw_measurement(line_nums[qubit_key], line_nums[(name, -1)], idx, ax, x)
    elif isinstance(statement, ast.QuantumBarrier):
        lines = []
        for q in statement.qubits:
            # https://github.com/openqasm/openqasm/issues/461
            if not isinstance(q, QubitIdentifier):
                raise ValueError(
                    f"Unsupported qubit type '{type(q).__name__}' in "
                    f"'{type(statement).__name__}' statement. "
                    f"Expected a qubit of type {QubitIdentifier}."
                )
            lines.append(line_nums[_identifier_to_key(q)])

        _mpl_draw_barrier(lines, ax, x)
    elif isinstance(statement, ast.QuantumReset):
        _mpl_draw_reset(line_nums[_identifier_to_key(statement.qubits)], ax, x)
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


def _draw_mpl_one_qubit_gate(
    gate: ast.QuantumGate, args: list[Any], line: int, ax: plt.Axes, x: float
):
    from matplotlib.patches import FancyBboxPatch

    color = DEFAULT_GATE_COLOR
    if gate.name.name == "h":
        color = HADAMARD_GATE_COLOR
    text = gate.name.name.upper()

    y = _mpl_line_to_y(line)

    rect = FancyBboxPatch(
        (x - GATE_BOX_WIDTH / 2, y - GATE_BOX_HEIGHT / 2),
        GATE_BOX_WIDTH,
        GATE_BOX_HEIGHT,
        facecolor=color,
        edgecolor="none",
        boxstyle=BOX_STYLE,
    )
    ax.add_patch(rect)

    if len(args) > 0:
        args_text = f"{', '.join([f'{a:.3f}' if isinstance(a, float) else str(a) for a in args])}"
        ax.text(x, y + GATE_BOX_HEIGHT / 8, text, ha="center", va="center", fontsize=12)
        ax.text(x, y - GATE_BOX_HEIGHT / 4, args_text, ha="center", va="center", fontsize=8)
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
    from matplotlib.patches import FancyBboxPatch

    y1 = _mpl_line_to_y(qbit_line)

    color = "#A0A0A0"
    gap = GATE_BOX_WIDTH / 3
    rect = FancyBboxPatch(
        (x - GATE_BOX_WIDTH / 2, y1 - GATE_BOX_HEIGHT / 2),
        GATE_BOX_WIDTH,
        GATE_BOX_HEIGHT,
        facecolor=color,
        edgecolor="none",
        boxstyle=BOX_STYLE,
    )
    ax.add_patch(rect)
    ax.text(x, y1, "M", ha="center", va="center")

    if cbit_line >= 0 and idx >= 0:
        y2 = _mpl_line_to_y(cbit_line)
        ax.vlines(
            x=x - gap / 10,
            ymin=min(y1, y2) + gap,
            ymax=max(y1, y2),
            color=color,
            linestyle="-",
            zorder=-1,
        )
        ax.vlines(
            x=x + gap / 10,
            ymin=min(y1, y2) + gap,
            ymax=max(y1, y2),
            color=color,
            linestyle="-",
            zorder=-1,
        )
        ax.plot(x, y2 + gap, "v", markersize=12, color=color)
        ax.text(x + gap, y2 + gap, str(idx), color=color, ha="left", va="bottom", fontsize=8)


def _mpl_draw_barrier(lines: list[int], ax: plt.Axes, x: float):
    import matplotlib.pyplot as plt

    for line in lines:
        y = _mpl_line_to_y(line)
        ax.vlines(
            x=x,
            ymin=y - GATE_BOX_HEIGHT / 2 - LINE_SPACING / 2,
            ymax=y + GATE_BOX_HEIGHT / 2 + LINE_SPACING / 2,
            color="black",
            linestyle="--",
        )
        rect = plt.Rectangle(
            (x - GATE_BOX_WIDTH / 4, y - GATE_BOX_HEIGHT / 2 - LINE_SPACING / 2),
            GATE_BOX_WIDTH / 2,
            GATE_BOX_HEIGHT + LINE_SPACING,
            facecolor="lightgray",
            edgecolor="none",
            alpha=0.5,
            zorder=-1,
        )
        ax.add_patch(rect)


def _mpl_draw_reset(line: int, ax: plt.Axes, x: float):
    from matplotlib.patches import FancyBboxPatch

    y = _mpl_line_to_y(line)
    rect = FancyBboxPatch(
        (x - GATE_BOX_WIDTH / 2, y - GATE_BOX_HEIGHT / 2),
        GATE_BOX_WIDTH,
        GATE_BOX_HEIGHT,
        facecolor="lightgray",
        edgecolor="none",
        boxstyle=BOX_STYLE,
    )
    ax.add_patch(rect)
    ax.text(x, y, "∣0⟩", ha="center", va="center", fontsize=12)
