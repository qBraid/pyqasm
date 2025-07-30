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
Pre-processing prior to loading OpenQASM files as QasmModule objects.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from pyqasm.exceptions import ValidationError


@dataclass
class IncludeContext:
    """Context for recursively processing include statements."""

    visited: set[str] = field(default_factory=set)
    base_file_header: list[str] = field(default_factory=list)
    include_stdgates: bool = False
    include_qelib1: bool = False
    results: list[str] = field(default_factory=list)


PATTERNS = {
    "openqasm": re.compile(r"^\s*OPENQASM\s+\d+(?:\.\d+)?;\s*"),
    "include_stdgates": re.compile(r'^\s*include\s+"stdgates\.inc";\s*', re.MULTILINE),
    "include_qelib1": re.compile(r'^\s*include\s+"qelib1\.inc";\s*', re.MULTILINE),
    "include_custom": re.compile(
        r'^\s*include\s+"(?!stdgates\.inc|qelib1\.inc)([^"]+)";\s*', re.MULTILINE
    ),
    "include_standard": re.compile(
        r'^\s*include\s+"(?:stdgates\.inc|qelib1\.inc)";\s*', re.MULTILINE
    ),
    "include": re.compile(r'^\s*include\s+"([^"]+)";\s*', re.MULTILINE),
}


STD_FILES = ["stdgates.inc", "qelib1.inc"]


def process_include_statements(filename: str) -> str:
    # First, read the file and check if it has any custom includes
    with open(filename, "r", encoding="utf-8") as f:
        program = f.read()

    # Check if file has any custom includes
    has_custom_includes = bool(PATTERNS["include_custom"].search(program))

    # If no custom includes, return the file as-is
    if not has_custom_includes:
        return program

    # Initialize context
    ctx = IncludeContext()

    stack: list[tuple[str, Optional[int], Optional[int]]] = [(filename, None, None)]
    _collect_headers(ctx, filename)

    while stack:
        # Pop the next file to process
        current_file, current_file_idx, current_file_col = stack.pop()
        # Skip already processed files
        if current_file in ctx.visited:
            continue
        # Find path to include file
        valid_path = _resolve_include_path(filename, current_file)
        if valid_path is None:
            raise FileNotFoundError(
                f"Include file '{current_file}' not found at line "
                f"{current_file_idx}, column {current_file_col}"
            )
        # Read the file
        with open(valid_path, "r", encoding="utf-8") as f:
            program = f.read()

        # Find all additional files to include
        include_files = []
        # Iterate through program lines
        for idx, line in enumerate(program.splitlines()):
            # Search for custom include statements
            if new_includes := _get_custom_includes(ctx, current_file, line, idx):
                include_files.extend(new_includes)
            # Check if additional standard includes are needed
            if not ctx.include_stdgates and PATTERNS["include_stdgates"].match(line):
                ctx.include_stdgates = True
                ctx.base_file_header.append('include "stdgates.inc";')
            if not ctx.include_qelib1 and PATTERNS["include_qelib1"].match(line):
                ctx.include_qelib1 = True
                ctx.base_file_header.append('include "qelib1.inc";')

        # Additional custom includes found, add to stack
        if include_files:
            # Current file contains include - reprocess after includes
            stack.append((current_file, current_file_idx, current_file_col))
            stack.extend(include_files)
        else:
            # No more included files - add cleaned program to results
            ctx.results.append(_clean_statements(program))
            ctx.visited.add(current_file)  # mark as visited

    # Add original program header (without custom gates) to results
    result = "\n".join(ctx.base_file_header) + "\n\n" + "\n\n".join(ctx.results)
    return result


def _get_custom_includes(
    ctx: IncludeContext, current_file: str, line: str, line_idx: int
) -> list[tuple[str, int, int]]:
    """Extracts the custom include file name from a line.

    Args:
        line (str): The line containing the include statement.

    Returns:
        list[tuple[str, int, int]]: A list of tuples containing the include filename,
            line number, and column number where the include was found.
    """
    includes = []
    # Search for custom include statements
    match = PATTERNS["include_custom"].match(line)
    if match:
        include_filename = match.group(1)
        # Ignore circular imports
        if include_filename.strip() == current_file.strip():
            col = line.index(include_filename) + 1
            raise ValidationError(
                f"Circular include detected for file '{include_filename}'"
                f" at line {line_idx + 1}, column {col}: '{line.strip()}'"
            )
        # New include file to process found
        if include_filename not in STD_FILES and include_filename not in ctx.visited:
            col = line.index(include_filename) + 1
            includes.append((include_filename, line_idx + 1, col))
    return includes


def _resolve_include_path(base_file: str, file_to_include: str) -> str | None:
    """Resolve the include path for a given file.

    Args:
        base_file (str): The base file from which the include is being made.
        file_to_include (str): The file to include.

    Returns:
        str | None: The resolved include path, or None if not found.
    """
    possible_paths = [os.path.join(os.path.dirname(base_file), file_to_include), file_to_include]
    for path in possible_paths:
        if os.path.isfile(path):
            return path
    return None


def _collect_headers(ctx: IncludeContext, base_filename: str) -> None:
    """Collects the header lines (OPENQASM and standard includes) from the base file.
    Args:
        base_filename (str): The base filename to read.
    Returns:
        None: Modifies the context in place.
    """

    with open(base_filename, "r", encoding="utf-8") as f:
        program = f.read()

    for line in program.splitlines():

        if PATTERNS["openqasm"].match(line) or PATTERNS["include_standard"].match(line):
            if PATTERNS["openqasm"].match(line) and line.strip() not in ctx.base_file_header:
                # ensure openqasm line comes first
                ctx.base_file_header.insert(0, line.strip())
            if line.strip() not in ctx.base_file_header:
                ctx.base_file_header.append(line.strip())
            if PATTERNS["include_stdgates"].match(line):
                ctx.include_stdgates = True
            if PATTERNS["include_qelib1"].match(line):
                ctx.include_qelib1 = True


def _clean_statements(program: str) -> str:
    """Removes all include and OPENQASM statements from the program.

    Args:
        program (str): The OpenQASM program as a string.

    Returns:
        str: The program with all include statements removed.
    """
    for pattern in [PATTERNS["openqasm"], PATTERNS["include"]]:
        program = pattern.sub("", program)
    return program
