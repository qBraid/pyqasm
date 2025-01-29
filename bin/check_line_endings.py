# Copyright (C) 2025 qBraid
#
# This file is part of PyQASM
#
# PyQASM is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for PyQASM, as per Section 15 of the GPL v3.

"""
Check that all Python files in the project have Unix line endings (LF).
"""

import os


def check_line_endings(directory):
    failures = []
    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"):
                continue
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "rb") as f:
                    for line in f:
                        if line.endswith(b"\r\n") or line.endswith(b"\r"):
                            failures.append(file_path)
                            break
            except OSError as e:
                print(f"Could not check file '{file_path}': {e}")

    return failures


if __name__ == "__main__":
    failed_files = []

    pyqasm_root = os.path.join(os.getcwd(), "src", "pyqasm")
    failed_files.extend(check_line_endings(pyqasm_root))

    tests = os.path.join(os.getcwd(), "tests")
    failed_files.extend(check_line_endings(tests))

    bin_dir = os.path.join(os.getcwd(), "bin")
    failed_files.extend(check_line_endings(bin_dir))

    if failed_files:
        raise ValueError(
            f"Error: {len(failed_files)} have incorrect line endings:\n" + "\n".join(failed_files)
        )
    print("\033[92mSuccess: All Python files have Unix line endings (LF).\033[0m")
