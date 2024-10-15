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

################################################################################
# Description:
# Finds and installs the first .whl file in a specified directory including
# specified extras. The directory path is passed as the first argument.
# Extras are specified with --extra flags.
#
# Example Usage:
#   ./install_wheel_extras.sh ./dist --extra extra1 --extra extra2
#   ./install_wheel_extras.sh ./dist
################################################################################

# Check if at least one argument (the directory path) is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <directory> [--extra <extra>...]"
    exit 1
fi

# The first argument is the directory path
DIST=$1
shift # Remove the directory path from the arguments list

# Initialize extras array
EXTRAS=()

# Parse remaining arguments for --extra flags
while (( "$#" )); do
    case "$1" in
        --extra)
            EXTRAS+=($2)
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Combine extras into a comma-separated string
EXTRAS_STR=$(IFS=, ; echo "${EXTRAS[*]}")

# Use ls and grep to find the first .whl file
WHEEL_FILE=$(ls $DIST | grep '\.whl$' | head -n 1)

if [ -z "$WHEEL_FILE" ]; then
    echo "No .whl file found in the specified directory."
    exit 1
else
    echo "Wheel file found: $WHEEL_FILE"
fi

# Build the pip install command with extras, if provided
if [ -n "$EXTRAS_STR" ]; then
    INSTALL_COMMAND="python3 -m pip install '$DIST/$WHEEL_FILE[$EXTRAS_STR]'"
else
    INSTALL_COMMAND="python3 -m pip install '$DIST/$WHEEL_FILE'"
fi

# Execute the pip install command
echo "Executing: $INSTALL_COMMAND"
eval $INSTALL_COMMAND
