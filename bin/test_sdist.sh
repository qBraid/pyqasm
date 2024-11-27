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

# Usage: ./bin/test_sdist.sh [TARGET_PATH]
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

# Install the source distribution
SCRIPT_DIR="$TARGET_PATH/bin"

"$SCRIPT_DIR/install_wheel_extras.sh" "$TARGET_PATH/dist" --type sdist --extra cli --extra test

# Run the tests on the installed source distribution
pytest "$TARGET_PATH/tests"

# Deactivate and remove venv
deactivate
rm -rf "$TEMP_ENV_DIR"