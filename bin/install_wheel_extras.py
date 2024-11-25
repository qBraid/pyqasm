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
#   python install_wheel_extras.py ./dist --extra extra1 --extra extra2
#   python install_wheel_extras.py ./dist
################################################################################


import argparse
import glob
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Install wheel with extras.")
    parser.add_argument("directory", help="Directory containing the wheel file.")
    parser.add_argument("--extra", action="append", help="Extras to install.")
    args = parser.parse_args()

    # Find the first .whl file in the specified directory
    wheel_files = glob.glob(os.path.join(args.directory, "*.whl"))
    if not wheel_files:
        print("No .whl file found in the specified directory.")
        sys.exit(1)

    wheel_file = wheel_files[0]
    print(f"Wheel file found: {wheel_file}")

    # Build the pip install command with extras, if provided
    extras_str = ",".join(args.extra) if args.extra else ""
    if extras_str:
        install_command = f"python -m pip install '{wheel_file}[{extras_str}]'"
    else:
        install_command = f"python -m pip install '{wheel_file}'"

    # Execute the pip install command
    print(f"Executing: {install_command}")
    os.system(install_command)


if __name__ == "__main__":
    main()
