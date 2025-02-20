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

from pathlib import Path

import pytest
from matplotlib.testing.compare import compare_images

from pyqasm import draw
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


def test_draw_bell():
    """Test drawing a simple Bell state circuit."""
    qasm3 = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[2] q;
    bit[2] b;
    h q;
    cnot q[0], q[1];
    b = measure q;
    """
    images_dir = Path(__file__).parent / "images"
    expected_img = images_dir / "bell.png"
    test_img = images_dir / "bell-test.png"
    diff_img = images_dir / "bell-failed-diff.png"

    try:
        draw(qasm3, output="mpl", filename=test_img)

        assert compare_images(str(test_img), str(expected_img), tol=0.001) is None
    finally:
        for img in [test_img, diff_img]:
            if img.exists():
                img.unlink()


def test_draw_misc_ops():
    """Test drawing a circuit with various operations."""
    qasm3 = """
    OPENQASM 3;
    include "stdgates.inc";
    qubit[3] q;
    h q;
    ccnot q[0], q[1], q[2];
    rz(2*pi) q[0];
    ry(pi/4) q[1];
    rx(pi) q[2];
    swap q[0], q[2];
    swap q[1], q[2];
    id q[0];
    barrier q;
    measure q;
    reset q;
    """
    images_dir = Path(__file__).parent / "images"
    expected_img = images_dir / "misc.png"
    test_img = images_dir / "misc-test.png"
    diff_img = images_dir / "misc-failed-diff.png"

    try:
        draw(qasm3, output="mpl", filename=test_img)

        assert compare_images(str(test_img), str(expected_img), tol=0.001) is None
    finally:
        for img in [test_img, diff_img]:
            if img.exists():
                img.unlink()
