# Copyright (C) 2025 qBraid
#
# This file is part of PyQASM
#
# PyQASM is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for PyQASM, as per Section 15 of the GPL v3.

"""
This script is used to write the version to the version file.
It is used to ensure that the version file is always up to date
with the version in pyproject.toml.
"""

import pathlib
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def get_version_from_pyproject(pyproject_path: pathlib.Path) -> str:
    """Extract the version from pyproject.toml file."""
    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except FileNotFoundError:
        print(f"Error: pyproject.toml not found at {pyproject_path}")
        sys.exit(1)
    except KeyError:
        print("Error: Version not found in pyproject.toml")
        sys.exit(1)


def parse_version_tuple(version_string: str) -> tuple[int | str, ...]:
    """Parse a semantic version string into a tuple."""
    parts = version_string.split(".")

    version_tuple = []
    for part in parts[:3]:
        try:
            version_tuple.append(int(part))
        except ValueError:
            version_tuple.append(part)

    if len(parts) > 3:
        extra = ".".join(parts[3:])
        if "-" in extra:
            pre_release, build = extra.split("-", 1)
            version_tuple.extend(pre_release.split("."))
            if "+" in build:
                build = build.split("+", 1)[0]
            version_tuple.extend(build.split("."))
        elif "+" in extra:
            pre_release, build = extra.split("+", 1)
            version_tuple.extend(pre_release.split("."))
        else:
            version_tuple.extend(extra.split("."))

    return tuple(version_tuple)


def write_version_file(version_file_path: pathlib.Path, version: str) -> None:
    """Write the version to a file."""
    version_file_path.parent.mkdir(parents=True, exist_ok=True)
    version_tuple = parse_version_tuple(version)
    content = f"""# file generated during build
# don't change, don't track in version control
TYPE_CHECKING = False
if TYPE_CHECKING:
    VERSION_TUPLE = tuple[int | str, ...]
else:
    VERSION_TUPLE = object

version: str
__version__: str
__version_tuple__: VERSION_TUPLE
version_tuple: VERSION_TUPLE

__version__ = version = '{version}'
__version_tuple__ = version_tuple = {version_tuple}
"""
    version_file_path.write_text(content)
    print(f"Version file written: {version_file_path}")


if __name__ == "__main__":
    root = pathlib.Path(__file__).parent.parent.resolve()
    pyproject_toml = root / "pyproject.toml"
    version_file = root / "src" / "pyqasm" / "_version.py"

    version_str = get_version_from_pyproject(pyproject_toml)
    write_version_file(version_file, version_str)
