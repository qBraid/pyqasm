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

# Check if dir argument (the directory path) is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

set -e 

echo "Running pre_build.sh"

# Script has an argument which is the project path 
project=$1

# Reset any uncommitted changes which may have been made
git reset --hard HEAD 
git clean -xdf

# Upgrade pip
# python -m pip install --upgrade pip

# Install required packages
uv pip install setuptools wheel cython tomli

# Test if we are running the build for pre-release version
if [[ ${PRE_RELEASE_BUILD:-false} == "true" ]]; then
    echo "Running pre-release changes"

    # Install required packages
    uv pip install -U toml-cli qbraid-core
    deps_exit_code=$?

    if [ $deps_exit_code -ne 0 ]; then
        echo "Failed to install dependencies for pre-release changes"
        exit 1
    fi

    # Set the PRE_RELEASE_VERSION variable
    PRE_RELEASE_VERSION=$(python $project/bin/stamp_pre_release.py pyqasm)
    version_exit_code=$?

    if [ $version_exit_code -ne 0 ]; then
        echo "Failed to set PRE_RELEASE_VERSION"
        exit 1
    fi

    export PRE_RELEASE_VERSION

    # exit if the version is not pre-release
    [[ "$PRE_RELEASE_VERSION" =~ .*(-a\.|-b\.|-rc\.).* ]] && echo "Deploying pre-release version '$PRE_RELEASE_VERSION'" || (echo "not pre-release version"; exit 0)

    # Get the path to .toml file
    PYPROJECT_TOML_PATH="${project}/pyproject.toml"
    DEV_VERSION="${PRE_RELEASE_VERSION}"

    # Update the version in the .toml file
    echo "Setting version to ${DEV_VERSION}"
    toml set --toml-path "$PYPROJECT_TOML_PATH" "project.version" "$DEV_VERSION"

fi

python $project/bin/write_version_file.py

echo "Finished running pre_build.sh"