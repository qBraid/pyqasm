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
import tempfile
from io import StringIO
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from pyqasm import dumps, load
from pyqasm.exceptions import QasmParsingError, UnrollError, ValidationError

from .utils import skip_qasm_files_with_tag

logger = logging.getLogger(__name__)
logger.propagate = False


# pylint: disable-next=too-many-locals,too-many-statements
def unroll_qasm(
    src_paths: list[str],
    skip_files: Optional[list[str]] = None,
    overwrite: Optional[bool] = False,
    output_path: Optional[str] = None,
) -> None:
    """Unroll OpenQASM files"""
    skip_files = skip_files or []

    failed_files: list[tuple[str, Exception, str]] = []
    successful_files: list[str] = []

    console = Console()

    # pylint: disable-next=too-many-locals, too-many-branches, too-many-statements
    def unroll_qasm_file(file_path: str) -> None:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if file_path in skip_files:
            return
        if skip_qasm_files_with_tag(content, "unroll"):
            skip_files.append(file_path)
            return

        pyqasm_logger = logging.getLogger("pyqasm")
        pyqasm_logger.setLevel(logging.ERROR)
        pyqasm_logger.handlers.clear()  # Suppress previous handlers
        pyqasm_logger.propagate = False  # Prevent propagation
        buf = StringIO()
        handler = logging.StreamHandler(buf)
        handler.setLevel(logging.ERROR)
        pyqasm_logger.addHandler(handler)
        try:
            module = load(file_path)
            module.unroll()
            unrolled_content = dumps(module)

            # Determine output file path
            if output_path and len(src_paths) == 1:
                # If output_path is a directory, use the input filename inside that directory
                if os.path.isdir(output_path):
                    output_file = os.path.join(output_path, os.path.basename(file_path))
                else:
                    output_file = output_path
                if os.path.exists(output_file) and not overwrite:
                    console.print(
                        "Output file '{output_file}' already exists. Use --overwrite to force."
                    )
                    raise typer.Exit(1)
                output_dir = os.path.dirname(output_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                temp_dir = output_dir
                temp_file = None
                try:
                    with tempfile.NamedTemporaryFile(
                        "w", encoding="utf-8", dir=temp_dir, delete=False
                    ) as tf:
                        temp_file = tf.name
                        tf.write(unrolled_content)
                    os.replace(temp_file, output_file)
                except Exception as write_err:
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)
                    raise write_err
            elif overwrite:
                output_file = file_path
            else:
                # Create new file with _unrolled suffix
                path = Path(file_path)
                output_file = str(path.parent / f"{path.stem}_unrolled{path.suffix}")

            with open(output_file, "w", encoding="utf-8") as outf:
                outf.write(unrolled_content)

            successful_files.append(file_path)

        except (ValidationError, UnrollError, QasmParsingError) as err:
            failed_files.append((file_path, err, buf.getvalue()))
        except Exception as uncaught:  # pylint: disable=broad-exception-caught
            logger.debug("Uncaught error in %s", file_path, exc_info=uncaught)
            failed_files.append((file_path, uncaught, buf.getvalue()))
        finally:
            pyqasm_logger.removeHandler(handler)  # Clean up handler

    def process_files_in_directory(directory: str) -> int:
        count = 0
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

    loaded_files = len(skip_files) + len(successful_files) + len(failed_files)
    if (checked - loaded_files) == len(src_paths) or checked == 0:
        console.print("[red]No .qasm files present. Nothing to do.[/red]")

    # Report results
    if successful_files:
        s_success = "" if len(successful_files) == 1 else "s"
        console.print(
            f"[green]Successfully unrolled {len(successful_files)} file{s_success}[/green]"
        )

    if skip_files:
        skiped = "" if len(skip_files) == 1 else "s"
        console.print(f"[yellow]Skipped {len(skip_files)} file{skiped}[/yellow]")

    if failed_files:
        for file, err, raw_stderr in failed_files:
            category = (
                "".join(["-" + c.lower() if c.isupper() else c for c in type(err).__name__])
                .lstrip("-")
                .removesuffix("-error")
            )
            # pylint: disable-next=anomalous-backslash-in-string
            console.print("-" * 100)
            console.print(f"Failed to unroll: {file}", "\n")
            console.print(f"[yellow]\\[{category}-error][/yellow] -> {err}", "\n")
            if raw_stderr:
                console.print(raw_stderr.rstrip())
                console.print("-" * 100)

        num_failed = len(failed_files)
        s1 = "" if num_failed == 1 else "s"
        console.print(f"[red]Failed to unroll {num_failed} file{s1}[/red]")

    console.print(f"[green]Checked {checked} source file{'s' if checked != 1 else ''}[/green]")
    raise typer.Exit(0)
