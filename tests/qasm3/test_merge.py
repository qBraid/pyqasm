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
Unit tests for QasmModule.merge().
"""

from pyqasm.entrypoint import loads
from pyqasm.modules import QasmModule


def _qasm3(qasm: str) -> QasmModule:
    return loads(qasm)


def test_merge_basic_gates_and_offsets():
    qasm_a = (
        "OPENQASM 3.0;\n" 'include "stdgates.inc";\n' "qubit[2] q;\n" "x q[0];\n" "cx q[0], q[1];\n"
    )
    qasm_b = (
        "OPENQASM 3.0;\n" 'include "stdgates.inc";\n' "qubit[3] r;\n" "h r[0];\n" "cx r[1], r[2];\n"
    )

    mod_a = _qasm3(qasm_a)
    mod_b = _qasm3(qasm_b)

    merged = mod_a.merge(mod_b)

    # Unrolled representation should have a single consolidated qubit declaration of size 5
    text = str(merged)
    assert "qubit[5] __PYQASM_QUBITS__;" in text

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # Keep only gate lines for comparison; skip version/includes/declarations
    gate_lines = [
        l
        for l in lines
        if l[0].isalpha()
        and not l.startswith("include")
        and not l.startswith("OPENQASM")
        and not l.startswith("qubit")
    ]
    assert gate_lines[0].startswith("x __PYQASM_QUBITS__[0]")
    assert gate_lines[1].startswith("cx __PYQASM_QUBITS__[0], __PYQASM_QUBITS__[1]")
    assert any(l.startswith("h __PYQASM_QUBITS__[2]") for l in gate_lines)
    assert any(l.startswith("cx __PYQASM_QUBITS__[3], __PYQASM_QUBITS__[4]") for l in gate_lines)


def test_merge_with_measurements_and_barriers():
    # Module A: 1 qubit + classical 1; has barrier and measure
    qasm_a = (
        "OPENQASM 3.0;\n"
        'include "stdgates.inc";\n'
        "qubit[1] qa; bit[1] ca;\n"
        "h qa[0];\n"
        "barrier qa;\n"
        "ca[0] = measure qa[0];\n"
    )
    # Module B: 2 qubits + classical 2
    qasm_b = (
        "OPENQASM 3.0;\n"
        'include "stdgates.inc";\n'
        "qubit[2] qb; bit[2] cb;\n"
        "x qb[1];\n"
        "cb[1] = measure qb[1];\n"
    )

    mod_a = _qasm3(qasm_a)
    mod_b = _qasm3(qasm_b)

    merged = mod_a.merge(mod_b)
    merged_text = str(merged)

    assert "qubit[3] __PYQASM_QUBITS__;" in merged_text
    assert "measure __PYQASM_QUBITS__[2];" in merged_text
    assert "barrier __PYQASM_QUBITS__" in merged_text


def test_merge_qasm2_with_qasm3():
    qasm2 = "OPENQASM 2.0;\n" 'include "qelib1.inc";\n' "qreg q[1];\n" "h q[0];\n"
    qasm3 = "OPENQASM 3.0;\n" 'include "stdgates.inc";\n' "qubit[2] r;\n" "x r[0];\n"

    mod2 = loads(qasm2)
    mod3 = loads(qasm3)

    merged = mod2.merge(mod3)
    text = str(merged)
    # Since we are merging starting from a QASM2 module, the merged output
    # should remain in QASM2 syntax (qreg), not QASM3 (qubit).
    assert "OPENQASM 2.0;" in text
    assert 'include "qelib1.inc";' in text
    assert "qreg __PYQASM_QUBITS__[3];" in text
    assert "x __PYQASM_QUBITS__[1];" in text
