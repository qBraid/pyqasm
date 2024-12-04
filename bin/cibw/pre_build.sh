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

set -e 

echo "Running pre_build.sh"

# Script has an argument which is the project path 
project=$1

# Upgrade pip
python -m pip install --upgrade pip

# Install required packages
pip install setuptools wheel cython

# Test if we are running the build for pre-release version 
if [[ ${PRE_RELEASE_BUILD:-false} == "true" ]]; then
    echo "Running pre-release changes"

    # Install required packages
    python -m pip install -U toml-cli qbraid-core
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


echo "Finished running pre_build.sh"