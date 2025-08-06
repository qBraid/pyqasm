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
Test the compare() method of the QasmModule class.
"""

import pytest

from pyqasm.elements import BasisSet
from pyqasm.entrypoint import loads


def test_compare_method_output(capsys):
    """
    Tests the output of the QasmModule.compare() method to ensure it
    correctly identifies and displays differences between two modules.
    """
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q;
    h q[0];
    cx q[0], q[1];
    barrier q;
    """

    module_a = loads(qasm_str)
    module_b = loads(qasm_str)

    module_a.unroll()
    module_b.unroll(unroll_barriers=False, external_gates=["cx"])
    module_b.rebase(BasisSet.ROTATIONAL_CX)

    module_a.compare(module_b)
    captured = capsys.readouterr()
    stdout = captured.out

    print(stdout)

    assert "Attribute" in stdout
    assert "Self" in stdout
    assert "Other" in stdout
    assert "Qubits" in stdout
    assert "Depth" in stdout
    assert "History" in stdout
    assert "External Gates" in stdout
    assert "Gate Counts" in stdout
    assert "unroll({})" in stdout
    assert "unroll({'unroll_barriers': False, 'external_gates': ['cx']})" in stdout
    assert "rebase(BasisSet.ROTATIONAL_CX)" in stdout
    assert "h" in stdout
    assert "cx" in stdout
    assert "barrier" in stdout


def test_compare_with_measurements_and_barriers(capsys):
    """Test compare method with modules that have measurements and barriers."""
    qasm_with_both = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q;
    bit[2] c;
    h q[0];
    barrier q;
    cx q[0], q[1];
    c = measure q;
    """

    qasm_without_both = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q;
    h q[0];
    cx q[0], q[1];
    """

    module_with_both = loads(qasm_with_both)
    module_without_both = loads(qasm_without_both)

    module_with_both.compare(module_without_both)
    captured = capsys.readouterr()
    stdout = captured.out

    assert "Measurements" in stdout
    assert "Barriers" in stdout
    assert "True" in stdout
    assert "False" in stdout
    assert "Classical Bits" in stdout


def test_compare_invalid_type():
    """Test compare method with invalid input type raises TypeError."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q;
    h q[0];
    """

    module = loads(qasm_str)

    with pytest.raises(TypeError, match="Expected QasmModule instance, got str"):
        module.compare("not a module")

    with pytest.raises(TypeError, match="Expected QasmModule instance, got int"):
        module.compare(42)
