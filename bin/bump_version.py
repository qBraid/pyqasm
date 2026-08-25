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
Script to bump the major, minor, or patch version in pyproject.toml.

Pass --alpha to append an -alpha suffix, which opens a development cycle. The
bumped version always sits above the latest release, so a pre-release built from
it can never collide with a version that is already live on PyPI.

"""

import pathlib
import sys

from packaging.version import Version
from qbraid_core.system.versions import (
    bump_version,
    get_latest_package_version,
    update_version_in_pyproject,
)

if __name__ == "__main__":

    package_name = sys.argv[1]
    bump_type = sys.argv[2]
    alpha = "--alpha" in sys.argv[3:]

    root = pathlib.Path(__file__).parent.parent.resolve()
    pyproject_toml_path = root / "pyproject.toml"

    current_version = get_latest_package_version(package_name)
    bumped_version = bump_version(current_version, bump_type)

    if alpha:
        # base_version drops any suffix the bumped version already carries, so
        # that the result is always exactly one -alpha and never 1.2.0-alpha-alpha
        bumped_version = f"{Version(bumped_version).base_version}-alpha"

    update_version_in_pyproject(pyproject_toml_path, bumped_version)
    print(bumped_version)
