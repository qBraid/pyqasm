# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

"""
Module containing the class for evaluating QASM expressions.

"""

from openqasm3.ast import (
    BinaryExpression,
    BooleanLiteral,
    BoolType,
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
from openqasm3.ast import SizeOf, Statement, UnaryExpression

from pyqasm.analyzer import Qasm3Analyzer
from pyqasm.exceptions import ValidationError, raise_qasm3_error
from pyqasm.maps import CONSTANTS_MAP, qasm3_expression_op_map
from pyqasm.validator import Qasm3Validator


class Qasm3ExprEvaluator:
    """Class for evaluating QASM3 expressions."""

    visitor_obj = None

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

        if not cls.visitor_obj._check_in_scope(var_name):
            raise_qasm3_error(
                f"Undefined identifier {var_name} in expression",
                ValidationError,
                expression.span,
            )

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
        const_var = cls.visitor_obj._get_from_visible_scope(var_name).is_constant
        if const_expr and not const_var:
            raise_qasm3_error(
                f"Variable '{var_name}' is not a constant in given expression",
                ValidationError,
                expression.span,
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

        if not Qasm3Validator.validate_variable_type(
            cls.visitor_obj._get_from_visible_scope(var_name), reqd_type
        ):
            raise_qasm3_error(
                f"Invalid type of variable {var_name} for required type {reqd_type}",
                ValidationError,
                expression.span,
            )

    @staticmethod
    def _check_var_initialized(var_name, var_value, expression):
        """Checks if a variable is initialized and raises an error if it is not.

        Args:
            var_name (str): The name of the variable.
            var_value: The value of the variable.
            expression: The expression where the variable is used.
        Raises:
            ValidationError: If the variable is uninitialized.
        """

        if var_value is None:
            raise_qasm3_error(
                f"Uninitialized variable {var_name} in expression",
                ValidationError,
                expression.span,
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
            var_value = cls.visitor_obj._get_from_visible_scope(var_name).value
        else:
            validated_indices = Qasm3Analyzer.analyze_classical_indices(
                indices, cls.visitor_obj._get_from_visible_scope(var_name), cls
            )
            var_value = Qasm3Analyzer.find_array_element(
                cls.visitor_obj._get_from_visible_scope(var_name).value, validated_indices
            )
        return var_value

    @classmethod
    # pylint: disable-next=too-many-return-statements,too-many-branches,too-many-statements,too-many-locals
    def evaluate_expression(  # type: ignore[return]
        cls, expression, const_expr: bool = False, reqd_type=None, validate_only: bool = False
    ) -> tuple:
        """Evaluate an expression. Scalar types are assigned by value.

        Args:
            expression (Any): The expression to evaluate.
            const_expr (bool): Whether the expression is a constant. Defaults to False.
            reqd_type (Any): The required type of the expression. Defaults to None.

        Returns:
            tuple[Any, list[Statement]] : The result of the evaluation.

        Raises:
            ValidationError: If the expression is not supported.
        """
        statements: list[Statement] = []
        if expression is None:
            return None, []

        if isinstance(expression, (ImaginaryLiteral, DurationLiteral)):
            raise_qasm3_error(
                f"Unsupported expression type {type(expression)}",
                ValidationError,
                expression.span,
            )

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

        if isinstance(expression, Identifier):
            var_name = expression.name
            if var_name in CONSTANTS_MAP:
                if not reqd_type or reqd_type == Qasm3FloatType:
                    return _check_and_return_value(CONSTANTS_MAP[var_name])
                raise_qasm3_error(
                    f"Constant {var_name} not allowed in non-float expression",
                    ValidationError,
                    expression.span,
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
                dimensions = cls.visitor_obj._get_from_visible_scope(  # type: ignore[union-attr]
                    var_name
                ).dims
            else:
                raise_qasm3_error(
                    message=f"Unsupported target type {type(target)} for sizeof expression",
                    err_type=ValidationError,
                    span=expression.span,
                )

            if dimensions is None or len(dimensions) == 0:
                raise_qasm3_error(
                    message=f"Invalid sizeof usage, variable {var_name} is not an array.",
                    err_type=ValidationError,
                    span=expression.span,
                )

            if index is None:
                return _check_and_return_value(dimensions[0])  # return first dimension

            index, stmts = cls.evaluate_expression(index, const_expr, reqd_type=Qasm3IntType)
            statements.extend(stmts)

            assert index is not None and isinstance(index, int)
            if index < 0 or index >= len(dimensions):
                raise_qasm3_error(
                    f"Index {index} out of bounds for array {var_name} with "
                    f"{len(dimensions)} dimensions",
                    ValidationError,
                    expression.span,
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
                raise_qasm3_error(
                    f"Invalid value {expression.value} with type {type(expression)} "
                    f"for required type {reqd_type}",
                    ValidationError,
                    expression.span,
                )
            return _check_and_return_value(expression.value)

        if isinstance(expression, UnaryExpression):
            operand, returned_stats = cls.evaluate_expression(
                expression.expression, const_expr, reqd_type
            )
            if expression.op.name == "~" and not isinstance(operand, int):
                raise_qasm3_error(
                    f"Unsupported expression type {type(operand)} in ~ operation",
                    ValidationError,
                    expression.span,
                )
            op_name = "UMINUS" if expression.op.name == "-" else expression.op.name
            statements.extend(returned_stats)
            return _check_and_return_value(qasm3_expression_op_map(op_name, operand))

        if isinstance(expression, BinaryExpression):
            lhs_value, lhs_statements = cls.evaluate_expression(
                expression.lhs, const_expr, reqd_type
            )
            statements.extend(lhs_statements)
            rhs_value, rhs_statements = cls.evaluate_expression(
                expression.rhs, const_expr, reqd_type
            )
            statements.extend(rhs_statements)
            return _check_and_return_value(
                qasm3_expression_op_map(expression.op.name, lhs_value, rhs_value)
            )

        if isinstance(expression, FunctionCall):
            # function will not return a reqd / const type
            # Reference : https://openqasm.com/language/types.html#compile-time-constants, para: 5
            ret_value, ret_stmts = cls.visitor_obj._visit_function_call(expression)  # type: ignore
            statements.extend(ret_stmts)
            return _check_and_return_value(ret_value)

        raise_qasm3_error(
            f"Unsupported expression type {type(expression)}", ValidationError, expression.span
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
