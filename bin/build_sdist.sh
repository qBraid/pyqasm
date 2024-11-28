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

# Usage: ./bin/build_sdist.sh [TARGET_PATH]
# TARGET_PATH: The path to the root directory of the project
set -e
set -x

# Set the target path to the argument or default to the
# current working directory
TARGET_PATH="${1:-$(pwd)}"

# Create a temporary dir, XXXXX will be replaced by a random string
# of 5 chars to make the directory unique
TEMP_ENV_DIR=$(mktemp -d -t build_env_XXXXX)
python -m venv "$TEMP_ENV_DIR"
source "$TEMP_ENV_DIR/bin/activate"

# Install the necessary packages for building sdist 
# NOTE: project deps are not reqd as we are just making a source distribution
python -m pip install twine build

python -m build --sdist --outdir "$TARGET_PATH/dist" "$TARGET_PATH"

# Check whether the source distribution will render correctly
twine check "$TARGET_PATH/dist"/*.tar.gz

# Deactivate and remove venv
deactivate
rm -rf "$TEMP_ENV_DIR"