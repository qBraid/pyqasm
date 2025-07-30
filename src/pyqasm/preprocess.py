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

from pyqasm.exceptions import ValidationError


@dataclass
class IncludeContext:
    """Context for recursively processing include statements."""

    base_file_header: list[str] = field(default_factory=list)
    include_stdgates: bool = False
    include_qelib1: bool = False
    visited: set[str] = field(default_factory=set)


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


def process_include_statements(filename: str) -> str:
    """
    Recursively processes include statements in an OpenQASM file, replacing them with the
    contents of the included files. Handles circular includes and missing files.

    Args:
        filename (str): The path to the OpenQASM file to process.

    Returns:
        str: The fully include-resolved program content.

    Raises:
        FileNotFoundError: If an included file cannot be found.
        ValidationError: If a circular include is detected.
    """
    # Generate context for include processing
    ctx = IncludeContext()

    with open(filename, "r", encoding="utf-8") as f:
        program = f.read()

    _collect_headers(ctx, program)

    # Return program and let entrypoint handle error if missing OPENQASM line
    if len(ctx.base_file_header) == 0 or "OPENQASM" not in ctx.base_file_header[0]:
        return program

    # Recursively process and replace includes in-line
    result = _process_file(ctx, filename)

    # Return processed file with original header
    return "\n".join(ctx.base_file_header) + "\n\n" + result


def _process_file(ctx: IncludeContext, filepath: str) -> str:
    """
    Process a single file, replacing include statements with the contents of the included files
    recursively.

    Args:
        ctx (IncludeContext): The context for processing includes.
        filepath (str): The path to the file to process.

    Returns:
        str: The fully include-resolved program content.

    Raises:
        FileNotFoundError: If an included file cannot be found.
        ValidationError: If a circular include is detected.
    """
    filename = os.path.basename(filepath)
    if filename in ctx.visited:
        return ""  # Already processed this file, skip to avoid circular includes

    with open(filepath, "r", encoding="utf-8") as f:
        program = f.read()

    ctx.visited.add(filename)  # Mark as visited to avoid looping
    new_program_lines = []

    for idx, line in enumerate(program.splitlines()):
        # Search for custom include statements
        match = PATTERNS["include_custom"].match(line)
        if match:
            include_filename = match.group(1)
            # Check for circular imports
            if include_filename.strip() == filename.strip():
                col = line.index(include_filename) + 1
                raise ValidationError(
                    f"Circular include detected for file '{include_filename}'"
                    f" at line {idx + 1}, column {col}: '{line.strip()}'"
                )
            # Find valid path to included file
            include_path = _resolve_include_path(filepath, include_filename)
            if include_path is None:
                raise FileNotFoundError(
                    f"Include file '{include_filename}' not found at line "
                    f"{idx+1}, column {line.find(include_filename)+1}"
                )
            # Recursively process include statements within the included file
            included_content = _process_file(ctx, include_path)
            new_program_lines.append(included_content)
        else:
            _check_for_std_includes(ctx, line)
            # Skip openqasm and std includes (already in header)
            if not PATTERNS["openqasm"].match(line) and not PATTERNS["include_standard"].match(
                line
            ):
                new_program_lines.append(line)

    # Join and save cleaned content for this file
    cleaned = "\n".join(new_program_lines)
    return cleaned  # return the fully inlined program


def _check_for_std_includes(ctx: IncludeContext, line: str) -> None:
    """
    Check if the line contains standard includes and update context accordingly.

    Args:
        ctx (IncludeContext): The context to update.
        line (str): The line to check.

    Returns:
        None
    """
    # Check if additional standard includes are needed
    if not ctx.include_stdgates and PATTERNS["include_stdgates"].match(line):
        ctx.include_stdgates = True
        ctx.base_file_header.append('include "stdgates.inc";')
    if not ctx.include_qelib1 and PATTERNS["include_qelib1"].match(line):
        ctx.include_qelib1 = True
        ctx.base_file_header.append('include "qelib1.inc";')


def _resolve_include_path(base_file: str, file_to_include: str) -> str | None:
    """
    Resolve the include path for a given file.

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


def _collect_headers(ctx: IncludeContext, program: str) -> None:
    """
    Collects the header lines (OPENQASM and standard includes) from the base file.

    Args:
        program (str): The program content to scan for headers.

    Returns:
        None: Modifies the context in place.
    """
    found_openqasm = False

    for line in program.splitlines():
        stripped = line.strip()
        if len(stripped) == 0:
            continue  # skip empty lines

        if PATTERNS["openqasm"].match(line):
            if stripped not in ctx.base_file_header:
                # ensure OPENQASM comes first
                ctx.base_file_header.insert(0, stripped)
                found_openqasm = True
            continue  # no need to check further for this line

        if PATTERNS["include_standard"].match(line):
            # Include before OPENQASM is invalid - return to handle error
            if not found_openqasm:
                return
            # Add included library to header if not already present
            if stripped not in ctx.base_file_header:
                ctx.base_file_header.append(stripped)
            # Check which standard includes this is
            if not ctx.include_stdgates and PATTERNS["include_stdgates"].match(line):
                ctx.include_stdgates = True
            if not ctx.include_qelib1 and PATTERNS["include_qelib1"].match(line):
                ctx.include_qelib1 = True
            continue

        # If we've already found standard includes, we can stop
        if ctx.include_stdgates and ctx.include_qelib1:
            return
