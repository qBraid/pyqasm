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
Module containing unit tests for linalg.py functions.

"""

import pytest

from pyqasm import ValidationError, dumps, loads
from tests.utils import check_unrolled_qasm


def test_no_include_added():
    qasm_str = """
    OPENQASM 3.0;
    include "random.qasm";
    """
    expected_qasm_str = """
    OPENQASM 3.0;
    include "random.qasm";
    """
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm_str)


def test_includes_preserved():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    include "random.qasm";

    qubit[2] q;
    h q;
    """
    expected_qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    include "random.qasm";
    qubit[2] q;
    h q[0];
    h q[1];
    """
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm_str)


def test_repeated_include_raises_error():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    include "stdgates.inc";
    """
    with pytest.raises(ValidationError):
        module = loads(qasm_str)
        module.validate()


def test_remove_includes():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    include "random.qasm";

    qubit[2] q;
    h q;
    """
    expected_qasm_str = """
    OPENQASM 3.0;
    qubit[2] q;
    h q[0];
    h q[1];
    """
    module = loads(qasm_str)
    module.remove_includes()
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm_str)


def test_remove_includes_without_include():
    qasm_str = """
    OPENQASM 3.0;

    qubit[2] q;
    h q;
    """
    expected_qasm_str = """
    OPENQASM 3.0;
    qubit[2] q;
    h q[0];
    h q[1];
    """
    module = loads(qasm_str)
    module = module.remove_includes(in_place=False)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm_str)
