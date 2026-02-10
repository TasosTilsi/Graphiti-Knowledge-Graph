"""Input handling for CLI commands.

Provides functions for reading content from positional arguments or stdin,
with proper TTY detection and UTF-8 handling.
"""
import sys
import typer
from typing import Optional


def read_content(positional: Optional[str] = None) -> str:
    """Resolve content from positional argument or stdin.

    Args:
        positional: Optional positional argument containing content

    Returns:
        Content string (from positional arg or stdin)

    Raises:
        typer.BadParameter: If no content provided from either source

    Priority:
        1. Positional argument (if provided)
        2. Stdin (if not a TTY)
        3. Error if neither available

    Example:
        # From positional arg
        content = read_content("hello world")

        # From stdin (when piped)
        # echo "hello" | graphiti add
        content = read_content()
    """
    # Positional arg takes precedence (matches git behavior)
    if positional is not None:
        return positional

    # Check if stdin is available (not a TTY means it's piped)
    if not sys.stdin.isatty():
        # Reconfigure stdin to handle UTF-8 with error replacement
        sys.stdin.reconfigure(encoding='utf-8', errors='replace')

        # Read all content and strip whitespace
        content = sys.stdin.read().strip()

        # Empty content counts as no content
        if not content:
            raise typer.BadParameter(
                "No content provided. Pass as argument or pipe via stdin.\n"
                "Usage: graphiti add 'content' or echo 'content' | graphiti add"
            )

        return content

    # No content from either source
    raise typer.BadParameter(
        "No content provided. Pass as argument or pipe via stdin.\n"
        "Usage: graphiti add 'content' or echo 'content' | graphiti add"
    )
