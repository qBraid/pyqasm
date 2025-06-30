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
Module containing unit tests for PyQASM CLI commands.

"""

import os
import re
import shutil
import warnings

import pytest
import typer
from typer.testing import CliRunner

warnings.filterwarnings(
    "ignore", "Importing 'pyqasm' outside a proper installation.", category=UserWarning
)

from pyqasm.cli.main import app
from pyqasm.cli.unroll import unroll_qasm
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
    assert "unroll" in result.output


# Unroll command tests
def test_unroll_command_single_file(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with a single file."""
    # Create a test file
    test_file = tmp_path / "test.qasm"
    test_file.write_text(
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        gate hgate q { h q; }
        qubit[2] q;
        hgate q[0];
        hgate q[1];
        """
    )

    result = runner.invoke(app, ["unroll", str(test_file)])

    assert result.exit_code == 0
    assert "Successfully unrolled 1 file" in result.output
    assert "Success: unrolled 1 source file" in result.output

    # Check that unrolled file was created
    unrolled_file = tmp_path / "test_unrolled.qasm"
    assert unrolled_file.exists()


def test_unroll_command_single_file_with_output(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with explicit output path."""
    # Create a test file
    test_file = tmp_path / "test.qasm"
    test_file.write_text(
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        gate hgate q { h q; }
        qubit[2] q;
        hgate q[0];
        hgate q[1];
        """
    )

    output_file = tmp_path / "custom_output.qasm"
    result = runner.invoke(app, ["unroll", str(test_file), "--output", str(output_file)])

    assert result.exit_code == 0
    assert "Successfully unrolled 1 file" in result.output
    assert output_file.exists()

    # Verify content was unrolled (custom gate should be expanded)
    content = output_file.read_text()
    assert "h q[0];" in content
    assert "h q[1];" in content
    assert "gate hgate" not in content  # Custom gate should be removed


def test_unroll_command_single_file_overwrite(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with overwrite option."""
    # Create a test file
    test_file = tmp_path / "test.qasm"
    original_content = """
    OPENQASM 3.0;
    include "stdgates.inc";
    gate hgate q { h q; }
    qubit[2] q;
    hgate q[0];
    hgate q[1];
    """
    test_file.write_text(original_content)

    result = runner.invoke(app, ["unroll", str(test_file), "--overwrite"])

    assert result.exit_code == 0
    assert "Successfully unrolled 1 file" in result.output

    # Check that original file was overwritten
    new_content = test_file.read_text()
    assert new_content != original_content
    assert "h q[0];" in new_content
    assert "h q[1];" in new_content
    assert "gate hgate" not in new_content


def test_unroll_command_directory(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with a directory."""
    # Create test directory with multiple files
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # Create multiple test files
    for i in range(3):
        test_file = test_dir / f"test{i}.qasm"
        test_file.write_text(
            f"""
            OPENQASM 3.0;
            include "stdgates.inc";
            gate hgate{i} q {{ h q; }}
            qubit[2] q;
            hgate{i} q[0];
            hgate{i} q[1];
            """
        )

    result = runner.invoke(app, ["unroll", str(test_dir)])

    assert result.exit_code == 0
    assert "Successfully unrolled 3 files" in result.output

    # Check that unrolled files were created
    for i in range(3):
        unrolled_file = test_dir / f"test{i}_unrolled.qasm"
        assert unrolled_file.exists()


def test_unroll_command_directory_overwrite(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with directory and overwrite."""
    # Create test directory with multiple files
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # Create multiple test files
    original_contents = []
    for i in range(2):
        test_file = test_dir / f"test{i}.qasm"
        content = """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        h q;
        """
        test_file.write_text(content)
        original_contents.append(content)

    result = runner.invoke(app, ["unroll", str(test_dir), "--overwrite"])

    assert result.exit_code == 0
    assert "Successfully unrolled 2 files" in result.output

    # Check that original files were overwritten
    for i in range(2):
        test_file = test_dir / f"test{i}.qasm"
        new_content = test_file.read_text()
        assert new_content != original_contents[i]
        assert "h q[0];" in new_content
        assert "h q[1];" in new_content


def test_unroll_command_with_skip(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with skip option."""
    # Create test directory with multiple files
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # Create test files
    for i in range(3):
        test_file = test_dir / f"test{i}.qasm"
        test_file.write_text(
            """
            OPENQASM 3.0;
            include "stdgates.inc";
            qubit[2] q;
            h q;
            """
        )

    # Skip one file
    skip_file = str(test_dir / "test1.qasm")
    result = runner.invoke(app, ["unroll", str(test_dir), "--skip", skip_file])

    assert result.exit_code == 0
    assert "Successfully unrolled 2 files" in result.output

    # Check that only 2 files were processed
    assert (test_dir / "test0_unrolled.qasm").exists()
    assert not (test_dir / "test1_unrolled.qasm").exists()
    assert (test_dir / "test2_unrolled.qasm").exists()


def test_unroll_command_with_skip_tag(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with skip tag in file."""
    # Create test directory
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # Create a file with skip tag
    skip_file = test_dir / "skip_me.qasm"
    skip_file.write_text(
        """
        // pyqasm: ignore
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[2] q;
        h q[0];
        """
    )

    # Create a normal file
    normal_file = test_dir / "normal.qasm"
    normal_file.write_text(
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        gate hgate q { h q; }
        qubit[2] q;
        hgate q[0];
        """
    )

    result = runner.invoke(app, ["unroll", str(test_dir)])

    assert result.exit_code == 0
    assert "Successfully unrolled 1 file" in result.output

    # Check that only normal file was processed
    assert (test_dir / "normal_unrolled.qasm").exists()
    assert not (test_dir / "skip_me_unrolled.qasm").exists()

def test_unroll_command_with_invalid_file(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with an invalid file."""
    # Create an invalid test file
    test_file = tmp_path / "invalid.qasm"
    test_file.write_text(
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        h q[2];  // Invalid: index 2 out of range
        """
    )

    result = runner.invoke(app, ["unroll", str(test_file)])

    assert result.exit_code == 1
    assert "Failed to unroll:" in result.output
    # The error message has extra spaces, so let's normalize it
    normalized_output = " ".join(result.output.split())
    assert "Index 2 out of range for register of size 1 in qubit" in normalized_output


def test_unroll_command_mixed_success_and_failure(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with mixed success and failure."""
    # Create test directory
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # Create a valid file
    valid_file = test_dir / "valid.qasm"
    valid_file.write_text(
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        h q[0];
        """
    )

    # Create an invalid file
    invalid_file = test_dir / "invalid.qasm"
    invalid_file.write_text(
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        h q[2];  // Invalid: index 2 out of range
        """
    )

    result = runner.invoke(app, ["unroll", str(test_dir)])

    assert result.exit_code == 1
    assert "Successfully unrolled 1 file" in result.output
    assert "Failed to unroll:" in result.output
    assert "Failed to unroll 1 file (checked 2 source files)" in result.output

    # Check that valid file was processed
    assert (test_dir / "valid_unrolled.qasm").exists()


def test_unroll_command_no_files(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with no .qasm files."""
    # Create empty directory
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()

    # Create a non-qasm file
    text_file = empty_dir / "text.txt"
    text_file.write_text("This is not a QASM file")

    result = runner.invoke(app, ["unroll", str(empty_dir)])

    assert result.exit_code == 0
    assert "No .qasm files present. Nothing to do." in result.output


def test_unroll_command_nonexistent_file(runner: CliRunner):
    """Test the `unroll` CLI command with nonexistent file."""
    result = runner.invoke(app, ["unroll", "nonexistent.qasm"])

    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_unroll_command_nonexistent_directory(runner: CliRunner):
    """Test the `unroll` CLI command with nonexistent directory."""
    result = runner.invoke(app, ["unroll", "nonexistent_directory/"])
    assert result.exit_code == 2
    assert "does not" in result.output and "exist" in result.output


def test_unroll_command_output_to_nonexistent_directory(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with output to nonexistent directory."""
    # Create a test file
    test_file = tmp_path / "test.qasm"
    test_file.write_text("OPENQASM 3.0; qubit[1] q; h q[0];")

    # Try to output to nonexistent directory
    output_path = tmp_path / "nonexistent_dir" / "output.qasm"
    result = runner.invoke(app, ["unroll", str(test_file), "--output", str(output_path)])

    # This should succeed and create the directory
    assert result.exit_code == 0
    assert output_path.exists()


def test_unroll_command_overwrite_and_output_precedence(runner: CliRunner, tmp_path):
    """Test that --output takes precedence over --overwrite."""
    # Create a test file
    test_file = tmp_path / "test.qasm"
    original_content = """
    OPENQASM 3.0;
    include "stdgates.inc";
    gate hgate q { h q; }
    qubit[2] q;
    hgate q[0];
    """
    test_file.write_text(original_content)

    output_file = tmp_path / "output.qasm"
    result = runner.invoke(
        app, ["unroll", str(test_file), "--overwrite", "--output", str(output_file)]
    )

    assert result.exit_code == 0
    assert "Successfully unrolled 1 file" in result.output

    # Check that original file was not changed
    assert test_file.read_text() == original_content
    # Check that output file was created
    assert output_file.exists()


def test_unroll_command_mixed_inputs(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with mixed file and directory inputs."""
    # Create a test file
    test_file = tmp_path / "test.qasm"
    test_file.write_text("OPENQASM 3.0; qubit[1] q; h q[0];")

    # Create a test directory
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    dir_file = test_dir / "dir_test.qasm"
    dir_file.write_text("OPENQASM 3.0; qubit[1] q; x q[0];")

    result = runner.invoke(app, ["unroll", str(test_file), str(test_dir)])

    assert result.exit_code == 0
    assert "Successfully unrolled 2 files" in result.output

    # Check that both files were processed
    assert (tmp_path / "test_unrolled.qasm").exists()
    assert (test_dir / "dir_test_unrolled.qasm").exists()


def test_unroll_command_skip_multiple_files(runner: CliRunner, tmp_path):
    """Test the `unroll` CLI command with multiple skip files."""
    # Create test directory
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # Create multiple test files
    for i in range(4):
        test_file = test_dir / f"test{i}.qasm"
        test_file.write_text(f"OPENQASM 3.0; qubit[1] q; h q[0];")

    # Skip multiple files using multiple --skip flags with full paths
    result = runner.invoke(
        app,
        [
            "unroll",
            str(test_dir),
            "--skip",
            str(test_dir / "test0.qasm"),
            "--skip",
            str(test_dir / "test2.qasm"),
        ],
    )

    assert result.exit_code == 0
    assert "Successfully unrolled 2 files" in result.output

    # Check that only non-skipped files were processed
    assert not (test_dir / "test0_unrolled.qasm").exists()
    assert (test_dir / "test1_unrolled.qasm").exists()
    assert not (test_dir / "test2_unrolled.qasm").exists()
    assert (test_dir / "test3_unrolled.qasm").exists()


# Direct function tests for unroll_qasm
def test_unroll_qasm_function_single_file(capsys, tmp_path):
    """Test unroll_qasm function directly with a single file."""
    # Create a test file
    test_file = tmp_path / "test.qasm"
    test_file.write_text(
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        gate hgate q { h q; }
        qubit[2] q;
        hgate q[0];
        hgate q[1];
        """
    )

    with pytest.raises(typer.Exit) as exc_info:
        unroll_qasm([str(test_file)])

    assert exc_info.value.exit_code == 0

    captured = capsys.readouterr()
    assert "Successfully unrolled 1 file" in captured.out
    assert "Success: unrolled 1 source file" in captured.out

    # Check that unrolled file was created
    unrolled_file = tmp_path / "test_unrolled.qasm"
    assert unrolled_file.exists()

    # Verify content was unrolled (custom gate should be expanded)
    content = unrolled_file.read_text()
    assert "h q[0];" in content
    assert "h q[1];" in content
    assert "gate hgate" not in content  # Custom gate should be removed


def test_unroll_qasm_function_with_invalid_file(capsys, tmp_path):
    """Test unroll_qasm function directly with an invalid file."""
    # Create an invalid test file
    test_file = tmp_path / "invalid.qasm"
    test_file.write_text(
        """
        OPENQASM 3.0;
        include "stdgates.inc";
        qubit[1] q;
        h q[2];  // Invalid: index 2 out of range
        """
    )

    with pytest.raises(typer.Exit) as exc_info:
        unroll_qasm([str(test_file)])

    assert exc_info.value.exit_code == 1

    captured = capsys.readouterr()
    assert "Failed to unroll:" in captured.out
    # The error message has extra spaces, so let's normalize it
    normalized_output = " ".join(captured.out.split())
    assert "Index 2 out of range for register of size 1 in qubit" in normalized_output
