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

from pyqasm.exceptions import ValidationError


def process_include_statements(program: str, filename: str) -> str:
    """
    Process include statements in a QASM file.

    Args:
        program (str): The QASM program string.
        filename (str): Path to the QASM file (for resolving relative includes).

    Returns:
        str: The processed QASM program with includes injected.

    Raises:
        FileNotFoundError: If an include file is not found or cannot be read.
    """
    program_lines = program.splitlines()
    processed_files = set()

    for idx, line in enumerate(program_lines):
        line = line.strip()
        if line.startswith("include"):
            # Extract include filename from quotes
            match = re.search(r'include\s+["\']([^"\']+)["\']', line)
            if not match:
                raise ValidationError("Invalid include statement detected in QASM file.")
            include_filename = match.group(1)
            # Skip stdgates.inc and already processed files
            if include_filename == "stdgates.inc" or include_filename in processed_files:
                continue
            # Try to find include file relative to main file first, then current directory
            include_paths = [
                os.path.join(os.path.dirname(filename), include_filename),  # Relative to main file
                include_filename,  # Current working directory
            ]
            include_found = False
            for include_path in include_paths:
                try:
                    with open(include_path, "r", encoding="utf-8") as include_file:
                        include_content = include_file.read().strip()
                        if (os.path.splitext(include_filename)[1]) == ".qasm":
                            # Remove extra OPENQASM version line to avoid duplicates
                            openqasm_pattern = r"^\s*OPENQASM\s+\d+\.\d+;\s*"
                            include_content = re.sub(openqasm_pattern, "", include_content, count=1)
                            # Remove extra stdgates.inc line to avoid duplicates
                            stdgates_pattern = r'^\s*include\s+"stdgates\.inc";\s*'
                            include_content = re.sub(stdgates_pattern, "", include_content, count=1)
                            # TODO: recursive handling for nested includes

                        # Replace the include line with the content
                        program_lines[idx] = include_content
                        processed_files.add(include_filename)
                        include_found = True
                        break
                except FileNotFoundError:
                    continue
            if not include_found:
                raise FileNotFoundError(f"Include file '{include_filename}' not found.") from None
    return "\n".join(program_lines)
