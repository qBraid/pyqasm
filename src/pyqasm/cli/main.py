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
Entrypoint for the PyQASM CLI.

"""

import sys
from typing import Optional

try:
    import typer
    from typing_extensions import Annotated

    from pyqasm.cli.unroll import unroll_qasm
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
        from pyqasm import __version__  # type: ignore

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


@app.command(name="unroll", help="Unroll OpenQASM files.")
def unroll(  # pylint: disable=dangerous-default-value
    src_paths: Annotated[
        list[str],
        typer.Argument(
            ..., help="Source file or directory paths to unroll.", callback=validate_paths_exist
        ),
    ],
    skip_files: Annotated[
        list[str],
        typer.Option(
            "--skip", "-s", help="Files to skip during unrolling.", callback=validate_paths_exist
        ),
    ] = [],
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite original files instead of creating new ones."),
    ] = False,
    output: Annotated[
        Optional[str],
        typer.Option(
            "--output", "-o", help="Output file path (can only be used with a single input file)."
        ),
    ] = None,
):
    """Unroll OpenQASM files."""
    # Validate that output_path is only used with a single file
    if output and len(src_paths) > 1:
        raise typer.BadParameter("--output can only be used with a single input file")

    unroll_qasm(src_paths, skip_files, overwrite, output)


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
