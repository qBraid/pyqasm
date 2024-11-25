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

echo "Running test_wheel.sh"

for wheel in dist/*.whl; do
    echo "Installing $wheel"
    python -m pip install $wheel"[test]"
    echo "Running tests for " $wheel
    python -m pytest tests/
    echo "Uninstalling " $wheel
    pip uninstall -y pyqasm 
    echo "Test success for " $wheel
done

echo "Finished running test_wheel.sh"

