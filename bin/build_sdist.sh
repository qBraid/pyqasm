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

python -m venv build_env
source build_env/bin/activate

python -m pip install numpy cython
python -m pip install twine build

cd pyqasm
python -m build --sdist --outdir dist

# Check whether the source distribution will render correctly
twine check dist/*.tar.gz

# Deactivate the virtual environment and remove it
deactivate
rm -rf build_env