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

# pylint: disable=all
# mypy: disable-error-code=union-attr
"""
Module defining OpenPulse Visitor.

"""
import logging
from typing import Any

import openpulse.ast as pulse_ast

from pyqasm.elements import Frame
from pyqasm.exceptions import (
    raise_qasm3_error,
)

logger = logging.getLogger(__name__)
logger.propagate = False


class OpenPulseVisitor:
    """A visitor for basic OpenPulse program elements.

    This class is designed to traverse and interact with elements in an OpenPulse program.

    Args:
        visitor: The QasmVisitor instance that provides scope and context information.
        check_only: If True, only check the program without executing it. Defaults to False.
    """

    def __init__(
        self,
        qasm_visitor,
        check_only: bool = False,
    ):
        self._qasm_visitor = qasm_visitor
        self._module = qasm_visitor._module
        self._check_only: bool = check_only
        self._frames = list[Frame]
        self._ports = list[pulse_ast.PortType]
        self._waveforms = list[pulse_ast.WaveformType]
        self._is_def_cal: bool = False

    def _visit_barrier(self, barrier: pulse_ast.QuantumBarrier) -> list[pulse_ast.QuantumBarrier]:
        """Visit a barrier statement element.

        Args:
            statement (pulse_ast.QuantumBarrier): The barrier statement to visit.

        Returns:
            None
        """
        if barrier.qubits:
            print("TODO")
            for frm in barrier.qubits:
                print(frm, "TODO")
                # check frame in global scope

        return []

    def _visit_classical_declaration(
        self, statement: pulse_ast.ClassicalDeclaration
    ) -> list[pulse_ast.Statement]:
        """Visit a classical operation element.

        Args:
            statement (ClassicalType): The classical operation to visit.

        Returns:
            None
        """

        if isinstance(statement.type, pulse_ast.PortType):
            print("TODO")
            # check if identifier already exists and not empty
            # create a port to qubit mapping in global scope (further-use)

        if isinstance(statement.type, pulse_ast.FrameType):
            print("TODO")
            # check if identifier already exists and not empty

            if statement.init_expression:
                print("TODO")
                frame_args = statement.init_expression.arguments
                if not 3 <= len(frame_args) <= 4:
                    print("ERROR")
                new_frame = statement.init_expression.name.name
                if new_frame != "newframe":
                    print("ERROR")

                # can be moved to function
                port_arg = frame_args[0]
                if not isinstance(port_arg, pulse_ast.Identifier):
                    print("ERROR")
                else:
                    print("TODO")
                # check if identifier already exists in global scope

                freq_arg = frame_args[1]
                if isinstance(freq_arg, pulse_ast.Identifier):
                    print("TODO")
                    # evaluate expression
                    # store as class level value using frame class
                elif isinstance(freq_arg, float):
                    print("TODO")
                    # store as class level value using frame class
                else:
                    print("ERROR")

                phase_arg = frame_args[2]
                if isinstance(phase_arg, pulse_ast.Identifier):
                    print("TODO")
                    # evaluate expression
                    # store as class level value using frame class
                elif isinstance(phase_arg, pulse_ast.AngleType):
                    print("TODO")
                    # store as class level value using frame class
                else:
                    print("ERROR")

                if len(frame_args) == 4:
                    time_arg = frame_args[3]
                    if isinstance(time_arg, pulse_ast.Identifier):
                        print("TODO")
                        # evaluate expression
                        # store as class level value using frame class
                    elif isinstance(time_arg, pulse_ast.DurationType):
                        print("TODO")
                        # store as class level value using frame class
                    else:
                        print("ERROR")

                # all this data can access through class level frame object
                # Frame(frame_name, freq, pulse, time)

        if isinstance(statement.type, pulse_ast.WaveformType):
            print("TODO")
            if statement.init_expression:
                id_func_name = statement.init_expression.name.name
                if id_func_name == "gaussian":
                    wave_form_args = statement.init_expression.arguments
                    if len(wave_form_args) == 3:
                        amp_arg = wave_form_args[0]
                        if isinstance(amp_arg, pulse_ast.ComplexType):
                            print("TODO")
                        elif isinstance(amp_arg, pulse_ast.Identifier):
                            print("TODO")
                        else:
                            print("ERROR")
                        duration_arg = wave_form_args[1]
                        if isinstance(duration_arg, pulse_ast.DurationType):
                            print("TODO")
                        elif isinstance(duration_arg, pulse_ast.Identifier):
                            print("TODO")
                        else:
                            print("ERROR")
                        std_deviation_arg = wave_form_args[2]
                        if isinstance(std_deviation_arg, pulse_ast.DurationType):
                            print("TODO")
                        elif isinstance(std_deviation_arg, pulse_ast.Identifier):
                            print("TODO")
                        else:
                            print("ERROR")
                    else:
                        print("ERROR")

                if id_func_name == "sech":
                    print("TODO")
                if id_func_name == "gaussian_square":
                    print("TODO")
                if id_func_name == "drag":
                    print("TODO")
                if id_func_name == "constant":
                    print("TODO")
                if id_func_name == "sine":
                    print("TODO")
                if id_func_name == "mix":
                    print("TODO")
                if id_func_name == "sum":
                    print("TODO")
                if id_func_name == "phase_shift":
                    print("TODO")
                if id_func_name == "scale":
                    print("TODO")

                ## Add all waveforms to global scope

        if self._check_only:
            return []

        return []

    def _visit_function_call(
        self, statement: pulse_ast.FunctionCall
    ) -> tuple[Any, list[pulse_ast.Statement]]:
        """Visit a function call element.

        Args:
            statement (pulse_ast.FunctionCall): The function call to visit.
        Returns:
            None

        """
        # evaluate expressions to get name
        if statement.name.name == "set_phase":
            stmt_args = statement.arguments
            if len(stmt_args) == 2:
                frame_arg = stmt_args[0]
                if isinstance(frame_arg, pulse_ast.Identifier):
                    print("TODO")
                    # get frame object from global scope
                else:
                    print("ERROR")

                angle_arg = stmt_args[1]
                if isinstance(angle_arg, pulse_ast.Identifier):
                    print("TODO")
                    # evaluate expression to get value
                elif isinstance(angle_arg, pulse_ast.AngleType):
                    print("TODO")
                else:
                    print("ERROR")

            # update frame.phase

            else:
                print("ERROR")
        if statement.name.name == "get_phase":
            print("TODO")
        if statement.name.name == "shift_phase":
            print("TODO")
        if statement.name.name == "set_frequency":
            print("TODO")
        if statement.name.name == "get_frequency":
            print("TODO")
        if statement.name.name == "shift_frequency":
            print("TODO")
        if statement.name.name == "play":
            print("TODO")
            if not self._is_def_cal:
                print("ERROR")
            play_args = statement.arguments
            if len(play_args) == 2:
                frame_arg = play_args[0]
                if isinstance(frame_arg, pulse_ast.Identifier):
                    print("TODO")
                    # check if frame declared and exists in global scope
                else:
                    print("ERROR")

                wave_form_arg = play_args[1]
                if isinstance(wave_form_arg, pulse_ast.Identifier):
                    print("TODO")
                    # check if frame declared and exists in global scope
                elif isinstance(wave_form_arg, pulse_ast.WaveformType):
                    print("TODO")
                    # evaluate expression
                else:
                    print("ERROR")

            else:
                print("ERROR")

        ## capture command update waveform
        if statement.name.name == "capture_v0 ":
            print("TODO")
        if statement.name.name == "capture_v1 ":
            print("TODO")
        if statement.name.name == "capture_v2 ":
            print("TODO")
        if statement.name.name == "capture_v3 ":
            print("TODO")
        if statement.name.name == "capture_v4 ":
            print("TODO")

        if self._check_only:
            return 0, []

        return 0, []

    def _visit_delay_instruction(
        self, statement: pulse_ast.DelayInstruction
    ) -> list[pulse_ast.Statement]:
        """Visit a delay instruction statement.

        Args:
            statement (pulse_ast.DelayInstruction): The delay instruction statement to visit.
        Returns:
            None
        """
        if isinstance(statement.duration, pulse_ast.DurationLiteral):
            print("TODO")
            # evaluate expression
        elif isinstance(statement.duration, pulse_ast.DurationType):
            print("TODO")
            # evaluate expression
        else:
            print("ERROR")

        if statement.qubits:
            print("TODO")
            # evaluate expression
            # check if frame exists in global scope
        else:
            print("ERROR")

        if self._check_only:
            return []

        return []

    def visit_statement(self, statement: pulse_ast.Statement) -> list[pulse_ast.Statement]:
        """Visit a statement element.

        Args:
            statement (pulse_ast.Statement): The statement to visit.

        Returns:
            None
        """
        logger.debug("Visiting statement '%s'", str(statement))
        result = []
        visit_map = {
            pulse_ast.QuantumBarrier: self._visit_barrier,
            pulse_ast.ClassicalDeclaration: self._visit_classical_declaration,
            pulse_ast.ExpressionStatement: lambda x: self._visit_function_call(x.expression),
            pulse_ast.DelayInstruction: self._visit_delay_instruction,
        }

        visitor_function = visit_map.get(type(statement))

        if visitor_function:
            if isinstance(statement, pulse_ast.ExpressionStatement):
                # these return a tuple of return value and list of statements
                _, ret_stmts = visitor_function(statement)  # type: ignore[operator]
                result.extend(ret_stmts)
            else:
                result.extend(visitor_function(statement))  # type: ignore[operator]
        else:
            raise_qasm3_error(
                f"Unsupported statement of type {type(statement)}",
                error_node=statement,
                span=statement.span,
            )
        return result

    def visit_basic_block(
        self,
        stmt_list: list[pulse_ast.Statement],
        is_def_cal: bool,
    ) -> list[pulse_ast.Statement]:
        """Visit a basic block of statements.

        Args:
            stmt_list (list[pulse_ast.Statement]): The list of statements to visit.
            is_def_cal (bool): is the given statements from def_cal block.

        Returns:
            list[pulse_ast.Statement]: The list of unrolled statements.
        """
        result = []
        self._is_def_cal = is_def_cal
        for stmt in stmt_list:
            result.extend(self.visit_statement(stmt))
        return result
