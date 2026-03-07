#!/bin/bash

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

"$SCRIPT_DIR/install_wheel_extras.sh" "$TARGET_PATH/dist" --type sdist --extra cli --extra test --extra pulse

# Print the installed version
python -c "import pyqasm; print('Installed pyqasm version:', pyqasm.__version__)"

# Verify the installed version if release build
if [[ ${RELEASE_BUILD:-false} == "true" ]]; then
    echo "Testing release build version"
    
    # get version from importlib 
    IMPORTLIB_VERSION=$(python -c "import importlib.metadata; print(importlib.metadata.version('pyqasm'))")
    echo "Importlib version: $IMPORTLIB_VERSION"
    
    # get version from __version__ 
    VERSION_ATTRIBUTE=$(python -c "import pyqasm; print(pyqasm.__version__)")
    echo "Version attribute: $VERSION_ATTRIBUTE"
    
    # check if the versions are the same
    if [[ $IMPORTLIB_VERSION != $VERSION_ATTRIBUTE ]]; then
        echo "Versions do not match"
        exit 1
    fi
fi

# Run the tests on the installed source distribution
pytest "$TARGET_PATH/tests"

# Deactivate and remove venv
deactivate
rm -rf "$TEMP_ENV_DIR"