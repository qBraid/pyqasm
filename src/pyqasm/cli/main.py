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
Entrypoint for the PyQASM CLI.

"""

import sys

try:
    import typer
    from typing_extensions import Annotated

    from pyqasm.cli.validate import validate_paths_exist, validate_qasm
except ImportError as err:
    print(
        f"Missing required dependency: '{err.name}'.\n\n"
        "Install the dependencies for the PyQASM CLI with:\n\n"
        "\t$ pip install 'pyqasm[cli]'",
        file=sys.stderr,
    )
    sys.exit(1)

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})


def version_callback(value: bool):
    """Show the version and exit."""
    if value:
        # pylint: disable-next=import-outside-toplevel
        from pyqasm._version import __version__  # type: ignore

        typer.echo(f"pyqasm/{__version__}")
        raise typer.Exit(0)


@app.command(name="validate", help="Validate OpenQASM files.")
def validate(  # pylint: disable=dangerous-default-value
    src_paths: Annotated[
        list[str],
        typer.Argument(
            ..., help="Source file or directory paths to validate.", callback=validate_paths_exist
        ),
    ],
    skip_files: Annotated[
        list[str],
        typer.Option(
            "--skip", "-s", help="Files to skip during validation.", callback=validate_paths_exist
        ),
    ] = [],
):
    """Validate OpenQASM files."""
    validate_qasm(src_paths, skip_files)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
):
    """The PyQASM CLI."""
    if ctx.invoked_subcommand and version:
        raise typer.BadParameter("The '--version' option cannot be used with a subcommand.")
    if not ctx.invoked_subcommand and not version:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


if __name__ == "__main__":
    app()
