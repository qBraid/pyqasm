# Copyright (C) 2025 qBraid
#
# This file is part of PyQASM
#
# PyQASM is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for PyQASM, as per Section 15 of the GPL v3.

"""
Tests for the QASM printer module.
"""

import pytest

from pyqasm.entrypoint import loads
from pyqasm.printer import mpl_draw

pytest.importorskip("matplotlib", reason="Matplotlib not installed.")


def _check_fig(_, fig):
    """Verify the matplotlib figure contains expected elements.

    Args:
        fig: a matplotlib figure
    """
    ax = fig.gca()
    assert len(ax.texts) > 0


def test_draw_qasm3_simple():
    """Test drawing a simple QASM 3.0 circuit."""
    qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[3] q;
    bit[3] b;

    h q[0];
    z q[1];
    rz(pi/1.1) q[0];
    cx q[0], q[1];
    swap q[0], q[1];
    ccx q[0], q[1], q[2];
    b = measure q;
    """
    circ = loads(qasm)
    fig = mpl_draw(circ)
    _check_fig(circ, fig)


def test_draw_qasm3_custom_gate():
    qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit q;

    gate custom a {
        h a;
        z a;
    }
    custom q;
    """
    circ = loads(qasm)
    fig = mpl_draw(circ)
    _check_fig(circ, fig)


def test_draw_qasm2_simple():
    """Test drawing a simple QASM 2.0 circuit."""
    qasm = """
    OPENQASM 2.0;
    include "qelib1.inc";

    qreg q[4];
    creg c[4];

    h q[0];
    cx q[0], q[1];
    x q[2];
    rz(pi/4) q[3];
    cx q[1], q[2];
    ccx q[0], q[1], q[3];
    u3(pi/2, pi/4, pi/8) q[2];
    barrier q;
    measure q -> c;
    """
    circ = loads(qasm)
    fig = mpl_draw(circ)
    _check_fig(circ, fig)
