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
Script to unroll OpenQASM files

"""

import logging
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from pyqasm import dumps, load
from pyqasm.exceptions import QasmParsingError, UnrollError, ValidationError

logger = logging.getLogger(__name__)
logger.propagate = False


# pylint: disable-next=too-many-locals,too-many-statements
def unroll_qasm(
    src_paths: list[str],
    skip_files: Optional[list[str]] = None,
    overwrite: bool = False,
    output_path: Optional[str] = None,
) -> None:
    """Unroll OpenQASM files"""
    skip_files = skip_files or []

    failed_files: list[tuple[str, Exception]] = []
    successful_files: list[str] = []

    console = Console()

    def should_skip(filepath: str, content: str) -> bool:
        if filepath in skip_files:
            return True

        skip_tag = "// pyqasm: ignore"

        for line in content.splitlines():
            if skip_tag in line:
                return True
            if "OPENQASM" in line:
                break

        return False

    def unroll_qasm_file(file_path: str) -> None:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if should_skip(file_path, content):
            return

        try:
            module = load(file_path)
            module.unroll()
            unrolled_content = dumps(module)

            # Determine output file path
            if output_path and len(src_paths) == 1:
                # Use explicitly specified output path
                output_file = output_path
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
            elif overwrite:
                output_file = file_path
            else:
                # Create new file with _unrolled suffix
                path = Path(file_path)
                output_file = str(path.parent / f"{path.stem}_unrolled{path.suffix}")

            # Write the unrolled content
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(unrolled_content)

            successful_files.append(file_path)

        except (ValidationError, UnrollError, QasmParsingError) as err:
            failed_files.append((file_path, err))
        except Exception as uncaught_err:  # pylint: disable=broad-exception-caught
            logger.debug("Uncaught error in %s", file_path, exc_info=uncaught_err)
            failed_files.append((file_path, uncaught_err))

    def process_files_in_directory(directory: str) -> int:
        count = 0
        if not os.path.isdir(directory):
            return count
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".qasm"):
                    file_path = os.path.join(root, file)
                    unroll_qasm_file(file_path)
                    count += 1
        return count

    checked = 0
    for item in src_paths:
        if os.path.isdir(item):
            checked += process_files_in_directory(item)
        elif os.path.isfile(item) and item.endswith(".qasm"):
            unroll_qasm_file(item)
            checked += 1

    checked -= len(skip_files)

    if checked == 0:
        console.print("No .qasm files present. Nothing to do.")
        raise typer.Exit(0)

    # Report results
    if successful_files:
        s_success = "" if len(successful_files) == 1 else "s"
        console.print(
            f"[green]Successfully unrolled {len(successful_files)} file{s_success}[/green]"
        )

    if failed_files:
        for file, err in failed_files:
            category = (
                "".join(["-" + c.lower() if c.isupper() else c for c in type(err).__name__])
                .lstrip("-")
                .removesuffix("-error")
            )
            # pylint: disable-next=anomalous-backslash-in-string
            console.print(f"Failed to unroll: {file} ({err}) [yellow]\\[{category}][/yellow]")

        num_failed = len(failed_files)
        s1 = "" if num_failed == 1 else "s"
        console.print(
            f"[red]Failed to unroll {num_failed} file{s1} "
            f"(checked {checked} source file{'s' if checked != 1 else ''})[/red]"
        )
        raise typer.Exit(1)

    s_checked = "" if checked == 1 else "s"
    console.print(f"[green]Success: unrolled {checked} source file{s_checked}[/green]")
    raise typer.Exit(0)
