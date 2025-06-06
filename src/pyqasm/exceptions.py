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
Module defining base PyQASM exceptions.

"""

import os
import sys
from typing import Optional, Type

from openqasm3.ast import QASMNode, Span
from openqasm3.parser import QASM3ParsingError
from openqasm3.printer import dumps

from ._logging import logger


class PyQasmError(Exception):
    """Base exception for all PyQASM exceptions."""


class ValidationError(PyQasmError):
    """Exception raised when a OpenQASM program fails validation."""
    
    def __init__(self, message: str, error_node=None, span=None):
        super().__init__(message)
        self.error_node = error_node
        self.span = span


class UnrollError(PyQasmError):
    """Exception raised when a OpenQASM program fails unrolling."""


class RebaseError(PyQasmError):
    """Exception raised when a OpenQASM program fails to rebase into target basis set."""


class QasmParsingError(QASM3ParsingError):
    """An error raised by the AST visitor during the AST-generation phase.  This is raised in cases
    where the given program could not be correctly parsed."""


class LoopException(Exception):
    """Base class for loop control flow exceptions (break/continue)."""


class BreakException(LoopException):
    """Exception to signal a break statement in a loop."""


class ContinueException(LoopException):
    """Exception to signal a continue statement in a loop."""


class PyqasmRuntimeError(Exception):
    """Base class for runtime errors in pyqasm."""


class LoopLimitExceeded(PyqasmRuntimeError):
    """Raised when a loop exceeds the maximum allowed iterations."""
    def __init__(self, message=None, error_node=None, span=None):
        super().__init__(message)
        self.error_node = error_node
        self.span = span


def raise_qasm3_error(
    message: Optional[str] = None,
    err_type: Type[Exception] = ValidationError,
    error_node: Optional[QASMNode] = None,
    span: Optional[Span] = None,
    raised_from: Optional[Exception] = None,
) -> None:
    """Raises a QASM3 conversion error with optional chaining from another exception.

    Args:
        message: The error message. If not provided, a default message will be used.
        err_type: The type of error to raise.
        error_node: The QASM node that caused the error.
        span: The span (location) in the QASM file where the error occurred.
        raised_from: Optional exception from which this error was raised (chaining).

    Raises:
        err_type: The error type initialized with the specified message and chained exception.
    """
    error_parts = []

    if span:
        error_parts.append(
            f"Error at line {span.start_line}, column {span.start_column} in QASM file"
        )

    if error_node:
        try:
            if isinstance(error_node, QASMNode):
                error_parts.append("\n >>>>>> " + dumps(error_node, indent="    ") + "\n")
            elif isinstance(error_node, list):
                error_parts.append(
                    "\n >>>>>> " + " , ".join(dumps(node, indent="    ") for node in error_node)
                )
        except Exception as _:  # pylint: disable = broad-exception-caught
            print(_)
            error_parts.append("\n >>>>>> " + str(error_node))

    if error_parts:
        logger.error("\n".join(error_parts))

    if os.getenv("PYQASM_EXPAND_TRACEBACK", "false") == "false":
        # Disable traceback for cleaner output
        sys.tracebacklimit = 0
    else:
        # default value
        sys.tracebacklimit = None  # type: ignore

    # Extract the latest message from the traceback if raised_from is provided
    if raised_from:
        raise err_type(message) from raised_from
    raise err_type(message)
