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
Module containing the class for validating QASM3 subroutines.

"""
from typing import Optional

from openqasm3.ast import (
    AccessControl,
    ArrayReferenceType,
    Identifier,
    IndexExpression,
    IntType,
    QASMNode,
    QubitDeclaration,
)
from openqasm3.printer import dumps

from pyqasm.analyzer import Qasm3Analyzer
from pyqasm.elements import Variable
from pyqasm.exceptions import ValidationError, raise_qasm3_error
from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.transformer import Qasm3Transformer
from pyqasm.validator import Qasm3Validator


class Qasm3SubroutineProcessor:
    """Class for processing QASM3 subroutines."""

    visitor_obj = None

    @classmethod
    def set_visitor_obj(cls, visitor_obj) -> None:
        """Set the visitor object for the class.

        Args:
            visitor_obj (QasmVisitor): The visitor object to set.
        """
        cls.visitor_obj = visitor_obj

    @staticmethod
    def get_fn_actual_arg_name(actual_arg: Identifier | IndexExpression) -> Optional[str]:
        """Get the name of the actual argument passed to a function.

        Args:
            actual_arg (Identifier | IndexExpression): The actual argument passed to the
                                                             function.

        Returns:
            Optional[str]: The name of the actual argument.
        """
        actual_arg_name = None
        if isinstance(actual_arg, Identifier):
            actual_arg_name = actual_arg.name
        elif isinstance(actual_arg, IndexExpression):
            if isinstance(actual_arg.collection, Identifier):
                actual_arg_name = actual_arg.collection.name
            else:
                actual_arg_name = (
                    actual_arg.collection.collection.name  # type: ignore[attr-defined]
                )
        return actual_arg_name

    @classmethod
    def process_classical_arg(cls, formal_arg, actual_arg, fn_name, fn_call):
        """Process the classical argument for a function call.

        Args:
            formal_arg (FormalArgument): The formal argument of the function.
            actual_arg (ActualArgument): The actual argument passed to the function.
            fn_name (str): The name of the function.
            span (Span): The span of the function call.

        Returns:
            Variable: The variable object for the formal argument.
        """
        actual_arg_name = Qasm3SubroutineProcessor.get_fn_actual_arg_name(actual_arg)

        if isinstance(formal_arg.type, ArrayReferenceType):
            return cls._process_classical_arg_by_reference(
                formal_arg, actual_arg, actual_arg_name, fn_name, fn_call
            )
        return cls._process_classical_arg_by_value(
            formal_arg, actual_arg, actual_arg_name, fn_name, fn_call
        )

    @classmethod  # pylint: disable-next=too-many-arguments
    def _process_classical_arg_by_value(
        cls, formal_arg, actual_arg, actual_arg_name, fn_name, fn_call
    ):
        """
        Process the classical argument for a function call.

        Args:
            formal_arg (FormalArgument): The formal argument of the function.
            actual_arg (ActualArgument): The actual argument passed to the function.
            actual_arg_name (str): The name of the actual argument.
            fn_name (str): The name of the function.
            span (Span): The span of the function call.

        Raises:
            ValidationError: If the actual argument is a qubit register instead
                                of a classical argument.
            ValidationError: If the actual argument is an undefined variable.
        """
        # 1. variable mapping is equivalent to declaring the variable
        #     with the formal argument name and doing classical assignment
        #     in the scope of the function

        fn_defn = cls.visitor_obj._subroutine_defns.get(fn_name)
        formal_args_desc = " , ".join(dumps(arg, indent="    ") for arg in fn_defn.arguments)

        if actual_arg_name:  # actual arg is a variable not literal
            if actual_arg_name in cls.visitor_obj._global_qreg_size_map:
                formal_args_desc = " , ".join(
                    dumps(arg, indent="    ") for arg in fn_defn.arguments
                )
                raise_qasm3_error(
                    f"Expecting classical argument for '{formal_arg.name.name}'. "
                    f"Qubit register '{actual_arg_name}' found for function '{fn_name}'\n"
                    f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                    error_node=fn_call,
                    span=fn_call.span,
                )

            # 2. as we have pushed the scope for fn, we need to check in parent
            #    scope for argument validation
            if not cls.visitor_obj._check_in_scope(actual_arg_name):
                raise_qasm3_error(
                    f"Undefined variable '{actual_arg_name}' used"
                    f" for function call '{fn_name}'\n"
                    f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                    error_node=fn_call,
                    span=fn_call.span,
                )
        actual_arg_value = Qasm3ExprEvaluator.evaluate_expression(actual_arg)[0]

        # save this value to be updated later in scope
        return Variable(
            name=formal_arg.name.name,
            base_type=formal_arg.type,
            base_size=Qasm3ExprEvaluator.evaluate_expression(formal_arg.type.size)[0],
            dims=None,
            value=actual_arg_value,
            is_constant=False,
            span=fn_call.span,
        )

    @classmethod  # pylint: disable-next=too-many-arguments,too-many-locals,too-many-branches
    def _process_classical_arg_by_reference(
        cls, formal_arg, actual_arg, actual_arg_name, fn_name, fn_call
    ):
        """Process the classical args by reference in the QASM3 visitor.
            Currently being used for array references only.

        Args:
            formal_arg (Qasm3Expression): The formal argument of the function.
            actual_arg (Qasm3Expression): The actual argument passed to the function.
            actual_arg_name (str): The name of the actual argument.
            fn_name (str): The name of the function.
            span (Span): The span of the function call.

        Raises:
            ValidationError: If the actual argument is -
                                - not an array.
                                - an undefined variable.
                                - a qubit register.
                                - a literal.
                                - having type mismatch with the formal argument.
        """

        formal_arg_base_size = Qasm3ExprEvaluator.evaluate_expression(
            formal_arg.type.base_type.size
        )[0]
        fn_defn = cls.visitor_obj._subroutine_defns.get(fn_name)

        array_expected_type_msg = (
            "Expecting type 'array["
            f"{formal_arg.type.base_type.__class__.__name__.lower().removesuffix('type')}"
            f"[{formal_arg_base_size}],...]' for '{formal_arg.name.name}'"
            f" in function '{fn_name}'. "
        )

        formal_args_desc = " , ".join(dumps(arg, indent="    ") for arg in fn_defn.arguments)

        if actual_arg_name is None:
            raise_qasm3_error(
                array_expected_type_msg
                + f"Literal '{Qasm3ExprEvaluator.evaluate_expression(actual_arg)[0]}' "
                + "found in function call\n"
                + f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                error_node=fn_call,
                span=fn_call.span,
            )

        if actual_arg_name in cls.visitor_obj._global_qreg_size_map:
            raise_qasm3_error(
                array_expected_type_msg
                + f"Qubit register '{actual_arg_name}' found for function call\n"
                + f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                error_node=fn_call,
                span=fn_call.span,
            )

        # verify actual argument is defined in the parent scope of function call
        if not cls.visitor_obj._check_in_scope(actual_arg_name):
            raise_qasm3_error(
                f"Undefined variable '{actual_arg_name}' used for function call '{fn_name}'\n"
                + f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                error_node=fn_call,
                span=fn_call.span,
            )

        array_reference = cls.visitor_obj._get_from_visible_scope(actual_arg_name)
        actual_type_string = Qasm3Transformer.get_type_string(array_reference)

        # ensure that actual argument is an array
        if not array_reference.dims:
            raise_qasm3_error(
                array_expected_type_msg
                + f"Variable '{actual_arg_name}' has type '{actual_type_string}'\n"
                + f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                error_node=fn_call,
                span=fn_call.span,
            )

        # The base types of the elements in array should match
        actual_arg_type = array_reference.base_type
        actual_arg_size = array_reference.base_size

        if formal_arg.type.base_type != actual_arg_type or formal_arg_base_size != actual_arg_size:
            raise_qasm3_error(
                array_expected_type_msg
                + f"Variable '{actual_arg_name}' has type '{actual_type_string}'\n"
                + f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                error_node=fn_call,
                span=fn_call.span,
            )

        # The dimensions passed in the formal arg should be
        # within limits of the actual argument

        # need to ensure that we have a positive integer as dimension
        actual_dimensions = array_reference.dims
        formal_dimensions_raw = formal_arg.type.dimensions
        # 1. Either we  will have #dim = <<some integer>>
        if not isinstance(formal_dimensions_raw, list):
            try:
                num_formal_dimensions = Qasm3ExprEvaluator.evaluate_expression(
                    formal_dimensions_raw, reqd_type=IntType, const_expr=True
                )[0]
            except ValidationError as err:
                raise_qasm3_error(
                    f"Invalid dimension size {dumps(formal_dimensions_raw)} "
                    f"for '{formal_arg.name.name}' in function '{fn_name}'\n"
                    f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                    error_node=fn_call,
                    span=fn_call.span,
                    raised_from=err,
                )
        # 2. or we will have a list of the dimensions in the formal arg
        else:
            num_formal_dimensions = len(formal_dimensions_raw)

        if num_formal_dimensions <= 0 or num_formal_dimensions > len(actual_dimensions):
            error_msg = (
                f"Invalid number of dimensions {num_formal_dimensions}"
                if num_formal_dimensions <= 0
                else f"Dimension mismatch. Expected {num_formal_dimensions} dimensions but "
                f"variable '{actual_arg_name}' has {len(actual_dimensions)}"
            )
            raise_qasm3_error(
                f"{error_msg} for '{formal_arg.name.name}' in function '{fn_name}'\n"
                f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                error_node=fn_call,
                span=fn_call.span,
            )
        formal_dimensions = []

        # we need to ensure that the dimensions are within the limits AND valid integers
        if not isinstance(formal_dimensions_raw, list):
            # the case when we have #dim identifier
            formal_dimensions = actual_dimensions[:num_formal_dimensions]
        else:
            for idx, (formal_dim, actual_dim) in enumerate(
                zip(formal_dimensions_raw, actual_dimensions)
            ):
                try:
                    formal_dim = Qasm3ExprEvaluator.evaluate_expression(
                        formal_dim, reqd_type=IntType, const_expr=True
                    )[0]
                    if formal_dim <= 0 or formal_dim > actual_dim:
                        error_msg = (
                            f"Invalid dimension size {formal_dim}"
                            if formal_dim <= 0
                            else f"Dimension mismatch. Expected dimension {idx} with "
                            f"size >= {formal_dim} but got {actual_dim}"
                        )
                        raise_qasm3_error(
                            f"{error_msg} for '{formal_arg.name.name}' in function '{fn_name}'\n"
                            f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                            error_node=fn_call,
                            span=fn_call.span,
                        )
                    formal_dimensions.append(formal_dim)
                except ValidationError as err:
                    formal_arg_str = (
                        dumps(formal_dim) if isinstance(formal_dim, QASMNode) else formal_dim
                    )
                    raise_qasm3_error(
                        f"Invalid dimension size {formal_arg_str}"
                        f" for '{formal_arg.name.name}' in function '{fn_name}'\n"
                        f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                        error_node=fn_call,
                        span=fn_call.span,
                        raised_from=err,
                    )

        readonly_arr = formal_arg.access == AccessControl.readonly
        actual_array_view = array_reference.value
        if isinstance(actual_arg, IndexExpression):
            _, actual_indices = Qasm3Analyzer.analyze_index_expression(actual_arg)
            actual_indices = Qasm3Analyzer.analyze_classical_indices(
                actual_indices, array_reference, Qasm3ExprEvaluator
            )
            actual_array_view = Qasm3Analyzer.find_array_element(
                array_reference.value, actual_indices
            )

        return Variable(
            name=formal_arg.name.name,
            base_type=formal_arg.type.base_type,
            base_size=formal_arg_base_size,
            dims=formal_dimensions,
            value=actual_array_view,  # this is the VIEW of the actual array
            readonly=readonly_arr,
            span=fn_call.span,
        )

    @classmethod  # pylint: disable-next=too-many-arguments
    def process_quantum_arg(  # pylint: disable=too-many-locals
        cls,
        formal_arg,
        actual_arg,
        formal_qreg_size_map,
        duplicate_qubit_map,
        qubit_transform_map,
        fn_name,
        fn_call,
    ):
        """
        Process a quantum argument in the QASM3 visitor.

        Args:
            formal_arg (Qasm3Expression): The formal argument in the function signature.
            actual_arg (Qasm3Expression): The actual argument passed to the function.
            formal_qreg_size_map (dict): The map of formal quantum register sizes.
            duplicate_qubit_map (dict): The map of duplicate qubit registers.
            qubit_transform_map (dict): The map of qubit register transformations.
            fn_name (str): The name of the function.
            fn_call (qasm3_ast.FunctionCall) : The function call node in the AST.

        Returns:
            list: The list of actual qubit ids.

        Raises:
            ValidationError: If there is a mismatch in the quantum register size or
                                  if the actual argument is not a qubit register.

        """
        actual_arg_name = Qasm3SubroutineProcessor.get_fn_actual_arg_name(actual_arg)
        formal_reg_name = formal_arg.name.name
        formal_qubit_size = Qasm3ExprEvaluator.evaluate_expression(
            formal_arg.size, reqd_type=IntType, const_expr=True
        )[0]
        if formal_qubit_size is None:
            formal_qubit_size = 1

        fn_defn = cls.visitor_obj._subroutine_defns.get(fn_name)

        if formal_qubit_size <= 0:
            raise_qasm3_error(
                f"Invalid qubit size '{formal_qubit_size}' for variable '{formal_reg_name}'"
                f" in function '{fn_name}'",
                error_node=fn_defn.arguments,
                span=formal_arg.span,
            )
        formal_qreg_size_map[formal_reg_name] = formal_qubit_size

        # we expect that actual arg is qubit type only
        # note that we ONLY check in global scope as
        # we always map the qubit arguments to the global scope
        if actual_arg_name not in cls.visitor_obj._global_qreg_size_map:
            # Check if the actual argument is a qubit register
            is_literal = actual_arg_name is None
            arg_desc = (
                f"Literal '{Qasm3ExprEvaluator.evaluate_expression(actual_arg)[0]}' "
                if is_literal
                else f"Qubit register '{actual_arg_name}' not "
            )
            formal_args_desc = " , ".join(dumps(arg, indent="    ") for arg in fn_defn.arguments)
            raise_qasm3_error(
                f"Expecting qubit argument for '{formal_reg_name}'. "
                f"{arg_desc}found for function '{fn_name}'\n"
                f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                error_node=fn_call,
                span=fn_call.span,
            )
        # cls.visitor_obj._label_scope_level[cls.visitor_obj._curr_scope].add(formal_reg_name)

        actual_qids, actual_qubits_size = Qasm3Transformer.get_target_qubits(
            actual_arg, cls.visitor_obj._global_qreg_size_map, actual_arg_name
        )

        if formal_qubit_size != actual_qubits_size:
            formal_args_desc = " , ".join(dumps(arg, indent="    ") for arg in fn_defn.arguments)
            raise_qasm3_error(
                f"Qubit register size mismatch for function '{fn_name}'. "
                f"Expected {formal_qubit_size} qubits in variable '{formal_reg_name}' "
                f"but got {actual_qubits_size}\n"
                f"\nUsage: {fn_name} ( {formal_args_desc} )\n",
                error_node=fn_call,
                span=fn_call.span,
            )

        if not Qasm3Validator.validate_unique_qubits(
            duplicate_qubit_map, actual_arg_name, actual_qids
        ):
            raise_qasm3_error(
                f"Duplicate qubit argument for register '{actual_arg_name}' "
                f"in function call for '{fn_name}'",
                error_node=fn_call,
                span=fn_call.span,
            )

        for idx, qid in enumerate(actual_qids):
            qubit_transform_map[(formal_reg_name, idx)] = (actual_arg_name, qid)

        return Variable(
            name=formal_reg_name,
            base_type=QubitDeclaration,
            base_size=formal_qubit_size,
            dims=None,
            value=None,
            is_constant=False,
            span=fn_call.span,
        )
