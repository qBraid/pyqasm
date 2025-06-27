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
Module containing unit tests for the qubit register consolidation.

"""

import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


def test_reset():
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qreg q2[3];
    reset q2;
    reset q[1];
    """
    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[5] __PYQASM_QUBITS__;
    reset __PYQASM_QUBITS__[2];
    reset __PYQASM_QUBITS__[3];
    reset __PYQASM_QUBITS__[4];
    reset __PYQASM_QUBITS__[1];
    """

    result = loads(qasm)
    result.unroll(device_qubits=5)
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_barrier():
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qreg q2[3];
    barrier q2;
    barrier q[1];
    """
    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[5] __PYQASM_QUBITS__;
    barrier __PYQASM_QUBITS__[2];
    barrier __PYQASM_QUBITS__[3];
    barrier __PYQASM_QUBITS__[4];
    barrier __PYQASM_QUBITS__[1];
    """
    result = loads(qasm)
    result.unroll(device_qubits=5)
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_unrolled_barrier():
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qreg q2[3];
    barrier q[0];
    barrier q2;
    barrier q;
    """
    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[5] __PYQASM_QUBITS__;
    barrier __PYQASM_QUBITS__[0];
    barrier __PYQASM_QUBITS__[2:];
    barrier __PYQASM_QUBITS__[:2];
    """
    result = loads(qasm)
    result.unroll(unroll_barriers=False, device_qubits=5)
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_measurement():
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    qreg q2[3];
    bit[3] c;
    measure q2 -> c;
    c[0] = measure q[0];
    c = measure q[:3];
    c = measure q2;
    measure q2[1] -> c[2];
    """
    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[7] __PYQASM_QUBITS__;
    bit[3] c;
    c[0] = measure __PYQASM_QUBITS__[4];
    c[1] = measure __PYQASM_QUBITS__[5];
    c[2] = measure __PYQASM_QUBITS__[6];
    c[0] = measure __PYQASM_QUBITS__[0];
    c[0] = measure __PYQASM_QUBITS__[0];
    c[1] = measure __PYQASM_QUBITS__[1];
    c[2] = measure __PYQASM_QUBITS__[2];
    c[0] = measure __PYQASM_QUBITS__[4];
    c[1] = measure __PYQASM_QUBITS__[5];
    c[2] = measure __PYQASM_QUBITS__[6];
    c[2] = measure __PYQASM_QUBITS__[5];
    """
    result = loads(qasm)
    result.unroll(device_qubits=7)
    check_unrolled_qasm(dumps(result), expected_qasm)


def test_gates():
    qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] data;
    qubit[2] ancilla;
    bit[3] c;
    x data[3];
    cx data[0], ancilla[1];
    crx (0.1) ancilla[0], data[2];
    gate custom_rccx a, b, c{
    rccx a, b, c;
    }
    custom_rccx ancilla[0], data[1], data[0];
    if(c[0]){
       x data[0];
       cx data[1], ancilla[1];
    }
    if(c[1] == 1){
       cx ancilla[0], data[2];
    }
    """
    expected_qasm = """OPENQASM 3.0;
    include "stdgates.inc";
    qubit[6] __PYQASM_QUBITS__;
    bit[3] c;
    x __PYQASM_QUBITS__[3];
    cx __PYQASM_QUBITS__[0], __PYQASM_QUBITS__[5];
    rz(1.5707963267948966) __PYQASM_QUBITS__[2];
    rx(1.5707963267948966) __PYQASM_QUBITS__[2];
    rz(3.141592653589793) __PYQASM_QUBITS__[2];
    rx(1.5707963267948966) __PYQASM_QUBITS__[2];
    rz(3.141592653589793) __PYQASM_QUBITS__[2];
    cx __PYQASM_QUBITS__[4], __PYQASM_QUBITS__[2];
    rz(0) __PYQASM_QUBITS__[2];
    rx(1.5707963267948966) __PYQASM_QUBITS__[2];
    rz(3.0915926535897933) __PYQASM_QUBITS__[2];
    rx(1.5707963267948966) __PYQASM_QUBITS__[2];
    rz(3.141592653589793) __PYQASM_QUBITS__[2];
    cx __PYQASM_QUBITS__[4], __PYQASM_QUBITS__[2];
    rz(0) __PYQASM_QUBITS__[2];
    rx(1.5707963267948966) __PYQASM_QUBITS__[2];
    rz(3.191592653589793) __PYQASM_QUBITS__[2];
    rx(1.5707963267948966) __PYQASM_QUBITS__[2];
    rz(1.5707963267948966) __PYQASM_QUBITS__[2];
    rz(3.141592653589793) __PYQASM_QUBITS__[0];
    rx(1.5707963267948966) __PYQASM_QUBITS__[0];
    rz(4.71238898038469) __PYQASM_QUBITS__[0];
    rx(1.5707963267948966) __PYQASM_QUBITS__[0];
    rz(3.141592653589793) __PYQASM_QUBITS__[0];
    h __PYQASM_QUBITS__[0];
    rx(0.7853981633974483) __PYQASM_QUBITS__[0];
    h __PYQASM_QUBITS__[0];
    cx __PYQASM_QUBITS__[1], __PYQASM_QUBITS__[0];
    h __PYQASM_QUBITS__[0];
    rx(-0.7853981633974483) __PYQASM_QUBITS__[0];
    h __PYQASM_QUBITS__[0];
    cx __PYQASM_QUBITS__[4], __PYQASM_QUBITS__[0];
    h __PYQASM_QUBITS__[0];
    rx(0.7853981633974483) __PYQASM_QUBITS__[0];
    h __PYQASM_QUBITS__[0];
    cx __PYQASM_QUBITS__[1], __PYQASM_QUBITS__[0];
    h __PYQASM_QUBITS__[0];
    rx(-0.7853981633974483) __PYQASM_QUBITS__[0];
    h __PYQASM_QUBITS__[0];
    rz(3.141592653589793) __PYQASM_QUBITS__[0];
    rx(1.5707963267948966) __PYQASM_QUBITS__[0];
    rz(4.71238898038469) __PYQASM_QUBITS__[0];
    rx(1.5707963267948966) __PYQASM_QUBITS__[0];
    rz(3.141592653589793) __PYQASM_QUBITS__[0];
    if (c[0] == true) {
        x __PYQASM_QUBITS__[0];
        cx __PYQASM_QUBITS__[1], __PYQASM_QUBITS__[5];
    }
    if (c[1] == true) {
        cx __PYQASM_QUBITS__[4], __PYQASM_QUBITS__[2];
    }
    """
    result = loads(qasm)
    result.unroll(device_qubits=6)
    check_unrolled_qasm(dumps(result), expected_qasm)


@pytest.mark.parametrize(
    "qasm_code,error_message",
    [
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[4] data;
            qubit[3] ancilla;
            """,
            r"Total qubits '(7)' exceed device qubits '(6)'.",
        ),
        (
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[4] data;
            qubit[2] __PYQASM_QUBITS__;
            """,
            r"Original QASM program already declares reserved register '__PYQASM_QUBITS__'.",
        ),
    ],
)  # pylint: disable-next= too-many-arguments
def test_incorrect_qubit_reg_consolidation(qasm_code, error_message, caplog):
    with pytest.raises(ValidationError) as err:
        with caplog.at_level("ERROR"):
            loads(qasm_code).unroll(device_qubits=6)
    assert error_message in str(err.value)
