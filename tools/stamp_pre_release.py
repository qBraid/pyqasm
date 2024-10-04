# Copyright (C) 2024 qBraid
#
# This file is part of the qBraid-SDK
#
# The qBraid-SDK is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the qBraid-SDK, as per Section 15 of the GPL v3.

"""
Script for getting/bumping the next pre-release version.

"""
import pathlib
import sys

from qbraid_core.system.versions import get_prelease_version

if __name__ == "__main__":

    package_name = sys.argv[1]
    root = pathlib.Path(__file__).parent.parent.resolve()
    version = get_prelease_version(root, package_name)
    print(version)
