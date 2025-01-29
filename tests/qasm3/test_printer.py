# Copyright (C) 2025 qBraid#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

import random

import pytest
from qbraid import random_circuit, transpile

from pyqasm.entrypoint import loads


def _check_fig(circ, fig):
    ax = fig.gca()
    # plt.savefig("test.png")
    assert len(ax.texts) > 0
    # assert False


def test_simple():
    qasm = """OPENQASM 3.0;
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
    fig = circ.draw()
    _check_fig(circ, fig)


def test_custom_gate():
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit q;
    gate custom a {
        h a;
        z a;
    }
    custom q;
    """
    circ = loads(qasm)
    fig = circ.draw()
    _check_fig(circ, fig)


@pytest.mark.parametrize("_", range(100))
def test_random(_):
    circ = random_circuit("qiskit", measure=random.choice([True, False]))
    qasm_str = transpile(circ, random.choice(["qasm2", "qasm3"]))
    module = loads(qasm_str)
    fig = module.draw()
    _check_fig(circ, fig)