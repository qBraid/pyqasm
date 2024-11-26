#!/bin/bash

# Copyright (C) 2024 qBraid
#
# This file is part of the pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the pyqasm, as per Section 15 of the GPL v3.

set -e
set -x

# Move up 1 level to create the virtual
# environment outside of the source folder
cd ..

python -m venv test_env
source test_env/bin/activate

# Install the source distribution
python -m pip install pyqasm/dist/*.tar.gz

# Install test and CLI extra 
pip install pytest
pip install "typer>=0.12.1" typing-extensions "rich>=10.11.0"

# Run the tests on the installed source distribution
pytest pyqasm/tests

# Deactivate the virtual environment and remove it
deactivate
rm -rf build_env