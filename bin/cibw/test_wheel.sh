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

set -e  # Exit immediately if a command exits with a non-zero status

echo "Running test_wheel.sh"

# Script has an argument which is the project path 
project=$1

# the built wheel is already installed in the test env by cibuildwheel
# just run the tests 
python -m pytest $project/tests
pytest_exit_code=$?

if [ $pytest_exit_code -ne 0 ]; then
    echo "Tests failed for $wheel"
    exit 1
fi

echo "Finished running test_wheel.sh"