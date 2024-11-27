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

echo "Running pre_test.sh"

# dump system info in stdout 
echo "System info: "
python -c "import platform; print(platform.platform())"

echo "Finished running pre_test.sh"