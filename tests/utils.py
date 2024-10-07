# Copyright (C) 2024 qBraid
#
# This file is part of the pyqasm
#
# The pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the pyqasm, as per Section 15 of the GPL v3.


def check_unrolled_qasm(unrolled_qasm, expected_qasm):
    """Check that the unrolled qasm matches the expected qasm.

    Args:
        unrolled_qasm (str): The unrolled qasm to check.
        expected_qasm (str): The expected qasm to check against

    Raises:
        AssertionError: If the unrolled qasm does not match the expected qasm.
    """
    # check line by line
    unrolled_qasm = unrolled_qasm.split("\n")
    expected_qasm = expected_qasm.split("\n")
    assert len(unrolled_qasm) == len(expected_qasm)

    for unrolled_line, expected_line in zip(unrolled_qasm, expected_qasm):
        print(unrolled_line, expected_line)
        assert unrolled_line.strip() == expected_line.strip()
