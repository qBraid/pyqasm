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
Module containing the class for evaluating QASM expressions.

"""

from openqasm3.ast import (
    AngleType,
    BinaryExpression,
    BitstringLiteral,
    BitType,
    BooleanLiteral,
    BoolType,
    Cast,
    DurationLiteral,
    Expression,
    FloatLiteral,
)
from openqasm3.ast import FloatType as Qasm3FloatType
from openqasm3.ast import (
    FunctionCall,
    Identifier,
    ImaginaryLiteral,
    IndexExpression,
    IntegerLiteral,
)
from openqasm3.ast import IntType as Qasm3IntType
from openqasm3.ast import (
    SizeOf,
    Statement,
    StretchType,
    UnaryExpression,
)

from pyqasm.analyzer import Qasm3Analyzer
from pyqasm.elements import Variable
from pyqasm.exceptions import ValidationError, raise_qasm3_error
from pyqasm.maps.expressions import (
    CONSTANTS_MAP,
    FUNCTION_MAP,
    TIME_UNITS_MAP,
    qasm3_expression_op_map,
)
from pyqasm.validator import Qasm3Validator


class Qasm3ExprEvaluator:
    """Class for evaluating QASM3 expressions."""

    visitor_obj = None
    angle_var_in_expr = None

    @classmethod
    def set_visitor_obj(cls, visitor_obj) -> None:
        cls.visitor_obj = visitor_obj

    @classmethod
    def _check_var_in_scope(cls, var_name, expression):
        """Checks if a variable is in scope.

        Args:
            var_name: The name of the variable to check.
            expression: The expression containing the variable.
        Raises:
            ValidationError: If the variable is undefined in the current scope.
        """

        scope_manager = cls.visitor_obj._scope_manager
        var = scope_manager.get_from_global_scope(var_name)
        if not scope_manager.check_in_scope(var_name):
            if var is not None and not var.is_constant:
                raise_qasm3_error(
                    f"Global variable '{var_name}' must be a constant to use it in a local scope.",
                    error_node=expression,
                    span=expression.span,
                )
            raise_qasm3_error(
                f"Undefined identifier '{var_name}' in expression",
                err_type=ValidationError,
                error_node=expression,
                span=expression.span,
            )
        if var and isinstance(var.base_type, AngleType):
            if cls.angle_var_in_expr and cls.angle_var_in_expr != var.base_type.size:
                raise_qasm3_error(
                    "All 'Angle' variables in binary expression must have the same size",
                    error_node=expression,
                    span=expression.span,
                )
            cls.angle_var_in_expr = var.base_type.size

    @classmethod
    def _check_var_constant(cls, var_name, const_expr, expression):
        """Checks if a variable is constant.

        Args:
            var_name: The name of the variable to check.
            const_expr: Whether the expression is a constant.
            expression: The expression containing the variable.

        Raises:
            ValidationError: If the variable is not a constant in the given
                                expression.
        """
        const_var = cls.visitor_obj._scope_manager.get_from_visible_scope(var_name).is_constant
        if const_expr and not const_var:
            raise_qasm3_error(
                f"Expected variable '{var_name}' to be constant in given expression",
                err_type=ValidationError,
                error_node=expression,
                span=expression.span,
            )

    @classmethod
    def _check_var_type(cls, var_name, reqd_type, expression):
        """Check the type of a variable and raise an error if it does not match the
        required type.

        Args:
            var_name: The name of the variable to check.
            reqd_type: The required type of the variable.
            expression: The expression where the variable is used.

        Raises:
            ValidationError: If the variable has an invalid type for the required type.
        """
        var = cls.visitor_obj._scope_manager.get_from_visible_scope(var_name)
        if not Qasm3Validator.validate_variable_type(var, reqd_type):
            raise_qasm3_error(
                message=f"Invalid type '{var.base_type}' of variable '{var_name}' for "
                f"required type {reqd_type}",
                err_type=ValidationError,
                error_node=expression,
                span=expression.span,
            )

    @classmethod
    def _check_var_initialized(cls, var_name, var_value, expression):
        """Checks if a variable is initialized and raises an error if it is not.

        Args:
            var_name (str): The name of the variable.
            var_value: The value of the variable.
            expression: The expression where the variable is used.
        Raises:
            ValidationError: If the variable is uninitialized.
        """

        var = cls.visitor_obj._scope_manager.get_from_visible_scope(var_name)
        if not isinstance(var.base_type, StretchType) and var_value is None:
            raise_qasm3_error(
                f"Uninitialized variable '{var_name}' in expression",
                err_type=ValidationError,
                error_node=expression,
                span=expression.span,
            )

    @classmethod
    def _get_var_value(cls, var_name, indices, expression):
        """Retrieves the value of a variable.

        Args:
            var_name (str): The name of the variable.
            indices (list): The indices of the variable (if it is an array).
            expression (Identifier or Expression): The expression representing the variable.
        Returns:
            var_value: The value of the variable.
        """

        var_value = None
        if isinstance(expression, Identifier):
            var_value = cls.visitor_obj._scope_manager.get_from_visible_scope(var_name).value
        else:
            validated_indices = Qasm3Analyzer.analyze_classical_indices(
                indices, cls.visitor_obj._scope_manager.get_from_visible_scope(var_name), cls
            )
            var_value = Qasm3Analyzer.find_array_element(
                cls.visitor_obj._scope_manager.get_from_visible_scope(var_name).value,
                validated_indices,
            )
        return var_value

    @classmethod
    # pylint: disable-next=too-many-return-statements,too-many-branches,too-many-statements,too-many-locals,too-many-arguments
    def evaluate_expression(  # type: ignore[return]
        cls,
        expression,
        const_expr: bool = False,
        reqd_type=None,
        validate_only: bool = False,
        dt=None,
    ) -> tuple:
        """Evaluate an expression. Scalar types are assigned by value.

        Args:
            expression (Any): The expression to evaluate.
            const_expr (bool): Whether the expression is a constant. Defaults to False.
            reqd_type (Any): The required type of the expression. Defaults to None.
            validate_only (bool): Whether to validate the expression only. Defaults to False.
            dt (float): The time step of the compiler. Defaults to None.

        Returns:
            tuple[Any, list[Statement]] : The result of the evaluation.

        Raises:
            ValidationError: If the expression is not supported.
        """
        statements: list[Statement] = []
        if expression is None:
            return None, []

        def _check_and_return_value(value):
            if validate_only:
                return None, statements
            return value, statements

        def _process_variable(var_name: str, indices=None):
            cls._check_var_in_scope(var_name, expression)
            cls._check_var_constant(var_name, const_expr, expression)
            cls._check_var_type(var_name, reqd_type, expression)
            var_value = cls._get_var_value(var_name, indices, expression)
            Qasm3ExprEvaluator._check_var_initialized(var_name, var_value, expression)
            return _check_and_return_value(var_value)

        def _check_type_size(expression, var_name, var_format, base_type):
            base_size = 1
            if not isinstance(base_type, BoolType):
                initial_size = 1 if isinstance(base_type, BitType) else 32
                try:
                    base_size = (
                        initial_size
                        if not hasattr(base_type, "size") or base_type.size is None
                        else Qasm3ExprEvaluator.evaluate_expression(
                            base_type.size, const_expr=True
                        )[0]
                    )
                except ValidationError as err:
                    raise_qasm3_error(
                        f"Invalid base size for {var_format} '{var_name}'",
                        error_node=expression,
                        span=expression.span,
                        raised_from=err,
                    )
                if not isinstance(base_size, int) or base_size <= 0:
                    raise_qasm3_error(
                        f"Invalid base size '{base_size}' for {var_format} '{var_name}'",
                        error_node=expression,
                        span=expression.span,
                    )
            return base_size

        def _is_external_function_call(expression):
            """Check if an expression is an external function call"""
            return isinstance(expression, FunctionCall) and (
                expression.name.name in cls.visitor_obj._module._extern_functions
            )

        def _get_external_function_return_type(expression):
            """Get the return type of an external function call"""
            if _is_external_function_call(expression):
                return cls.visitor_obj._module._extern_functions[expression.name.name][1]
            return None

        if isinstance(expression, ImaginaryLiteral):
            return _check_and_return_value(expression.value * 1j)

        if isinstance(expression, Identifier):
            var_name = expression.name
            if var_name in CONSTANTS_MAP:
                if not reqd_type or reqd_type in (Qasm3FloatType, AngleType):
                    return _check_and_return_value(CONSTANTS_MAP[var_name])
                raise_qasm3_error(
                    f"Constant '{var_name}' not allowed in non-float expression",
                    err_type=ValidationError,
                    error_node=expression,
                    span=expression.span,
                )
            return _process_variable(var_name)

        if isinstance(expression, IndexExpression):
            var_name, indices = Qasm3Analyzer.analyze_index_expression(expression)
            return _process_variable(var_name, indices)

        if isinstance(expression, SizeOf):
            target = expression.target
            index = expression.index

            if isinstance(target, Identifier):
                var_name = target.name
                cls._check_var_in_scope(var_name, expression)
                assert cls.visitor_obj
                dimensions = cls.visitor_obj._scope_manager.get_from_visible_scope(var_name).dims
            else:
                raise_qasm3_error(
                    message=f"Unsupported target type '{type(target)}' for sizeof expression",
                    err_type=ValidationError,
                    error_node=expression,
                    span=expression.span,
                )

            if dimensions is None or len(dimensions) == 0:
                raise_qasm3_error(
                    message=f"Invalid sizeof usage, variable '{var_name}' is not an array.",
                    err_type=ValidationError,
                    error_node=expression,
                    span=expression.span,
                )

            if index is None:
                return _check_and_return_value(dimensions[0])  # return first dimension

            index, stmts = cls.evaluate_expression(index, const_expr, reqd_type=Qasm3IntType)
            statements.extend(stmts)

            assert index is not None and isinstance(index, int)
            if index < 0 or index >= len(dimensions):
                raise_qasm3_error(
                    f"Index {index} out of bounds for array '{var_name}' with "
                    f"{len(dimensions)} dimensions",
                    err_type=ValidationError,
                    error_node=expression,
                    span=expression.span,
                )
            return _check_and_return_value(dimensions[index])

        if isinstance(expression, (BooleanLiteral, IntegerLiteral, FloatLiteral)):
            if reqd_type:
                if reqd_type == BoolType and isinstance(expression, BooleanLiteral):
                    return _check_and_return_value(expression.value)
                if reqd_type == Qasm3IntType and isinstance(expression, IntegerLiteral):
                    return _check_and_return_value(expression.value)
                if reqd_type == Qasm3FloatType and isinstance(expression, FloatLiteral):
                    return _check_and_return_value(expression.value)
                if reqd_type == AngleType:
                    return _check_and_return_value(expression.value)
                raise_qasm3_error(
                    f"Invalid value {expression.value} with type {type(expression)} "
                    f"for required type {reqd_type}",
                    err_type=ValidationError,
                    error_node=expression,
                    span=expression.span,
                )
            return _check_and_return_value(expression.value)

        if isinstance(expression, BitstringLiteral):
            return _check_and_return_value(format(expression.value, f"0{expression.width}b"))

        if isinstance(expression, DurationLiteral):
            unit_name = expression.unit.name
            if dt:
                if unit_name == "dt":
                    return _check_and_return_value(expression.value * dt)
                return _check_and_return_value(
                    (expression.value * TIME_UNITS_MAP[unit_name]["s"]) / dt
                )
            if unit_name == "dt":
                return _check_and_return_value(expression.value)
            return _check_and_return_value(expression.value * TIME_UNITS_MAP[unit_name]["ns"])

        if isinstance(expression, UnaryExpression):
            if validate_only:
                if isinstance(expression.expression, Cast):
                    return cls.evaluate_expression(
                        expression.expression, const_expr, reqd_type, validate_only
                    )
                # Check for external function in validate_only mode
                return_type = _get_external_function_return_type(expression.expression)
                if return_type:
                    return (return_type, statements)
                return (None, [])

            operand, returned_stats = cls.evaluate_expression(
                expression.expression, const_expr, reqd_type
            )

            # Handle external function replacement
            if _is_external_function_call(expression.expression):
                expression.expression = returned_stats[0]
                return _check_and_return_value(None)

            if expression.op.name == "~" and not isinstance(operand, int):
                raise_qasm3_error(
                    f"Unsupported expression type '{type(operand)}' in ~ operation",
                    err_type=ValidationError,
                    error_node=expression,
                    span=expression.span,
                )
            op_name = "UMINUS" if expression.op.name == "-" else expression.op.name
            statements.extend(returned_stats)
            return _check_and_return_value(qasm3_expression_op_map(op_name, operand))

        if isinstance(expression, BinaryExpression):
            if validate_only:
                if isinstance(expression.lhs, Cast) and isinstance(expression.rhs, Cast):
                    return (None, statements)

                _lhs, _lhs_stmts = cls.evaluate_expression(
                    expression.lhs,
                    const_expr,
                    reqd_type,
                    validate_only,
                )
                _rhs, _rhs_stmts = cls.evaluate_expression(
                    expression.rhs,
                    const_expr,
                    reqd_type,
                    validate_only,
                )

                if isinstance(expression.lhs, Cast):
                    return (_lhs, _lhs_stmts)
                if isinstance(expression.rhs, Cast):
                    return (_rhs, _rhs_stmts)

                if type(reqd_type) is type(AngleType) and cls.angle_var_in_expr:
                    _var_type = AngleType(cls.angle_var_in_expr)
                    cls.angle_var_in_expr = None
                    return (_var_type, statements)

                _lhs_return_type = None
                _rhs_return_type = None
                # Check for external functions in both operands
                _lhs_return_type = _get_external_function_return_type(expression.lhs)
                _rhs_return_type = _get_external_function_return_type(expression.rhs)

                if _lhs_return_type and _rhs_return_type:
                    if _lhs_return_type != _rhs_return_type:
                        raise_qasm3_error(
                            f"extern function return type mismatch in binary expression: "
                            f"{type(_lhs_return_type).__name__} and "
                            f"{type(_rhs_return_type).__name__}",
                            err_type=ValidationError,
                            error_node=expression,
                            span=expression.span,
                        )
                else:
                    if _lhs_return_type:
                        return (_lhs_return_type, statements)
                    if _rhs_return_type:
                        return (_rhs_return_type, statements)

                return (None, statements)

            lhs_value, lhs_statements = cls.evaluate_expression(
                expression.lhs, const_expr, reqd_type
            )
            # Handle external function replacement for lhs
            lhs_extern_function = False
            if _is_external_function_call(expression.lhs):
                expression.lhs = lhs_statements[0]
                lhs_extern_function = True
            statements.extend(lhs_statements)

            rhs_value, rhs_statements = cls.evaluate_expression(
                expression.rhs, const_expr, reqd_type
            )
            # Handle external function replacement for rhs
            rhs_extern_function = False
            if _is_external_function_call(expression.rhs):
                expression.rhs = rhs_statements[0]
                rhs_extern_function = True
            if lhs_extern_function or rhs_extern_function:
                return (None, [])

            statements.extend(rhs_statements)
            return _check_and_return_value(
                qasm3_expression_op_map(expression.op.name, lhs_value, rhs_value)
            )

        if isinstance(expression, FunctionCall):
            # function will not return a reqd / const type
            # Reference : https://openqasm.com/language/types.html#compile-time-constants, para: 5
            if validate_only:
                return_type = _get_external_function_return_type(expression)
                if return_type:
                    return (return_type, statements)
                return (None, statements)

            if expression.name.name in FUNCTION_MAP:
                _val, _ = cls.evaluate_expression(
                    expression.arguments[0], const_expr, reqd_type, validate_only
                )
                _val = FUNCTION_MAP[expression.name.name](_val)  # type: ignore
                return _check_and_return_value(_val)

            ret_value, ret_stmts = cls.visitor_obj._visit_function_call(expression)  # type: ignore
            statements.extend(ret_stmts)
            return _check_and_return_value(ret_value)

        if isinstance(expression, Cast):
            if validate_only:
                return (expression.type, statements)

            var_name = ""
            if isinstance(expression.argument, Identifier):
                var_name = expression.argument.name

            var_value, cast_stmts = cls.evaluate_expression(
                expression=expression.argument, const_expr=const_expr
            )

            var_format = "variable"
            if var_name == "":
                var_name = f"{var_value}"
                var_format = "value"

            cast_type_size = _check_type_size(expression, var_name, var_format, expression.type)
            variable = Variable(
                name=var_name,
                base_type=expression.type,
                base_size=cast_type_size,
                dims=[],
                value=var_value,
                is_constant=const_expr,
                span=expression.span,
            )
            cast_var_value = Qasm3Validator.validate_variable_assignment_value(
                variable, var_value, expression
            )
            statements.extend(cast_stmts)
            return _check_and_return_value(cast_var_value)

        raise_qasm3_error(
            f"Unsupported expression type {type(expression)}",
            err_type=ValidationError,
            error_node=expression,
            span=expression.span,
        )

    @classmethod
    def classical_register_in_expr(cls, expr: Expression) -> bool:
        """
        Check if a classical register is present in the expression

        Args:
            expr (Expression): The expression to check

        Returns:
            bool: True if a classical register is present, False otherwise
        """
        if isinstance(expr, Identifier):
            return expr.name in cls.visitor_obj._global_creg_size_map  # type: ignore
        if isinstance(expr, IndexExpression):
            var_name, _ = Qasm3Analyzer.analyze_index_expression(expr)
            return var_name in cls.visitor_obj._global_creg_size_map  # type: ignore
        if isinstance(expr, BinaryExpression):
            return cls.classical_register_in_expr(expr.lhs) or cls.classical_register_in_expr(
                expr.rhs
            )
        if isinstance(expr, UnaryExpression):
            return cls.classical_register_in_expr(expr.expression)
        return False
