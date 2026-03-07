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
Module containing unit tests for program formatting

"""

from pyqasm.entrypoint import dumps, loads
from tests.utils import check_unrolled_qasm


def test_comments_removed_from_qasm():
    qasm2_string = """
    OPENQASM 2.0;
    include "qelib1.inc";
    // This is a comment
    qreg q[1];
    // This is another comment
    h q[0];
    """
    expected_qasm2_string = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[1];
    h q[0];
    """

    result = loads(qasm2_string)
    actual_qasm2_string = dumps(result)

    check_unrolled_qasm(actual_qasm2_string, expected_qasm2_string)


def test_empty_lines_removed_from_qasm():
    qasm2_string = """
    OPENQASM 2.0;


    include "qelib1.inc";



    qreg q[1];
    h q[0];



    
    """
    expected_qasm2_string = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[1];
    h q[0];
    """

    result = loads(qasm2_string)
    actual_qasm2_string = dumps(result)

    check_unrolled_qasm(actual_qasm2_string, expected_qasm2_string)
