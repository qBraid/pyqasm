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

"""Regression tests for inclusive qubit register ranges."""

import pytest

from pyqasm.entrypoint import loads
from pyqasm.exceptions import ValidationError
from tests.utils import check_single_qubit_gate_op


@pytest.mark.parametrize(
    ("qubit_range", "expected_qubits"),
    [
        ("q[0:1]", [0, 1]),
        ("q[3:3]", [3]),
        ("q[0:2:4]", [0, 2, 4]),
        ("q[4:-1:0]", [4, 3, 2, 1, 0]),
        ("q[1:3]", [1, 2, 3]),
        ("q[:]", [0, 1, 2, 3, 4]),
    ],
)
def test_qubit_range_includes_end(qubit_range: str, expected_qubits: list[int]) -> None:
    """Unroll every selected qubit, including an explicit range endpoint."""
    module = loads(f'OPENQASM 3.0; include "stdgates.inc"; qubit[5] q; h {qubit_range};')
    module.unroll()
    check_single_qubit_gate_op(module.unrolled_ast, len(expected_qubits), expected_qubits, "h")


def test_qubit_range_rejects_end_past_register() -> None:
    """The endpoint itself must be a valid qubit index."""
    module = loads('OPENQASM 3.0; include "stdgates.inc"; qubit[4] q; h q[0:4];')
    with pytest.raises(ValidationError, match="Index 4 out of range"):
        module.validate()
