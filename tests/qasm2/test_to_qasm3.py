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
Module containing unit tests for conversion to qasm3.

"""
import pytest

from pyqasm.entrypoint import loads
from pyqasm.modules.qasm3 import Qasm3Module
from tests.utils import check_unrolled_qasm

QASM_TEST_DATA = [
    (
        """
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1] ;
qreg qubits  [10]   ;
creg c[1];
creg bits   [12]   ;
        """,
        """
OPENQASM 3.0;
include "stdgates.inc";
qubit[1] q;
qubit[10] qubits;
bit[1] c;
bit[12] bits;
        """,
    ),
    (
        """
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
measure q->c;
measure q[0] -> c[1];
        """,
        """
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
c = measure q;
c[1] = measure q[0];
        """,
    ),
    (
        """
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
        """,
        """
OPENQASM 3.0;
include "stdgates.inc";
qubit[1] q;
        """,
    ),
    (
        """
OPENQASM 2.0;
include "qelib1.inc";
qreg q[5];
u(1,2,3) q[0];
sxdg q[0];
csx q[0], q[1];
cu1(0.5) q[0], q[1];
cu3(1,2,3) q[0], q[1];
rzz(0.5) q[0], q[1];
rccx q[0], q[1], q[2];
rc3x q[0], q[1], q[2], q[3];
c3x q[0], q[1], q[2], q[3];
c3sqrtx q[0], q[1], q[2], q[3];
c4x q[0], q[1], q[2], q[3], q[4];
        """,
        """
OPENQASM 3.0;   
include "stdgates.inc";
qubit[5] q;
u(1, 2, 3) q[0];
sxdg q[0];
csx q[0], q[1];
cu1(0.5) q[0], q[1];
cu3(1, 2, 3) q[0], q[1];
rzz(0.5) q[0], q[1];
rccx q[0], q[1], q[2];
rc3x q[0], q[1], q[2], q[3];
c3x q[0], q[1], q[2], q[3];
c3sqrtx q[0], q[1], q[2], q[3];
c4x q[0], q[1], q[2], q[3], q[4];
        """,
    ),
]


@pytest.mark.parametrize("test_input, expected_qasm3", QASM_TEST_DATA)
def test_to_qasm3_str(test_input, expected_qasm3):
    result = loads(test_input)
    returned_qasm3 = result.to_qasm3(as_str=True)
    assert isinstance(returned_qasm3, str)
    check_unrolled_qasm(returned_qasm3, expected_qasm3)


def test_to_qasm3_module():
    qasm2_string = """
    OPENQASM 2.0;
    include "stdgates.inc";
    qreg q[1];
    creg c[1];
    h q;
    measure q -> c;
    """
    result = loads(qasm2_string)

    qasm3_module = result.to_qasm3(as_str=False)
    assert isinstance(qasm3_module, Qasm3Module)
    qasm3_module.unroll()
    assert qasm3_module.num_qubits == 1
    assert qasm3_module.num_clbits == 1
    assert qasm3_module.depth() == 2
