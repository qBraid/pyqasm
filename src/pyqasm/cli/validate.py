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
Script to verify OpenQASM files

"""

import logging
import os
from typing import Optional

import typer
from rich.console import Console

from pyqasm import load
from pyqasm.exceptions import QasmParsingError, UnrollError, ValidationError

logger = logging.getLogger(__name__)


def validate_paths_exist(paths: Optional[list[str]]) -> Optional[list[str]]:
    """Verifies that each path in the provided list exists."""
    if not paths:
        return paths

    non_existent_paths = [path for path in paths if not os.path.exists(path)]
    if non_existent_paths:
        if len(non_existent_paths) == 1:
            raise typer.BadParameter(f"Path '{non_existent_paths[0]}' does not exist")

        formatted_paths = ", ".join(f"'{item}'" for item in non_existent_paths)
        raise typer.BadParameter(f"The following paths do not exist: {formatted_paths}")
    return paths


# pylint: disable-next=too-many-locals,too-many-statements
def validate_qasm(src_paths: list[str], skip_files: Optional[list[str]] = None) -> None:
    """Script validate OpenQASM files"""
    skip_files = skip_files or []

    failed_files: list[tuple[str, Exception]] = []

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

    def validate_qasm_file(file_path: str) -> None:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if should_skip(file_path, content):
            return

        try:
            module = load(file_path)
            module.validate()
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
                    validate_qasm_file(file_path)
                    count += 1
        return count

    checked = 0
    for item in src_paths:
        if os.path.isdir(item):
            checked += process_files_in_directory(item)
        elif os.path.isfile(item) and item.endswith(".qasm"):
            validate_qasm_file(item)
            checked += 1

    checked -= len(skip_files)

    if checked == 0:
        console.print("No .qasm files present. Nothing to do.")
        raise typer.Exit(0)

    s_checked = "" if checked == 1 else "s"
    if failed_files:
        for file, err in failed_files:
            category = (
                "".join(["-" + c.lower() if c.isupper() else c for c in type(err).__name__])
                .lstrip("-")
                .removesuffix("-error")
            )
            # pylint: disable-next=anomalous-backslash-in-string
            console.print(f"{file}: [red]error:[/red] {err} [yellow]\[{category}][/yellow]")
        num_failed = len(failed_files)
        s1 = "" if num_failed == 1 else "s"
        console.print(
            f"[red]Found errors in {num_failed} file{s1} "
            f"(checked {checked} source file{s_checked})[/red]"
        )
        raise typer.Exit(1)

    console.print(f"[green]Success: no issues found in {checked} source file{s_checked}[/green]")
    raise typer.Exit(0)
