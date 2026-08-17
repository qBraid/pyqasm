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
Module containing unit tests for transformations on qasm3 programs

"""

import pytest
from openqasm3.ast import DiscreteSet, Identifier, IndexedIdentifier, IntegerLiteral, Span

from pyqasm.analyzer import Qasm3Analyzer
from pyqasm.elements import BasisSet
from pyqasm.entrypoint import dumps, loads
from pyqasm.maps import QUANTUM_STATEMENTS
from pyqasm.maps.gates import fresh_qubits
from tests.utils import check_unrolled_qasm


def test_remove_idle_qubits_qasm3_small():
    """Test that remove_idle_qubits for qasm3 string"""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    h q[1];
    cx q[1], q[3];
    """

    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    h q[0];
    cx q[0], q[1];
    """
    module = loads(qasm3_str)
    assert module.num_qubits == 4
    module.remove_idle_qubits()
    assert module.num_qubits == 2
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_remove_idle_qubits_not_in_place():
    """Test remove_idle_qubits(in_place=False) updates the copy and leaves the
    original module untouched"""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    h q[1];
    cx q[1], q[3];
    """
    module = loads(qasm3_str)
    module.unroll()
    new_module = module.remove_idle_qubits(in_place=False)

    assert new_module.num_qubits == 2
    assert "qubit[2] q;" in dumps(new_module)

    assert module.num_qubits == 4
    assert "qubit[4] q;" in dumps(module)


def test_remove_idle_qubits_qasm3():
    """Test conversion of qasm3 to compressed contiguous qasm3"""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    gate custom q1, q2, q3{
        x q1;
        y q2;
        z q3;
    }
    qreg q1[2];
    qubit[2] q2;
    qubit[3] q3;
    qubit q4;
    qubit[5]   q5;
    qreg qr[3];
    
    x q1[0];
    y q2[1];
    z q3;
    
    
    qubit[3] q6;
    
    cx q6[1], q6[2];
    """

    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q1;
    qubit[1] q2;
    qubit[3] q3;
    x q1[0];
    y q2[0];
    z q3[0];
    z q3[1];
    z q3[2];
    qubit[2] q6;
    cx q6[0], q6[1];
    """

    module = loads(qasm3_str)
    assert module.num_qubits == 19
    module.remove_idle_qubits()
    assert module.num_qubits == 7

    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_reverse_qubit_order_qasm3():
    """Test the reverse qubit ordering function for qasm3 string"""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit q3;
    bit[1] c; 

    cnot q[0], q[1];
    cnot q2[0], q2[1];
    x q2[3];
    cnot q2[0], q2[2];
    x q3;
    c[0] = measure q2[0];
    """

    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit[1] q3;
    bit[1] c;

    cx q[1], q[0];
    cx q2[3], q2[2];
    x q2[0];
    cx q2[3], q2[1];
    x q3[0];

    c[0] = measure q2[3];
    """

    module = loads(qasm3_str)
    module.reverse_qubit_order()
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_reverse_qubit_order_gate_decomposition():
    """Test reverse_qubit_order on a decomposed gate whose statements previously
    shared operand nodes (issue #333)"""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    crz(0.5) q[1], q[2];
    """

    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    rz(0.25) q[0];
    rx(1.5707963267948966) q[0];
    rz(3.141592653589793) q[0];
    rx(1.5707963267948966) q[0];
    rz(3.141592653589793) q[0];
    cx q[1], q[0];
    rz(-0.25) q[0];
    rx(1.5707963267948966) q[0];
    rz(3.141592653589793) q[0];
    rx(1.5707963267948966) q[0];
    rz(3.141592653589793) q[0];
    cx q[1], q[0];
    """

    module = loads(qasm3_str)
    module.unroll()
    module.reverse_qubit_order()
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def _assert_no_shared_operand_nodes(module):
    """Assert no two quantum statements in the unrolled AST share an operand node"""
    seen_bits: set[int] = set()
    seen_indices: set[int] = set()
    for statement in module._unrolled_ast.statements:
        if isinstance(statement, QUANTUM_STATEMENTS):
            for bit in Qasm3Analyzer.get_op_bit_list(statement):
                assert id(bit) not in seen_bits, f"operand node shared: {bit}"
                seen_bits.add(id(bit))
                # physical qubits are bare Identifiers, and an index may be a DiscreteSet
                # or multi-dimensional; only plain reg[int] operands have an index node
                if not isinstance(bit, IndexedIdentifier):
                    continue
                indices = bit.indices
                if not (
                    len(indices) == 1 and isinstance(indices[0], list) and len(indices[0]) == 1
                ):
                    continue
                index_node = indices[0][0]
                assert id(index_node) not in seen_indices, f"index node shared: {bit}"
                seen_indices.add(id(index_node))


@pytest.mark.parametrize(
    "operation",
    [
        "crz(0.5) q[1], q[2];",
        "crx(0.5) q[0], q[1];",
        "c4x q[0], q[1], q[2], q[3], q[4];",
        "ecr q[0], q[1];",
        "inv @ crz(0.5) q[1], q[2];",
        "negctrl @ x q[0], q[1];",
        "negctrl(2) @ x q[0], q[1], q[2];",
        # each of these reaches the negctrl expansion through a different
        # operand shape or repeats it, so each is a distinct way to regress
        "negctrl @ x q[{0, 1}], q[2];",
        "pow(2) @ negctrl @ x q[0], q[1];",
        "ctrl @ negctrl @ x q[0], q[1], q[2];",
    ],
)
def test_unroll_emits_fresh_operand_nodes(operation):
    """Test that unroll() never emits statements sharing operand nodes, so in-place
    transformations remap each operand exactly once (issues #331, #333)"""
    qasm3_str = f"""
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[5] q;
    {operation}
    """
    module = loads(qasm3_str)
    module.unroll()
    _assert_no_shared_operand_nodes(module)


def test_reverse_qubit_order_negctrl():
    """Test reverse_qubit_order on a negctrl gate whose leading and trailing x
    statements previously were the same object (issue #350)"""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    negctrl @ x q[0], q[1];
    """

    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    x q[2];
    cx q[2], q[1];
    x q[2];
    """

    module = loads(qasm3_str)
    module.unroll()
    module.reverse_qubit_order()
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_remove_idle_qubits_negctrl():
    """Test remove_idle_qubits on a negctrl gate whose leading and trailing x
    statements previously were the same object (issue #350).

    This path survived the aliasing only via the ``visited_node_ids`` guard in
    ``_remap_qubits``, so it is pinned here to keep that incidental rescue from
    being the only thing standing between a refactor and the crash.
    """
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    negctrl @ x q[0], q[1];
    """

    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    x q[0];
    cx q[0], q[1];
    x q[0];
    """

    module = loads(qasm3_str)
    module.unroll()
    module.remove_idle_qubits()
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_consolidate_qubits_negctrl():
    """Test unroll(consolidate_qubits=True) on a negctrl gate whose leading and
    trailing x statements previously were the same object (issue #350).

    Consolidation rewrote the shared operand once, then met the already-renamed
    node again and raised ``KeyError: '__PYQASM_QUBITS__'``.
    """
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    negctrl @ x q[0], q[1];
    """

    expected_qasm3_str = """
    OPENQASM 3.0;
    qubit[3] __PYQASM_QUBITS__;
    include "stdgates.inc";
    x __PYQASM_QUBITS__[0];
    cx __PYQASM_QUBITS__[0], __PYQASM_QUBITS__[1];
    x __PYQASM_QUBITS__[0];
    """

    module = loads(qasm3_str)
    module.unroll(consolidate_qubits=True)
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


@pytest.mark.parametrize(
    "operation", ["crz(0.5) q[1], q[2];", "swap q[0], q[2];", "cz q[1], q[2];"]
)
def test_rebase_emits_fresh_operand_nodes(operation):
    """Test that rebase() never emits statements sharing operand nodes (issue #333)

    ``swap`` and ``cz`` are in DECOMPOSITION_RULES so they exercise
    Decomposer._get_decomposed_gates; ``crz`` is handled by maps/gates.py instead.
    """
    qasm3_str = f"""
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    {operation}
    """
    module = loads(qasm3_str).rebase(BasisSet.ROTATIONAL_CX)
    _assert_no_shared_operand_nodes(module)


@pytest.mark.parametrize(
    "qubit",
    [
        # plain reg[int] operand, rebuilt node by node
        IndexedIdentifier(Identifier("q"), [[IntegerLiteral(2)]]),
        # physical qubit, kept as a bare Identifier
        Identifier("$0"),
        # anything else falls back to a deep copy
        IndexedIdentifier(Identifier("q"), [DiscreteSet([IntegerLiteral(0), IntegerLiteral(1)])]),
        IndexedIdentifier(Identifier("q"), [[IntegerLiteral(0)], [IntegerLiteral(1)]]),
    ],
)
def test_fresh_qubits_shares_no_nodes(qubit):
    """Test that fresh_qubits returns an equal operand that shares no node with the original"""
    qubit.span = Span(1, 0, 1, 4)

    (copied,) = fresh_qubits(qubit)

    assert copied == qubit
    assert copied.span == qubit.span
    assert copied is not qubit
    if isinstance(qubit, IndexedIdentifier):
        assert copied.name is not qubit.name
        for copied_dim, original_dim in zip(copied.indices, qubit.indices):
            assert copied_dim is not original_dim
            copied_exprs = copied_dim.values if isinstance(copied_dim, DiscreteSet) else copied_dim
            original_exprs = (
                original_dim.values if isinstance(original_dim, DiscreteSet) else original_dim
            )
            for copied_index, original_index in zip(copied_exprs, original_exprs):
                assert copied_index is not original_index


def test_populate_idle_qubits_qasm3():
    """Test the populate idle qubits function for qasm3 string"""

    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit q3;
    bit[1] c;

    cnot q;
    """

    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit[1] q3;
    bit[1] c;

    cnot q;
    id q2[0];
    id q2[1];
    id q2[2];
    id q2[3];
    id q3[0];
    """

    module = loads(qasm3_str)
    module.populate_idle_qubits()
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_populate_idle_qubits_for_no_idle_qubits():
    """Test the populate idle qubits function for qasm3 string"""

    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit q3;
    bit[1] c;

    h q;
    h q2;
    h q3;
    """
    # no change in the qasm
    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit[1] q3;
    bit[1] c;
    
    h q;
    h q2;
    h q3;
    """

    module = loads(qasm3_str)
    module.populate_idle_qubits()
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_populate_idle_qubits_increases_depth_by_one():
    """Test that the depth of the program increases by one when populating idle qubits"""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    qubit[4] q2;
    qubit q3;
    
    """
    module = loads(qasm3_str)
    original_depth = module.depth()
    module.populate_idle_qubits()
    assert module.depth() == original_depth + 1


def test_remove_idle_qubits_inside_box():
    """Operands nested in a box must be remapped along with the top-level ones (see #342)."""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    bit c;
    h q[2];
    box {
        cx q[2], q[1];
    }
    c = measure q[1];
    """
    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit[1] c;
    h q[1];
    box {
        cx q[1], q[0];
    }
    c[0] = measure q[0];
    """
    module = loads(qasm3_str)
    module.remove_idle_qubits()
    assert module.num_qubits == 2
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_remove_idle_qubits_keeps_qubits_used_in_a_branch():
    """A qubit touched only inside an if block is in use, so it must not be removed."""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    bit c;
    h q[2];
    c = measure q[2];
    if (c == 1) {
        x q[1];
    }
    """
    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit[1] c;
    h q[1];
    c[0] = measure q[1];
    if (c[0] == true) {
        x q[0];
    }
    """
    module = loads(qasm3_str)
    module.remove_idle_qubits()
    assert module.num_qubits == 2
    check_unrolled_qasm(dumps(module), expected_qasm3_str)
    # the result must still be a valid program
    loads(dumps(module)).validate()


def test_remove_idle_qubits_with_physical_qubits():
    """Physical qubits belong to no register, so the remap must skip over them."""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    h $1;
    h q[0];
    """
    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[1] q;
    h $1;
    h q[0];
    """
    module = loads(qasm3_str)
    module.unroll()
    module.remove_idle_qubits()
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_reverse_qubit_order_inside_box_and_branch():
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    bit c;
    h q[2];
    box {
        cx q[2], q[1];
    }
    c = measure q[0];
    if (c == 1) {
        x q[0];
    }
    """
    expected_qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[3] q;
    bit[1] c;
    h q[0];
    box {
        cx q[0], q[1];
    }
    c[0] = measure q[2];
    if (c[0] == true) {
        x q[2];
    }
    """
    module = loads(qasm3_str)
    module.reverse_qubit_order()
    check_unrolled_qasm(dumps(module), expected_qasm3_str)


def test_remove_idle_qubits_keeps_qubits_used_by_a_custom_gate_in_a_branch():
    """The expansion of a custom gate in a branch marks its qubits as used."""
    qasm3_str = """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[2] q;
    bit c;
    gate my_gate p, r { x p; cx p, r; }
    h q[0];
    c = measure q[0];
    if (c == 1) {
        my_gate q[0], q[1];
    }
    """
    module = loads(qasm3_str)
    module.remove_idle_qubits()
    assert module.num_qubits == 2
