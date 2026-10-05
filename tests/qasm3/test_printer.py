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
Module containing unit tests for the Qasm3Printer options.
"""

import pytest

from pyqasm.entrypoint import dumps, loads
from tests.utils import check_unrolled_qasm

QASM3_HEADER = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[2] q;\n'


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        ("rx(pi / 2) q[0];", "rx(pi/2) q[0];"),
        ("rx(pi * 0.5) q[0];", "rx(pi*0.5) q[0];"),
        ("rz(2 * pi) q[0];", "rz(2*pi) q[0];"),
        ("rx(2 ** 3) q[0];", "rx(2**3) q[0];"),
        ("rx(pi / 2 + 1) q[0];", "rx(pi/2 + 1) q[0];"),
        ("rx(pi - 1) q[0];", "rx(pi - 1) q[0];"),
        ("rx(pi / (2 * pi)) q[0];", "rx(pi/(2*pi)) q[0];"),
        ("rx((pi + 1) / 2) q[0];", "rx((pi + 1)/2) q[0];"),
        ("ctrl @ rx(pi / 2) q[0], q[1];", "ctrl @ rx(pi/2) q[0], q[1];"),
        ("gphase(pi / 2);", "gphase(pi/2);"),
    ],
)
def test_compact_gate_arguments(statement, expected):
    module = loads(QASM3_HEADER + statement, compact_gate_arguments=True)
    check_unrolled_qasm(dumps(module), QASM3_HEADER + expected)
    check_unrolled_qasm(str(module), QASM3_HEADER + expected)


def test_compact_gate_arguments_off_by_default():
    qasm = QASM3_HEADER + "rx(pi / 2) q[0];"
    module = loads(qasm)
    assert module.compact_gate_arguments is False
    check_unrolled_qasm(dumps(module), qasm)


def test_compact_gate_arguments_set_after_load():
    qasm = QASM3_HEADER + "rx(pi / 2) q[0];"
    module = loads(qasm)
    module.compact_gate_arguments = True
    check_unrolled_qasm(dumps(module), QASM3_HEADER + "rx(pi/2) q[0];")
    module.compact_gate_arguments = False
    check_unrolled_qasm(dumps(module), qasm)


def test_compact_gate_arguments_survives_unroll_and_copy():
    module = loads(QASM3_HEADER + "rx(pi / 2) q[0];\nh q[1];", compact_gate_arguments=True)
    module.unroll()
    assert module.compact_gate_arguments is True
    copied = module.copy()
    assert copied.compact_gate_arguments is True
    assert dumps(copied) == dumps(module)


def test_compact_gate_arguments_keeps_classical_spacing():
    qasm = QASM3_HEADER + "int[32] a = 3 * 4;\nrx(pi / 2) q[0];\n"
    expected = QASM3_HEADER + "int[32] a = 3 * 4;\nrx(pi/2) q[0];\n"
    check_unrolled_qasm(dumps(loads(qasm, compact_gate_arguments=True)), expected)


def test_compact_gate_arguments_qasm2():
    header = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[1];\n'
    module = loads(header + "rx(pi / 2) q[0];\n", compact_gate_arguments=True)
    check_unrolled_qasm(dumps(module), header + "rx(pi/2) q[0];")
    qasm3_header = 'OPENQASM 3.0;\ninclude "stdgates.inc";\nqubit[1] q;\n'
    check_unrolled_qasm(module.to_qasm3(as_str=True), qasm3_header + "rx(pi/2) q[0];")
    assert module.to_qasm3().compact_gate_arguments is True
