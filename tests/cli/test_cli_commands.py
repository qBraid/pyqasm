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
Module containing unit tests for PyQASM CLI commands.

"""

import os
import re
import shutil

import pytest
import typer
from typer.testing import CliRunner

from pyqasm.cli.main import app
from pyqasm.cli.validate import validate_qasm

CLI_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCE_DIR = os.path.join(CLI_TESTS_DIR, "resources")
INVALID_FILE = os.path.join(RESOURCE_DIR, "invalid1.qasm")
VALID_FILES = [
    os.path.join(RESOURCE_DIR, "valid1.qasm"),
    os.path.join(RESOURCE_DIR, "valid2.qasm"),
]


@pytest.fixture
def runner():
    """Fixture to create a CLI runner."""
    return CliRunner()


def normalize_output(output):
    """Normalize the output by stripping whitespace and replacing multiple spaces with a single space."""
    return re.sub(r"\s+", " ", output.strip())


def test_validate_qasm_with_invalid_file(capsys):
    """Test validate_qasm function with an invalid file present."""
    src_paths = [RESOURCE_DIR]

    with pytest.raises(typer.Exit):
        validate_qasm(src_paths)

    captured = capsys.readouterr()

    captured_out = normalize_output(captured.out)
    assert f"{INVALID_FILE}: error:" in captured_out
    assert "Index 2 out of range for register of size 1 in qubit [validation]" in captured_out
    assert "Found errors in 1 file (checked 3 source files)" in captured_out


def test_validate_qasm_with_skip_file(capsys):
    """Test validate_qasm function skipping invalid files."""
    src_paths = [RESOURCE_DIR]
    skip_files = [INVALID_FILE]

    with pytest.raises(typer.Exit):
        validate_qasm(src_paths, skip_files=skip_files)

    captured = capsys.readouterr()

    captured_out = captured.out.replace("\n", "")
    assert f"Success: no issues found in {len(VALID_FILES)} source files" in captured_out


def test_validate_command_with_invalid_file(runner: CliRunner):
    """Test the `validate` CLI command with an invalid file present."""
    result = runner.invoke(app, ["validate", RESOURCE_DIR])

    assert result.exit_code == 1

    result_output = normalize_output(result.output)
    assert f"{INVALID_FILE}: error:" in result_output
    assert "Index 2 out of range for register of size 1 in qubit [validation]" in result_output
    assert "Found errors in 1 file (checked 3 source files)" in result_output


def test_validate_command_with_skip_file(runner: CliRunner):
    """Test the `validate` CLI command skipping invalid files."""
    result = runner.invoke(app, ["validate", RESOURCE_DIR, "--skip", INVALID_FILE])

    assert result.exit_code == 0

    result_output = result.output.replace("\n", "")
    assert f"Success: no issues found in {len(VALID_FILES)} source files" in result_output


def test_validate_command_with_only_valid_files(runner: CliRunner):
    """Test the `validate` CLI command with only valid files."""
    valid_only_dir = os.path.join(RESOURCE_DIR, "valid")
    os.makedirs(valid_only_dir, exist_ok=True)

    try:
        for file in VALID_FILES:
            basename = os.path.basename(file)
            target_path = os.path.join(valid_only_dir, basename)
            with open(file, "r") as src, open(target_path, "w") as dst:
                dst.write(src.read())

        result = runner.invoke(app, ["validate", valid_only_dir])

        assert result.exit_code == 0
        assert (
            f"Success: no issues found in {len(VALID_FILES)} source files"
            in result.output.replace("\n", "")
        )

    finally:
        shutil.rmtree(valid_only_dir, ignore_errors=True)


def test_validate_command_no_files(runner: CliRunner):
    """Test the `validate` CLI command with no files provided."""
    empty_dir = os.path.join(CLI_TESTS_DIR, "resources", "empty")
    os.makedirs(empty_dir, exist_ok=True)

    try:
        result = runner.invoke(app, ["validate", empty_dir])

        assert result.exit_code == 0
        assert "No .qasm files present. Nothing to do." in result.output
    finally:
        shutil.rmtree(empty_dir, ignore_errors=True)


def test_main_version_flag(runner: CliRunner):
    """Test the `--version` flag of the CLI."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "pyqasm/" in result.output


def test_main_help_flag(runner: CliRunner):
    """Test the `--help` flag of the CLI."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "validate" in result.output
