#!/bin/bash

# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

# Check if dir argument (the directory path) is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

set -e  # Exit immediately if a command exits with a non-zero status

echo "Running test_wheel.sh"

# Script has an argument which is the project path 
project=$1

# the built wheel is already installed in the test env by cibuildwheel
# just run the tests 
python -m pytest $project/tests
pytest_exit_code=$?

if [ $pytest_exit_code -ne 0 ]; then
    echo "Tests failed for $wheel"
    exit 1
fi

echo "Finished running test_wheel.sh"