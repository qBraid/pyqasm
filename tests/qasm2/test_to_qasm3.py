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

from pyqasm.entrypoint import load
from pyqasm.modules.qasm3 import Qasm3Module
from tests.utils import check_unrolled_qasm


def test_to_qasm3_str():
    qasm2_string = """
    OPENQASM 2.0;
    include "stdgates.inc";
    qreg q[1];
    creg c[1];
    h q;
    measure q -> c;
    """
    result = load(qasm2_string)

    expected_qasm3 = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    bit[1] c;
    h q;
    c = measure q;
    """

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
    result = load(qasm2_string)

    qasm3_module = result.to_qasm3(as_str=False)
    assert isinstance(qasm3_module, Qasm3Module)
    qasm3_module.unroll()
    assert qasm3_module.num_qubits == 1
    assert qasm3_module.num_clbits == 1
    assert qasm3_module.depth() == 2
