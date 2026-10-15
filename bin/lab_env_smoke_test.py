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

"""
Smoke test for a pyqasm Lab environment. Run it with the environment's own Python.

Usage:
    <env>/pyenv/bin/python bin/lab_env_smoke_test.py VERSION

"""

import platform
import sys

import ipykernel  # pylint: disable=unused-import # noqa: F401 - Lab needs it to start the kernel

import pyqasm

PROGRAM = """
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
h q[0];
cx q[0], q[1];
"""


def main() -> None:
    """Check the pyqasm version, then unroll and validate a small program."""
    expected = sys.argv[1]
    if pyqasm.__version__ != expected:
        sys.exit(f"pyqasm {pyqasm.__version__} installed, expected {expected}")

    module = pyqasm.loads(PROGRAM)
    module.unroll()
    module.validate()
    print(pyqasm.dumps(module))
    print(f"pyqasm {pyqasm.__version__}, Python {platform.python_version()}, {platform.machine()}")


if __name__ == "__main__":
    main()
