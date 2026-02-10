"""CLI foundation for Graphiti knowledge graph operations.

This module provides the Typer app instance that all commands register with,
along with the entry point function for console_scripts.
"""
import sys
import typer
from typing import Optional
from src.cli.output import err_console, print_error


# Create main Typer app
app = typer.Typer(
    name="graphiti",
    help="Knowledge graph operations for global preferences and project memory",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit"
    ),
):
    """Main callback that handles version display and unknown command suggestions."""
    if version:
        # Import here to avoid circular dependency
        import importlib.metadata
        try:
            version_str = importlib.metadata.version("graphiti-knowledge-graph")
        except importlib.metadata.PackageNotFoundError:
            version_str = "0.1.0 (development)"
        typer.echo(f"graphiti version {version_str}")
        raise typer.Exit(0)

    # If command invoked but not found, suggest alternatives
    if ctx.invoked_subcommand is None and ctx.resilient_parsing is False:
        # This is just --help or no command, which is handled by no_args_is_help
        pass


def cli_entry():
    """Entry point for console_scripts.

    This function is registered in pyproject.toml as both 'graphiti' and 'gk'.
    """
    try:
        app()
    except typer.BadParameter as e:
        print_error(str(e))
        sys.exit(2)  # EXIT_BAD_ARGS
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)  # EXIT_ERROR


# Command registration will happen in subsequent plans
# Commands to be added:
# - add (plan 02)
# - search (plan 03)
# - delete, list, summarize (plan 04)
# - compact, config, health, show (plan 05)
