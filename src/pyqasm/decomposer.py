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
Definition of the Decomposer class
"""

import openqasm3.ast as qasm3_ast
from openqasm3.ast import BranchingStatement, QuantumGate

from pyqasm.algorithms import solovay_kitaev
from pyqasm.exceptions import RebaseError
from pyqasm.maps.decomposition_rules import (
    DECOMPOSITION_RULES,
    ROTATIONAL_LOOKUP_RULES,
    AppliedQubit,
)
from pyqasm.maps.expressions import CONSTANTS_MAP
from pyqasm.maps.gates import BASIS_GATE_MAP, get_target_matrix_for_rotational_gates


class Decomposer:
    """
    Class to decompose the gates based on the target basis set.
    """

    @classmethod
    def process_gate_statement(
        cls, gate_name, statement, target_basis_set, depth=10, accuracy=1e-6
    ):
        """Process the gate statement based on the target basis set.

        Args:
            gate_name: The name of the gate to process.
            statement: The statement to process.
            target_basis_set: The target basis set to rebase the module to.
            depth: The depth of the approximation.
            accuracy: The accuracy of the approximation.

        Returns:
            list: The processed gates based on the target basis set.
        """
        decomposition_rules = DECOMPOSITION_RULES[target_basis_set]
        target_basis_gate_list = BASIS_GATE_MAP[target_basis_set]

        processed_gates_list = []

        if gate_name in target_basis_gate_list:
            # Keep the gate as is
            processed_gates_list = [statement]
        elif gate_name in decomposition_rules:
            # Decompose the gates
            rule_list = decomposition_rules[gate_name]
            processed_gates_list = cls._get_decomposed_gates(rule_list, statement)
        elif gate_name in {"rx", "ry", "rz"}:
            processed_gates_list = cls._process_rotational_gate(
                gate_name, statement, target_basis_set, depth, accuracy
            )
        else:
            # Raise an error if the gate is not supported in the target basis set
            error = f"Gate '{gate_name}' is not supported in the '{target_basis_set} set'."
            raise RebaseError(error)

        return processed_gates_list

    @classmethod
    def process_branching_statement(cls, branching_statement, target_basis_set, depth, accuracy):
        """Process the branching statement based on the target basis set.

        Args:
            branching_statement: The branching statement to process.
            target_basis_set: The target basis set to rebase the module to.
            depth: The depth of the approximation.
            accuracy: The accuracy of the approximation.

        Returns:
            BranchingStatement: The processed branching statement based on the target basis set.
        """
        if_block = []
        else_block = []

        for statement in branching_statement.if_block:
            if isinstance(statement, QuantumGate):
                gate_name = statement.name.name
                processed_gates_list = cls.process_gate_statement(
                    gate_name, statement, target_basis_set
                )
                if_block.extend(processed_gates_list)
            elif isinstance(statement, BranchingStatement):
                if_block.append(
                    cls.process_branching_statement(statement, target_basis_set, depth, accuracy)
                )
            else:
                if_block.append(statement)

        for statement in branching_statement.else_block:
            if isinstance(statement, QuantumGate):
                gate_name = statement.name.name
                processed_gates_list = cls.process_gate_statement(
                    gate_name, statement, target_basis_set
                )
                else_block.extend(processed_gates_list)
            elif isinstance(statement, BranchingStatement):
                else_block.append(
                    cls.process_branching_statement(statement, target_basis_set, depth, accuracy)
                )
            else:
                else_block.append(statement)

        return BranchingStatement(
            condition=branching_statement.condition, if_block=if_block, else_block=else_block
        )

    @classmethod
    def _get_decomposed_gates(cls, rule_list, statement):
        """Apply the decomposed gates based on the decomposition rules.

        Args:
            rule_list: The decomposition rules to apply.
            statement: The statement to apply the decomposition rules to.

        Returns:
            list: The decomposed gates to be applied.
        """
        decomposed_gates = []

        for rule in rule_list:
            qubits = cls._get_qubits_for_gate(statement.qubits, rule)
            arguments = [qasm3_ast.FloatLiteral(value=rule["param"])] if "param" in rule else []

            new_gate = qasm3_ast.QuantumGate(
                modifiers=[],
                name=qasm3_ast.Identifier(name=rule if isinstance(rule, str) else rule["gate"]),
                arguments=arguments,
                qubits=qubits,
            )

            decomposed_gates.append(new_gate)
        return decomposed_gates

    @classmethod
    def _get_qubits_for_gate(cls, qubits, rule):
        """
        Determines the order of qubits to be used for a gate operation based on the provided rule.

        Args:
            qubits: The qubits to be used for the gate operation.
            rule: The decomposition rule to apply.

        Returns:
            list: The ordered qubits to be used for the gate operation.
        """
        if "controll_bit" in rule:
            if rule["controll_bit"] == AppliedQubit.QUBIT1:
                qubits = [qubits[0], qubits[1]]
            else:
                qubits = [qubits[1], qubits[0]]

        elif "target_bit" in rule:
            if rule["target_bit"] == AppliedQubit.QUBIT1:
                qubits = [qubits[0]]
            else:
                qubits = [qubits[1]]
        return qubits

    @classmethod
    def _process_rotational_gate(cls, gate_name, statement, target_basis_set, depth, accuracy):
        """Process the rotational gates based on the target basis set.

        Args:
            gate_name: The name of the gate.
            statement: The statement to process.
            target_basis_set: The target basis set to rebase the module to.
            depth: The depth of the approximation.
            accuracy: The accuracy of the approximation.

        Returns:
            list: The processed gates based on the target basis set.
        """
        theta = statement.arguments[0].value
        processed_gates_list = []

        # Use lookup table if ∅ is pi, pi/2 or pi/4
        if theta in [CONSTANTS_MAP["pi"], CONSTANTS_MAP["pi"] / 2, CONSTANTS_MAP["pi"] / 4]:
            rotational_lookup_rules = ROTATIONAL_LOOKUP_RULES[target_basis_set]
            rule_list = rotational_lookup_rules[gate_name][theta]
            processed_gates_list = cls._get_decomposed_gates(rule_list, statement)

        # Use Solovay-Kitaev's Algorithm for gate approximation
        else:
            target_matrix = get_target_matrix_for_rotational_gates(gate_name, theta)
            approximated_gates = solovay_kitaev(target_matrix, target_basis_set, depth, accuracy)

            for approximated_gate_name in approximated_gates.name:
                new_gate = qasm3_ast.QuantumGate(
                    modifiers=[],
                    name=qasm3_ast.Identifier(name=approximated_gate_name),
                    arguments=[],
                    qubits=statement.qubits,
                )

                processed_gates_list.append(new_gate)
        return processed_gates_list
