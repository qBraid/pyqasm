# Copyright (C) 2025 qBraid
#
# This file is part of PyQASM
#
# PyQASM is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for PyQASM, as per Section 15 of the GPL v3.

"""
Definition of the Decomposer class
"""

import openqasm3.ast as qasm3_ast
from openqasm3.ast import BranchingStatement, QuantumGate

from pyqasm.exceptions import RebaseError
from pyqasm.maps.decomposition_rules import DECOMPOSITION_RULES, AppliedQubit, ROTATIONAL_LOOKUP_RULES
from pyqasm.maps.expressions import CONSTANTS_MAP
from pyqasm.maps.gates import BASIS_GATE_MAP


class Decomposer:
    """
    Class to decompose the gates based on the target basis set.
    """

    @classmethod
    def process_gate_statement(cls, gate_name, statement, target_basis_set):
        """Process the gate statement based on the target basis set.

        Args:
            gate_name: The name of the gate to process.
            statement: The statement to process.
            target_basis_set: The target basis set to rebase the module to.

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
            processed_gates_list = cls._get_decomposed_gates(
                decomposition_rules, statement, gate_name
            )
        elif gate_name in {"rx", "ry", "rz"}:
            # Use lookup table if ∅ is pi, pi/2 or pi/4
            rotational_lookup_rules = ROTATIONAL_LOOKUP_RULES[target_basis_set]
            theta = statement.arguments[0].value
            if theta in [CONSTANTS_MAP["pi"], CONSTANTS_MAP["pi"]/2, CONSTANTS_MAP["pi"]/4]:
                gate_name = cls._get_rotational_gate_name(gate_name, theta)
                processed_gates_list = cls._get_decomposed_gates(
                    rotational_lookup_rules, statement, gate_name
                )
            
            # Approximate parameterized gates using Solovay-Kitaev
            # Example -
            # approx_gates = solovay_kitaev_algo(
            #     gate_name, statement.arguments[0].value, accuracy=0.01
            # )
            # return approx_gates
            pass
        else:
            # Raise an error if the gate is not supported in the target basis set
            error = f"Gate '{gate_name}' is not supported in the '{target_basis_set} set'."
            raise RebaseError(error)

        return processed_gates_list

    @classmethod
    def process_branching_statement(cls, branching_statement, target_basis_set):
        """Process the branching statement based on the target basis set.

        Args:
            branching_statement: The branching statement to process.
            target_basis_set: The target basis set to rebase the module to.

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
                if_block.append(cls.process_branching_statement(statement, target_basis_set))
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
                else_block.append(cls.process_branching_statement(statement, target_basis_set))
            else:
                else_block.append(statement)

        return BranchingStatement(
            condition=branching_statement.condition, if_block=if_block, else_block=else_block
        )

    @classmethod
    def _get_decomposed_gates(cls, decomposition_rules, statement, gate):
        """Apply the decomposed gates based on the decomposition rules.

        Args:
            decomposition_rules: The decomposition rules to apply.
            statement: The statement to apply the decomposition rules to.
            gate: The name of the gate to apply the decomposition rules to.

        Returns:
            list: The decomposed gates to be applied.
        """
        decomposed_gates = []

        for rule in decomposition_rules[gate]:
            qubits = cls._get_qubits_for_gate(statement.qubits, rule)
            arguments = [qasm3_ast.FloatLiteral(value=rule["param"])] if "param" in rule else []

            new_gate = qasm3_ast.QuantumGate(
                modifiers=[],
                name=qasm3_ast.Identifier(name=rule["gate"]),
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
    def _get_rotational_gate_name(cls, gate_name, theta):
        theta_string = ""
        if theta == CONSTANTS_MAP["pi"]:
            theta_string = "(pi)"
        elif theta == CONSTANTS_MAP["pi"]/2:
            theta_string = "(pi)/2"
        elif theta == CONSTANTS_MAP["pi"]/4:
            theta_string = "(pi)/4"
            
        return gate_name + theta_string