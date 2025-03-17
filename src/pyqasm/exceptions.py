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

import logging
from typing import Optional, Type

from openqasm3.ast import Span
from openqasm3.parser import QASM3ParsingError


class PyQasmError(Exception):
    """Base exception for all PyQASM exceptions."""


class ValidationError(PyQasmError):
    """Exception raised when a OpenQASM program fails validation."""


class UnrollError(PyQasmError):
    """Exception raised when a OpenQASM program fails unrolling."""


class RebaseError(PyQasmError):
    """Exception raised when a OpenQASM program fails to rebase into target basis set."""


class QasmParsingError(QASM3ParsingError):
    """An error raised by the AST visitor during the AST-generation phase.  This is raised in cases
    where the given program could not be correctly parsed."""


def raise_qasm3_error(
    message: Optional[str] = None,
    err_type: Type[Exception] = ValidationError,
    span: Optional[Span] = None,
    raised_from: Optional[Exception] = None,
) -> None:
    """Raises a QASM3 conversion error with optional chaining from another exception.

    Args:
        message: The error message. If not provided, a default message will be used.
        err_type: The type of error to raise.
        span: The span (location) in the QASM file where the error occurred.
        raised_from: Optional exception from which this error was raised (chaining).

    Raises:
        err_type: The error type initialized with the specified message and chained exception.
    """
    if span:
        logging.error(
            "Error at line %s, column %s in QASM file", span.start_line, span.start_column
        )

    if raised_from:
        raise err_type(message) from raised_from
    raise err_type(message)
