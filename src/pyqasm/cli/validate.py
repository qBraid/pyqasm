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

import os
import traceback
from typing import Optional

import typer
from rich.console import Console

from pyqasm import load

DEFAULT_ERROR_MESSAGE = (
    "An unexpected error occurred while processing your PyQASM CLI command. "
    "Please check your input and try again. If the problem persists, "
    "visit https://github.com/qBraid/pyqasm/issues to file a bug report."
)


def handle_error(
    error_type: Optional[str] = None, message: Optional[str] = None, include_traceback: bool = True
) -> None:
    """Generic CLI error handling helper function.

    This function handles errors by printing a styled error message to stderr and optionally
    including a traceback. It then exits the application with a non-zero status code, indicating
    an error.

    Args:
        error_type (Optional[str]): The type of the error to be displayed. Defaults to "Error" if
                                    not specified.
        message (Optional[str]): The error message to be displayed. If not specified, a default
                                 error message is used.
        include_traceback (bool): If True, include the traceback of the exception in the output.
                                  Defaults to True.

    Raises:
        typer.Exit: Exits the application with a status code of 1 to indicate an error.
    """
    error_type = error_type or "Error"
    message = message or DEFAULT_ERROR_MESSAGE
    error_prefix = typer.style(f"{error_type}:", fg=typer.colors.RED, bold=True)
    full_message = f"\n{error_prefix} {message}\n"
    if include_traceback:
        tb_string = traceback.format_exc()
        # TODO: find out reason for weird traceback emitted from
        # qbraid jobs enable/disable when library not installed.
        # For now, if matches, just don't print it.
        if tb_string.strip() != "NoneType: None":
            full_message += f"\n{tb_string}"
    typer.echo(full_message, err=True)
    raise typer.Exit(code=1)


def check_and_fix_headers(
    src_paths: list[str],
    skip_files: Optional[list[str]] = None,
) -> None:
    """Script to add or verify OpenQASM files"""
    for path in src_paths:
        if not os.path.exists(path):
            handle_error(error_type="FileNotFoundError", message=f"Path '{path}' does not exist.")

    skip_files = skip_files or []

    failed_files = []

    console = Console()

    def should_skip(filepath: str, content: str) -> bool:
        if filepath in skip_files:
            return True

        skip_tag = "// pyqasm: ignore"
        line_number = 0

        for line in content.splitlines():
            line_number += 1
            if 5 <= line_number <= 30 and skip_tag in line:
                return True
            if line_number > 30:
                break

        return False

    def validate_qasm(file_path: str) -> None:
        with open(file_path, "r", encoding="ISO-8859-1") as f:
            content = f.read()

        # Check if the content already starts with the header or if the file should be skipped
        if should_skip(file_path, content):
            return

        try:
            module = load(file_path)
            module.validate()
        except Exception as err:
            failed_files.append(file_path)

    def process_files_in_directory(directory: str, fix: bool = False) -> int:
        count = 0
        if not os.path.isdir(directory):
            return count
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".qasm"):
                    file_path = os.path.join(root, file)
                    validate_qasm(file_path, fix)
                    count += 1
        return count

    checked = 0
    for item in src_paths:
        if os.path.isdir(item):
            checked += process_files_in_directory(item)
        elif os.path.isfile(item) and item.endswith(".qasm"):
            validate_qasm(item)
            checked += 1
        else:
            if not os.path.isfile(item):
                handle_error(
                    error_type="FileNotFoundError", message=f"Path '{item}' does not exist."
                )

    if checked == 0:
        console.print("[bold]No QASM files present. Nothing to do[/bold] 😴")
        raise typer.Exit(0)

    if failed_files:
        for file in failed_files:
            console.print(f"[bold]would fix {file}[/bold]")
        num_failed = len(failed_files)
        num_passed = checked - num_failed
        s1, s2 = ("", "s") if num_failed == 1 else ("s", "")
        s_passed = "" if num_passed == 1 else "s"
        console.print("[bold]\nOh no![/bold] 💥 💔 💥")
        if num_passed > 0:
            punc = ", "
            passed_msg = f"[blue]{num_passed}[/blue] file{s_passed} would be left unchanged."
        else:
            punc = "."
            passed_msg = ""

        failed_msg = f"[bold][blue]{num_failed}[/blue] file{s1} need{s2} updating{punc}[/bold]"
        console.print(f"{failed_msg}{passed_msg}")
        raise typer.Exit(1)

    else:
        s_checked = "" if checked == 1 else "s"
        console.print("[bold]All done![/bold] ✨ 🚀 ✨")
        console.print(f"[blue]{checked}[/blue] file{s_checked} would be left unchanged.")
        raise typer.Exit(0)