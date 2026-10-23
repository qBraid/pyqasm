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
Module containing unit tests for OpenQASM 3 gate broadcasting over registers.

"""

import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            "qubit[2] a;\nqubit[2] b;\ncx a, b;",
            "qubit[2] a;\nqubit[2] b;\ncx a[0], b[0];\ncx a[1], b[1];",
        ),
        (
            "qubit[4] q;\ncx q[0:1], q[2:3];",
            "qubit[4] q;\ncx q[0], q[2];\ncx q[1], q[3];",
        ),
        (
            "qubit[4] q;\nlet a = q[0:1];\nlet b = q[2:3];\ncx a, b;",
            "qubit[4] q;\ncx q[0], q[2];\ncx q[1], q[3];",
        ),
        (
            "def f(qubit[2] a, qubit[2] b) { cx a, b; }\nqubit[2] r;\nqubit[2] s;\nf(r, s);",
            "qubit[2] r;\nqubit[2] s;\ncx r[0], s[0];\ncx r[1], s[1];",
        ),
        (
            "qubit[2] a;\nqubit[2] b;\nswap a, b;",
            "qubit[2] a;\nqubit[2] b;\nswap a[0], b[0];\nswap a[1], b[1];",
        ),
        (
            "qubit[2] a;\nqubit[2] b;\nctrl @ x a, b;",
            "qubit[2] a;\nqubit[2] b;\ncx a[0], b[0];\ncx a[1], b[1];",
        ),
        (
            "qubit[3] q;\nqubit[1] r;\ncx q, r[0];",
            "qubit[3] q;\nqubit[1] r;\ncx q[0], r[0];\ncx q[1], r[0];\ncx q[2], r[0];",
        ),
    ],
    ids=["registers", "slices", "aliases", "subroutine-registers", "swap", "ctrl", "mixed"],
)
def test_broadcast_pairs_register_operands(body, expected):
    """Register operands pair element by element and single qubits repeat (issue #384)."""
    header = 'OPENQASM 3.0;\ninclude "stdgates.inc";\n'
    result = loads(header + body)
    result.unroll()
    check_unrolled_qasm(dumps(result), header + expected)


def test_broadcast_spec_example():
    """The spec's g4 example applies the gate once per index of qr1 and qr3."""
    qasm3_string = """
    OPENQASM 3.0;
    gate g4 a, b, c, d { }
    qubit[1] qr0;
    qubit[3] qr1;
    qubit[2] qr2;
    qubit[3] qr3;
    g4 qr0[0], qr1, qr2[0], qr3;
    """
    result = loads(qasm3_string)
    result.unroll(external_gates=["g4"])
    gates = [line for line in dumps(result).splitlines() if line.startswith("g4")]
    assert gates == [
        "g4 qr0[0], qr1[0], qr2[0], qr3[0];",
        "g4 qr0[0], qr1[1], qr2[0], qr3[1];",
        "g4 qr0[0], qr1[2], qr2[0], qr3[2];",
    ]


def test_broadcast_register_length_mismatch_raises():
    """Register operands of different lengths cannot be paired."""
    qasm3_string = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[2] a;\nqubit[3] b;\ncx a, b;\n'
    with pytest.raises(ValidationError, match="different lengths"):
        loads(qasm3_string).unroll()
