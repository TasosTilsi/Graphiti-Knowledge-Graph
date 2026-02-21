"""MCP server command group for Graphiti CLI.

Provides graphiti mcp serve and graphiti mcp install subcommands.
"""
import typer
from typing import Annotated, Optional

from src.cli.output import console, print_success, print_json, print_error

mcp_app = typer.Typer(
    name="mcp",
    help="MCP server for Claude Code integration",
    no_args_is_help=True,
)


@mcp_app.command(name="serve")
def serve_command(
    transport: Annotated[str, typer.Option("--transport", "-t",
        help="Transport type: stdio or streamable-http")] = "stdio",
    port: Annotated[int, typer.Option("--port", "-p",
        help="HTTP port (streamable-http only)")] = 8000,
):
    """Start the graphiti MCP server.

    stdio transport (default): Claude Code spawns and manages the process.
    streamable-http: Standalone server on localhost:<port>.

    Examples:
        graphiti mcp serve                         # stdio (Claude Code managed)
        graphiti mcp serve --transport streamable-http --port 8080
    """
    from src.mcp_server.server import main as run_server
    run_server(transport=transport, port=port)


@mcp_app.command(name="install")
def install_command(
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing entries")] = False,
    format: Annotated[Optional[str], typer.Option("--format", "-f",
        help="Output format: json")] = None,
):
    """Install graphiti MCP server for Claude Code (zero-config setup).

    Writes the server configuration to ~/.claude.json and installs SKILL.md
    to ~/.claude/skills/graphiti/SKILL.md.

    After running this command, restart Claude Code to activate the server.

    Examples:
        graphiti mcp install         # Install (skip if already present)
        graphiti mcp install --force # Overwrite existing entries
    """
    try:
        from src.mcp_server.install import install_mcp_server
        results = install_mcp_server(force=force)

        if format == "json":
            print_json(results)
            return

        if results["claude_json_updated"]:
            print_success("MCP server registered in ~/.claude.json")
        else:
            console.print("[dim]MCP server already registered in ~/.claude.json (use --force to update)[/dim]")

        if results["skill_md_installed"]:
            from pathlib import Path
            skill_path = Path.home() / ".claude" / "skills" / "graphiti" / "SKILL.md"
            print_success(f"SKILL.md installed to {skill_path}")
        else:
            console.print("[dim]SKILL.md already installed (use --force to update)[/dim]")

        if results["claude_json_updated"] or results["skill_md_installed"]:
            console.print("\n[cyan]Restart Claude Code to activate the graphiti MCP server.[/cyan]")

    except Exception as e:
        print_error(f"Install failed: {str(e)}")
        raise typer.Exit(1)
