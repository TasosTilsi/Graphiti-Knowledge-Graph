"""Rich console and output formatting for CLI.

Provides a singleton Rich Console instance and formatting functions for
consistent output across all CLI commands.
"""
from typing import Any, Optional
from rich.console import Console
from rich.table import Table
import json


# Singleton console instances
console = Console()  # Auto-detects TTY
err_console = Console(stderr=True)  # For error output


def print_success(message: str):
    """Print success message with green checkmark prefix.

    Args:
        message: Success message to display
    """
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str, suggestion: Optional[str] = None):
    """Print error message with red X prefix to stderr.

    Args:
        message: Error message to display
        suggestion: Optional suggestion to help user recover
    """
    err_console.print(f"[red]✗[/red] {message}")
    if suggestion:
        err_console.print(f"  [dim]Suggestion: {suggestion}[/dim]")


def print_warning(message: str):
    """Print warning message with yellow warning prefix.

    Args:
        message: Warning message to display
    """
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_table(
    data: list[dict],
    title: Optional[str] = None,
    columns: Optional[list[str]] = None,
):
    """Print data as a Rich Table with auto-detected columns.

    Args:
        data: List of dictionaries to display as table rows
        title: Optional table title
        columns: Optional explicit column list (defaults to dict keys)
    """
    if not data:
        console.print("[dim]No results[/dim]")
        return

    # Auto-detect columns from first row if not provided
    if columns is None:
        columns = list(data[0].keys())

    # Create table with styling
    table = Table(title=title, show_header=True, header_style="bold cyan")

    # Add columns with type-specific styling
    for col in columns:
        col_lower = col.lower()
        if "name" in col_lower or "id" in col_lower:
            table.add_column(col, style="cyan")
        elif "type" in col_lower:
            table.add_column(col, style="magenta")
        elif "date" in col_lower or "time" in col_lower:
            table.add_column(col, style="green")
        else:
            table.add_column(col)

    # Add rows
    for row in data:
        table.add_row(*[str(row.get(col, "")) for col in columns])

    console.print(table)


def print_json(data: dict | list):
    """Print data as syntax-highlighted JSON.

    Args:
        data: Dictionary or list to display as JSON
    """
    console.print_json(data=data)


def print_compact(
    items: list[dict],
    name_key: str = "name",
    type_key: str = "type",
    snippet_key: str = "snippet",
):
    """Print items in compact one-line-per-result format.

    Args:
        items: List of items to display
        name_key: Dictionary key for item name
        type_key: Dictionary key for item type
        snippet_key: Dictionary key for content snippet
    """
    if not items:
        console.print("[dim]No results[/dim]")
        return

    for item in items:
        name = item.get(name_key, "Unknown")
        item_type = item.get(type_key, "")
        snippet = item.get(snippet_key, "")

        # Truncate snippet to 60 characters
        if len(snippet) > 60:
            snippet = snippet[:60] + "..."

        # Format: name (type) - snippet
        type_str = f" ({item_type})" if item_type else ""
        snippet_str = f" - {snippet}" if snippet else ""

        console.print(f"[cyan]{name}[/cyan]{type_str}{snippet_str}")


def format_output(data: dict | list, fmt: Optional[str] = None):
    """Dispatch function for formatting output based on format type.

    Args:
        data: Data to format and display
        fmt: Output format ('json', 'table', 'compact', or None for auto)

    Note:
        This function prints directly and returns None.
    """
    if fmt == "json":
        print_json(data)
    elif fmt == "table" and isinstance(data, list):
        print_table(data)
    elif fmt == "compact" and isinstance(data, list):
        print_compact(data)
    else:
        # Auto-detect: list -> table, dict -> json
        if isinstance(data, list):
            print_table(data)
        else:
            print_json(data)
