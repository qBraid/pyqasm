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

set -e 

echo "Running build_wheels.sh"

python -m pip install cibuildwheel
python -m cibuildwheel --output-dir dist
build_exit_code=$?

if [ $build_exit_code -ne 0 ]; then
    echo "Failed to build wheel"
    exit 1
fi

echo "Finished running build_wheels.sh"