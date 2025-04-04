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
Module containing unit tests for loading measurement operations.

"""
import pytest

from pyqasm.entrypoint import dumps, loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_unrolled_qasm


# Test measurement operations in different ways
def test_measure():
    qasm3_string = """
    OPENQASM 3.0;

    qubit[2] q1;
    qubit[5] q2;
    qubit q3;

    bit[2] c1;
    bit c2;

    // supported
    c1 = measure q1;
    measure q1 -> c1;
    c2[0] = measure q3[0];
    measure q1[:1] -> c1[1];
    measure q2[{0, 1}] -> c1[{1, 0}];

    """

    expected_qasm = """
    OPENQASM 3.0;
    qubit[2] q1;
    qubit[5] q2;
    qubit[1] q3;
    bit[2] c1;
    bit[1] c2;
    c1[0] = measure q1[0]; 
    c1[1] = measure q1[1]; 
    c1[0] = measure q1[0]; 
    c1[1] = measure q1[1]; 
    c2[0] = measure q3[0]; 
    c1[1] = measure q1[0]; 
    c1[1] = measure q2[0]; 
    c1[0] = measure q2[1]; 
    """

    module = loads(qasm3_string)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_has_measurements():
    qasm3_string_with_measure = """
    OPENQASM 3.0;

    qubit[2] q1;
    qubit[5] q2;
    qubit q3;

    bit[2] c1;
    bit c2;

    c1 = measure q1;
    measure q1 -> c1;
    c2[0] = measure q3[0];
    measure q1[:1] -> c1[1];
    measure q2[{0, 1}] -> c1[{1, 0}];

    """
    qasm_module = loads(qasm3_string_with_measure)
    assert qasm_module.has_measurements()

    qasm3_string_without_measure = """
    OPENQASM 3.0;

    qubit[2] q1;
    qubit[5] q2;
    """
    qasm_module = loads(qasm3_string_without_measure)
    assert not qasm_module.has_measurements()


def test_remove_measurement():
    qasm3_string = """
    OPENQASM 3.0;

    qubit[2] q1;
    qubit[5] q2;
    qubit q3;

    bit[2] c1;
    bit c2;

    c1 = measure q1;
    measure q1 -> c1;
    c2[0] = measure q3[0];
    measure q1[:1] -> c1[1];
    measure q2[{0, 1}] -> c1[{1, 0}];

    """

    expected_qasm = """
    OPENQASM 3.0;
    qubit[2] q1;
    qubit[5] q2;
    qubit[1] q3;
    bit[2] c1;
    bit[1] c2;
    """

    module = loads(qasm3_string)
    module.unroll()
    module.remove_measurements()

    check_unrolled_qasm(dumps(module), expected_qasm)


def test_init_measure():
    qasm3_string = """
    OPENQASM 3.0;
    qubit a;
    qubit[2] b;
    qubit[4] e;
    bit c = measure a;
    bit[2] d = measure b;
    bit[2] f = measure e[:2];
    bit[2] g = measure e[{2, 3}];
    """

    expected_qasm = """
    OPENQASM 3.0;
    qubit[1] a;
    qubit[2] b;
    qubit[4] e;
    bit[1] c;
    c[0] = measure a[0];
    bit[2] d;
    d[0] = measure b[0];
    d[1] = measure b[1];
    bit[2] f;
    f[0] = measure e[0];
    f[1] = measure e[1];
    bit[2] g;
    g[0] = measure e[2];
    g[1] = measure e[3];
    """

    module = loads(qasm3_string)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_standalone_measurement():
    qasm3_string = """
    OPENQASM 3.0;
    qubit[2] q;
    h q;
    measure q;
    """

    expected_qasm = """
    OPENQASM 3.0;
    qubit[2] q;
    h q[0];
    h q[1];
    measure q[0];
    measure q[1];
    """

    module = loads(qasm3_string)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_incorrect_measure():
    def run_test(qasm3_code, error_message):
        with pytest.raises(ValidationError, match=error_message):
            loads(qasm3_code).validate()

    # Test for undeclared register q2
    run_test(
        """
        OPENQASM 3.0;
        qubit[2] q1;
        bit[2] c1;
        c1[0] = measure q2[0];  // undeclared register
    """,
        r"Missing register declaration for q2 .*",
    )

    # Test for undeclared register c2
    run_test(
        """
        OPENQASM 3.0;
        qubit[2] q1;
        bit[2] c1;
        measure q1 -> c2;  // undeclared register
    """,
        r"Missing register declaration for c2 .*",
    )

    # Test for size mismatch between q1 and c2
    run_test(
        """
        OPENQASM 3.0;
        qubit[2] q1;
        bit[2] c1;
        bit[1] c2;
        c2 = measure q1;  // size mismatch
    """,
        r"Register sizes of q1 and c2 do not match .*",
    )

    # Test for size mismatch between q1 and c2 in ranges
    run_test(
        """
        OPENQASM 3.0;
        qubit[5] q1;
        bit[4] c1;
        bit[1] c2;
        c1[:3] = measure q1;  // size mismatch
    """,
        r"Register sizes of q1 and c1 do not match .*",
    )

    # Test for out of bounds index for q1
    run_test(
        """
        OPENQASM 3.0;
        qubit[2] q1;
        bit[2] c1;
        measure q1[3] -> c1[0];  // out of bounds
    """,
        r"Index 3 out of range for register of size 2 in qubit",
    )

    # Test for out of bounds index for c1
    run_test(
        """
        OPENQASM 3.0;
        qubit[2] q1;
        bit[2] c1;
        measure q1 -> c1[3];  // out of bounds
    """,
        r"Index 3 out of range for register of size 2 in clbit",
    )
