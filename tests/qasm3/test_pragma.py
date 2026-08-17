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
Module containing unit tests for Pragma statements.
"""

import openqasm3.ast as qasm3_ast

from pyqasm.entrypoint import dumps, loads
from tests.utils import check_unrolled_qasm


def test_pragma_is_preserved():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    #pragma braket result probability
    qubit[2] q;
    h q[0];
    """
    expected_qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";
    #pragma braket result probability
    qubit[2] q;
    h q[0];
    """
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_pragma_validation():
    qasm_str = """
    OPENQASM 3.0;
    #pragma braket noise bit_flip(0.1) q[0]
    qubit[1] q;
    """
    module = loads(qasm_str)
    module.validate()
    assert module.num_qubits == 1


def test_pragma_round_trip():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    #pragma braket verbatim
    box {
      rx(1.5707963267948966) $0;
      cz $0, $1;
    }
    """
    module = loads(qasm_str)
    module.unroll()
    reloaded = loads(dumps(module))
    reloaded.unroll()
    check_unrolled_qasm(dumps(reloaded), dumps(module))


def test_verbatim_box_is_not_decomposed():
    """Gates in a `#pragma braket verbatim` box must reach the device as written."""
    qasm_str = """
    OPENQASM 3.0;
    bit[2] c;
    #pragma braket verbatim
    box {
      prx(1.5707963267948966, 4.71238898038469) $1;
      cz $2, $1;
    }
    c[0] = measure $2;
    """
    expected_qasm = """
    OPENQASM 3.0;
    bit[2] c;
    #pragma braket verbatim
    box {
      prx(1.5707963267948966, 4.71238898038469) $1;
      cz $2, $1;
    }
    c[0] = measure $2;
    """
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_nested_box_in_verbatim_box_is_not_decomposed():
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    #pragma braket verbatim
    box {
      box {
        prx(0.1, 0.2) q[0];
      }
      cz q[0], q[1];
    }
    """
    expected_qasm = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    #pragma braket verbatim
    box {
      box {
        prx(0.1, 0.2) q[0];
      }
      cz q[0], q[1];
    }
    """
    module = loads(qasm_str)
    module.unroll()
    check_unrolled_qasm(dumps(module), expected_qasm)


def test_non_verbatim_box_is_decomposed():
    """A pragma that is not `braket verbatim` leaves the following box untouched."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    #pragma braket result probability
    box {
      prx(0.1, 0.2) q[0];
    }
    """
    module = loads(qasm_str)
    module.unroll()
    box = module.unrolled_ast.statements[-1]
    assert isinstance(box, qasm3_ast.Box)
    assert [gate.name.name for gate in box.body] == ["rz", "rx", "rz", "rx", "rz"]


def test_verbatim_applies_only_to_the_box_that_follows():
    """The verbatim marker is consumed by the next statement, box or not."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    #pragma braket verbatim
    h q[0];
    box {
      prx(0.1, 0.2) q[0];
    }
    """
    module = loads(qasm_str)
    module.unroll()
    box = module.unrolled_ast.statements[-1]
    assert isinstance(box, qasm3_ast.Box)
    assert [gate.name.name for gate in box.body] == ["rz", "rx", "rz", "rx", "rz"]


def test_verbatim_box_after_verbatim_box():
    """Each verbatim box needs its own pragma."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    #pragma braket verbatim
    box {
      prx(0.1, 0.2) q[0];
    }
    box {
      prx(0.1, 0.2) q[0];
    }
    """
    module = loads(qasm_str)
    module.unroll()
    verbatim_box, plain_box = module.unrolled_ast.statements[-2:]
    assert [gate.name.name for gate in verbatim_box.body] == ["prx"]
    assert [gate.name.name for gate in plain_box.body] == ["rz", "rx", "rz", "rx", "rz"]


def test_verbatim_marker_dropped_by_an_intervening_pragma():
    """Only the pragma immediately preceding a box marks that box verbatim."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    #pragma braket verbatim
    #pragma braket result probability
    box {
      prx(0.1, 0.2) q[0];
    }
    """
    module = loads(qasm_str)
    module.unroll()
    box = module.unrolled_ast.statements[-1]
    assert isinstance(box, qasm3_ast.Box)
    assert [gate.name.name for gate in box.body] == ["rz", "rx", "rz", "rx", "rz"]


def test_verbatim_custom_gate_counts_once_towards_depth():
    """A verbatim gate is emitted as written, so its depth is that of one gate."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    gate my_gate(a) p, r { rx(a) p; cx p, r; rx(a) r; }
    #pragma braket verbatim
    box {
      my_gate(0.3) q[0], q[1];
    }
    """
    module = loads(qasm_str)
    module.unroll()
    assert module.depth() == 1


def test_verbatim_basic_gate_counts_once_towards_depth():
    """A decomposable stdgates gate inside a verbatim box is emitted as written,
    so its depth is that of one gate, not of the skipped decomposition (issue #352)."""
    qasm_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    #pragma braket verbatim
    box {
      crz(0.5) q[0], q[1];
    }
    """
    module = loads(qasm_str)
    module.unroll()
    assert module.depth() == 1


def test_verbatim_marker_does_not_escape_a_box():
    """A pragma at the end of a box body must not mark the next box verbatim.

    The parser keeps pragmas global, so this reaches the visitor through a hand-built
    program - which `loads` accepts just the same.
    """

    def prx_gate():
        return qasm3_ast.QuantumGate(
            [],
            qasm3_ast.Identifier("prx"),
            [qasm3_ast.FloatLiteral(0.1), qasm3_ast.FloatLiteral(0.2)],
            [
                qasm3_ast.IndexedIdentifier(
                    qasm3_ast.Identifier("q"), [[qasm3_ast.IntegerLiteral(0)]]
                )
            ],
        )

    program = qasm3_ast.Program(
        statements=[
            qasm3_ast.QubitDeclaration(qasm3_ast.Identifier("q"), qasm3_ast.IntegerLiteral(1)),
            qasm3_ast.Box(duration=None, body=[prx_gate(), qasm3_ast.Pragma("braket verbatim")]),
            qasm3_ast.Box(duration=None, body=[prx_gate()]),
        ],
        version="3.0",
    )
    module = loads(program)
    module.unroll()
    trailing_box = module.unrolled_ast.statements[-1]
    assert [gate.name.name for gate in trailing_box.body] == ["rz", "rx", "rz", "rx", "rz"]
