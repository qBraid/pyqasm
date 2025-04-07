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

"""
Tests for the QASM printer module.
"""

import os
import unittest.mock

import pytest

from pyqasm.entrypoint import loads
from pyqasm.printer import draw, mpl_draw

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


@pytest.mark.mpl_image_compare(baseline_dir="images", filename="bell.png")
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
    fig = mpl_draw(qasm3)
    return fig


@pytest.mark.mpl_image_compare(baseline_dir="images", filename="misc.png")
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
    fig = mpl_draw(qasm3)
    return fig


def test_draw_raises_unsupported_format_error():
    """Test that an error is raised for unsupported formats."""
    qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    h q;
    cnot q[0], q[1];
    measure q;
    """
    circ = loads(qasm)

    with pytest.raises(ValueError, match=r"Unsupported output format"):
        draw(circ, output="unsupported_format")


def test_saved_figure():
    """Test that the saved figure is not None."""
    qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    h q;
    cnot q[0], q[1];
    measure q;
    """

    circ = loads(qasm)
    fig = mpl_draw(circ, filename="test_img.png")
    assert fig is not None

    # check the file exists
    assert os.path.exists("test_img.png")

    # clean up the file
    os.remove("test_img.png")


@pytest.mark.parametrize("is_interactive", [True, False])
def test_matplotlib_interactive_behavior(is_interactive):
    """Test plt.show() behavior depending on matplotlib's interactive mode."""
    qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    h q;
    cnot q[0], q[1];
    measure q;
    """

    with unittest.mock.patch(
        "matplotlib.pyplot.isinteractive", return_value=is_interactive
    ) as mock_isinteractive:
        with unittest.mock.patch("matplotlib.pyplot.show") as mock_show:
            # Call draw function
            draw(qasm, output="mpl")

            # Verify isinteractive was called
            mock_isinteractive.assert_called()

            # When not interactive, show should be called; otherwise it shouldn't
            if is_interactive:
                mock_show.assert_not_called()
            else:
                mock_show.assert_called_once()
