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
    # directory to resolve includes against, tried before the including file's own
    include_dir: str | None = None


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
    # OPENQASM 2 only. Captures indent, name, the parenthesised parameter list if any,
    # and the qubit list: "opaque Rz(lam) q;", "opaque ZZ() q1,q2;", "opaque zz q1,q2;"
    "opaque": re.compile(
        r"^([ \t]*)opaque\s+([A-Za-z_][A-Za-z0-9_]*)\s*(\([^)]*\))?\s*([^;{}]*?)\s*;",
        re.MULTILINE,
    ),
    "openqasm2": re.compile(r"^\s*OPENQASM\s+2(?:\.\d+)?;", re.MULTILINE),
}


def _blank_comments(program: str) -> str:
    """Overwrite `//` and `/* */` comments with spaces.

    Blanked rather than deleted so line and column numbers are unchanged: the parser
    reports spans against this text, and deleting a comment would shift every position
    after it.

    Args:
        program (str): The OpenQASM program text.

    Returns:
        str: The text with comment characters replaced by spaces.
    """
    out = list(program)
    idx, end = 0, len(program)
    in_line = in_block = False
    while idx < end:
        char, following = program[idx], program[idx + 1 : idx + 2]
        if in_line:
            in_line = char != "\n"
            out[idx] = char if char == "\n" else " "
        elif in_block:
            in_block = not (char == "*" and following == "/")
            out[idx] = char if char == "\n" else " "
            if not in_block:
                out[idx + 1] = " "
                idx += 1
        elif char == "/" and following in ("/", "*"):
            in_line, in_block = following == "/", following == "*"
            out[idx] = out[idx + 1] = " "
            idx += 1
        idx += 1
    return "".join(out)


def rewrite_opaque_declarations(program: str) -> tuple[str, set[str]]:
    """Rewrite OpenQASM 2 ``opaque`` declarations into gate definitions with empty bodies.

    The ``openqasm3`` parser pyqasm routes qasm2 through has no production for ``opaque``,
    so this runs before parsing. The empty body carries the gate's name and arity only,
    which is all an opaque gate has (issue #370). Gated on the qasm2 header, since
    ``opaque`` is not OpenQASM 3 syntax.

    Comments are blanked first, so a declaration commented out with ``/* */`` is neither
    rewritten nor recorded. The result goes straight to the parser, which discards
    comments anyway.

    Args:
        program (str): The OpenQASM program text.

    Returns:
        tuple[str, set[str]]: The rewritten program, and the names declared opaque.
    """
    code = _blank_comments(program)
    if not PATTERNS["openqasm2"].search(code):
        return program, set()

    names: set[str] = set()

    def _replace(match: re.Match) -> str:
        indent, name, params, qubits = match.groups()
        names.add(name)
        return f"{indent}gate {name}{params or ''} {qubits} {{ }}"

    return PATTERNS["opaque"].sub(_replace, code), names


def process_include_statements(filename: str, include_dir: str | None = None) -> str:
    """
    Recursively processes include statements in an OpenQASM file, replacing them with the
    contents of the included files. Handles circular includes and missing files.

    Args:
        filename (str): The path to the OpenQASM file to process.
        include_dir (str | None): Directory to resolve includes against, tried before the
            directory of the including file.

    Returns:
        str: The fully include-resolved program content.

    Raises:
        FileNotFoundError: If an included file cannot be found.
        ValidationError: If a circular include is detected.
    """
    with open(filename, "r", encoding="utf-8") as f:
        program = f.read()

    return _inline_includes(program, filename, include_dir)


def process_include_sources(program: str, include_dir: str) -> str:
    """
    Resolve the include statements of a program held as a string, against a directory the
    caller names.

    A string has no filesystem location of its own to resolve relative includes against,
    so ``include_dir`` supplies one (issue #368).

    Args:
        program (str): The OpenQASM program text.
        include_dir (str): Directory holding the include files.

    Returns:
        str: The fully include-resolved program content.

    Raises:
        ValidationError: If an include is not found in the directory, or is circular.
    """
    return _inline_includes(program, None, include_dir)


def _inline_includes(program: str, origin: str | None, include_dir: str | None) -> str:
    """
    Inline the include statements of a program, from either a file or a string.

    Args:
        program (str): The OpenQASM program text.
        origin (str | None): The path the text was read from, or None for a string.
        include_dir (str | None): Directory to resolve includes against.

    Returns:
        str: The fully include-resolved program content.
    """
    ctx = IncludeContext(include_dir=include_dir)
    _collect_headers(ctx, program)

    # Return program and let entrypoint handle error if missing OPENQASM line
    if len(ctx.base_file_header) == 0 or "OPENQASM" not in ctx.base_file_header[0]:
        return program

    if origin is not None:
        ctx.visited.add(os.path.basename(origin))  # Mark as visited to avoid looping

    # bind first: the walk appends to base_file_header when it meets a std include
    # inside an included file
    result = _process_source(ctx, program, origin)

    # Return processed program with original header
    return "\n".join(ctx.base_file_header) + "\n\n" + result


def _process_file(ctx: IncludeContext, filepath: str) -> str:
    """
    Read a file and inline its own include statements recursively.

    Args:
        ctx (IncludeContext): The context for processing includes.
        filepath (str): The path to the file to process.

    Returns:
        str: The fully include-resolved file content, empty if already included.
    """
    filename = os.path.basename(filepath)
    if filename in ctx.visited:
        return ""  # Already processed this file, skip to avoid circular includes

    with open(filepath, "r", encoding="utf-8") as f:
        program = f.read()

    ctx.visited.add(filename)  # Mark as visited to avoid looping
    return _process_source(ctx, program, filepath)


def _process_source(ctx: IncludeContext, program: str, origin: str | None) -> str:
    """
    Replace the include statements in one source with the contents of the included files.

    Args:
        ctx (IncludeContext): The context for processing includes.
        program (str): The text of the source to process.
        origin (str | None): The path the text was read from, or None for a string.

    Returns:
        str: The fully include-resolved program content.

    Raises:
        FileNotFoundError: If an included file cannot be found.
        ValidationError: If a circular include is detected, or an include cannot be
            resolved for a program given as a string.
    """
    filename = os.path.basename(origin) if origin is not None else None
    new_program_lines = []

    for idx, line in enumerate(program.splitlines()):
        # Search for custom include statements
        match = PATTERNS["include_custom"].match(line)
        if match:
            include_filename = match.group(1)
            # Check for circular imports
            if filename is not None and include_filename.strip() == filename.strip():
                col = line.index(include_filename) + 1
                raise ValidationError(
                    f"Circular include detected for file '{include_filename}'"
                    f" at line {idx + 1}, column {col}: '{line.strip()}'"
                )
            # Find valid path to included file
            include_path = _resolve_include_path(origin, include_filename, ctx.include_dir)
            if include_path is None:
                where = f"at line {idx + 1}, column {line.find(include_filename) + 1}"
                if origin is None:  # a string can only have come from include_dir
                    raise ValidationError(
                        f"Include file '{include_filename}' not found in include_dir "
                        f"'{ctx.include_dir}' {where}: '{line.strip()}'"
                    )
                raise FileNotFoundError(f"Include file '{include_filename}' not found {where}")
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

    # Join and save cleaned content for this source
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


def _resolve_include_path(
    base_file: str | None, file_to_include: str, include_dir: str | None = None
) -> str | None:
    """
    Resolve the include path for a given file.

    Args:
        base_file (str | None): The file the include is made from, or None for a string.
        file_to_include (str): The file to include.
        include_dir (str | None): Directory to try before the base file's own.

    Returns:
        str | None: The resolved include path, or None if not found.
    """
    possible_paths = []
    if include_dir is not None:
        possible_paths.append(os.path.join(include_dir, file_to_include))
    if base_file is not None:
        # a string has no directory of its own, and must not fall back to the cwd
        possible_paths += [os.path.join(os.path.dirname(base_file), file_to_include)]
        possible_paths += [file_to_include]
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
