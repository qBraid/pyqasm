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
Module containing unit tests for OpenQASM 3 gate broadcasting.

Broadcasting applies a gate once per index across register operands, repeating
single-qubit operands. See https://openqasm.com/versions/3.1/language/gates.html#broadcasting

"""

import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


def test_two_register_broadcast_zips_elementwise():
    """`cx q, r` with two same-size registers must zip, not linear-chunk (#384)."""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    qubit[4] r;
    cx q, r;
    """
    expected = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    qubit[4] r;
    cx q[0], r[0];
    cx q[1], r[1];
    cx q[2], r[2];
    cx q[3], r[3];
    """
    module = loads(qasm3_string)
    module.unroll()

    assert module.num_qubits == 8
    check_unrolled_qasm(dumps(module), expected)


def test_mixed_register_and_single_qubit_broadcast():
    """`cx q, r[0]` (register + single qubit) must broadcast r[0] to every q[i] (#384)."""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    qubit[1] r;
    cx q, r[0];
    """
    expected = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    qubit[1] r;
    cx q[0], r[0];
    cx q[1], r[0];
    cx q[2], r[0];
    cx q[3], r[0];
    """
    module = loads(qasm3_string)
    module.unroll()

    check_unrolled_qasm(dumps(module), expected)


def test_spec_example_g4_broadcast_repeats_single_qubit_operands():
    """OpenQASM 3.1 broadcasting example: g4 qr0[0], qr1, qr2[0], qr3 (#384).

    See https://openqasm.com/versions/3.1/language/gates.html#broadcasting -
    register operands qr1, qr3 (length 3) drive three applications; qr0[0]
    and qr2[0] are repeated element-wise.
    """
    qasm3_string = """
    OPENQASM 3.0;
    gate g4 a, b, c, d { }
    qubit[1] qr0;
    qubit[3] qr1;
    qubit[1] qr2;
    qubit[3] qr3;
    g4 qr0[0], qr1, qr2[0], qr3;
    """
    expected = """
    OPENQASM 3.0;
    qubit[1] qr0;
    qubit[3] qr1;
    qubit[1] qr2;
    qubit[3] qr3;
    g4 qr0[0], qr1[0], qr2[0], qr3[0];
    g4 qr0[0], qr1[1], qr2[0], qr3[1];
    g4 qr0[0], qr1[2], qr2[0], qr3[2];
    """
    module = loads(qasm3_string)
    module.unroll(external_gates=["g4"])
    check_unrolled_qasm(dumps(module), expected)


def test_broadcast_size_mismatch_raises():
    """Register operands of different sizes must raise, naming both operands (#384)."""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    qubit[3] r;
    cx q, r;
    """
    with pytest.raises(
        ValidationError,
        match=r"Register operands broadcast to different sizes for gate 'cx':"
        r" operand 'q' \(size 4\) and operand 'r' \(size 3\)",
    ):
        loads(qasm3_string).unroll()


def test_broadcast_under_ctrl_modifier():
    """`ctrl @ cx ctrl_q, a, b` with a, b registers must broadcast targets per i (#384)."""
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit ctrl_q;
    qubit[3] a;
    qubit[3] b;
    ctrl @ cx ctrl_q, a, b;
    """
    expected = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] ctrl_q;
    qubit[3] a;
    qubit[3] b;
    ccx ctrl_q[0], a[0], b[0];
    ccx ctrl_q[0], a[1], b[1];
    ccx ctrl_q[0], a[2], b[2];
    """
    module = loads(qasm3_string)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected)


def test_ambiguous_multi_register_broadcast_raises():
    """`cx q, r, s` (3 register operands, arity 2) is ambiguous and must raise (#384).

    Previously silently linear-chunked to `cx q[0],q[1]; cx r[0],r[1]; cx s[0],s[1]`,
    which is the exact silent-wrong behavior #384 flags.
    """
    qasm3_string = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[2] r;
    qubit[2] s;
    cx q, r, s;
    """
    with pytest.raises(
        ValidationError,
        match=r"Cannot broadcast operation 'cx' onto 3 operand\(s\)",
    ):
        loads(qasm3_string).unroll()
