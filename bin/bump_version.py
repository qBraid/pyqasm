# Copyright (C) 2024 qBraid
#
# This file is part of pyqasm
#
# Pyqasm is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for pyqasm, as per Section 15 of the GPL v3.

"""
Script to bump the major, minor, or patch version in pyproject.toml.

"""
import pathlib
import sys

from qbraid_core.system.versions import (
    bump_version,
    get_latest_package_version,
    update_version_in_pyproject,
)

if __name__ == "__main__":

    package_name = sys.argv[1]
    bump_type = sys.argv[2]

    root = pathlib.Path(__file__).parent.parent.resolve()
    pyproject_toml_path = root / "pyproject.toml"

    current_version = get_latest_package_version(package_name)
    bumped_version = bump_version(current_version, bump_type)
    update_version_in_pyproject(pyproject_toml_path, bumped_version)
    print(bumped_version)
