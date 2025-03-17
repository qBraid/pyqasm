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

# Usage: ./bin/build_sdist.sh [TARGET_PATH]
# TARGET_PATH: The path to the root directory of the project
set -e
set -x

# Set the target path to the argument or default to the
# current working directory
TARGET_PATH="${1:-$(pwd)}"

# Reset the uncommitted changes which may have been made
git reset --hard HEAD
git clean -xdf

PROJECT_ROOT=$(git rev-parse --show-toplevel)

# Create a temporary dir, XXXXX will be replaced by a random string
# of 5 chars to make the directory unique
TEMP_ENV_DIR=$(mktemp -d -t build_env_XXXXX)
python -m venv "$TEMP_ENV_DIR"
source "$TEMP_ENV_DIR/bin/activate"

# Install the necessary packages for building sdist
# NOTE: project deps are not reqd as we are just making a source distribution
python -m pip install --upgrade pip
python -m pip install twine build tomli

python $PROJECT_ROOT/bin/write_version_file.py

python -m build --sdist --outdir "$TARGET_PATH/dist" "$TARGET_PATH"

# Check whether the source distribution will render correctly
twine check "$TARGET_PATH/dist"/*.tar.gz

# Deactivate and remove venv
deactivate
rm -rf "$TEMP_ENV_DIR"