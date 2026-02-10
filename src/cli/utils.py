"""Shared utility functions for CLI commands.

Provides scope resolution, typo suggestions, confirmation prompts,
exit codes, and other common utilities.
"""
import difflib
import typer
from pathlib import Path
from typing import Optional

from src.models import GraphScope
from src.storage import GraphSelector


# Exit code constants (POSIX convention)
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_BAD_ARGS = 2

# Default result limit per user decision (10-20 range, 15 chosen)
DEFAULT_LIMIT = 15

# Valid CLI commands for typo suggestions
VALID_COMMANDS = [
    "add",
    "search",
    "delete",
    "list",
    "summarize",
    "compact",
    "config",
    "health",
    "show"
]


def suggest_command(invalid: str, cutoff: float = 0.6) -> Optional[str]:
    """Suggest a valid command for a misspelled command name.

    Uses difflib.get_close_matches to find similar command names.

    Args:
        invalid: The misspelled command name
        cutoff: Similarity threshold (0.0-1.0, default 0.6)

    Returns:
        Suggested command name or None if no close match found

    Example:
        >>> suggest_command("serch")
        "search"
        >>> suggest_command("delte")
        "delete"
        >>> suggest_command("xyz")
        None
    """
    matches = difflib.get_close_matches(invalid, VALID_COMMANDS, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def confirm_action(message: str, force: bool = False) -> bool:
    """Prompt user for confirmation before dangerous actions.

    Args:
        message: Confirmation message to display
        force: If True, skip prompt and return True immediately

    Returns:
        True if user confirmed (or force=True), False otherwise

    Example:
        >>> if confirm_action("Delete all nodes?", force=False):
        ...     delete_all()
    """
    if force:
        return True

    return typer.confirm(message, abort=False)


def resolve_scope(
    global_flag: bool = False,
    project_flag: bool = False
) -> tuple[GraphScope, Optional[Path]]:
    """Resolve graph scope from CLI flags.

    Args:
        global_flag: Whether --global was specified
        project_flag: Whether --project was specified

    Returns:
        Tuple of (scope, project_root_path)
        - For global scope: (GraphScope.GLOBAL, None)
        - For project scope: (GraphScope.PROJECT, project_root)
        - For auto-detect: Result from GraphSelector.determine_scope()

    Raises:
        typer.BadParameter: If both flags specified or project scope unavailable

    Example:
        >>> scope, root = resolve_scope(global_flag=True)
        >>> print(scope)
        GraphScope.GLOBAL
    """
    # Cannot specify both --global and --project
    if global_flag and project_flag:
        raise typer.BadParameter("Cannot use both --global and --project")

    # Explicit global scope
    if global_flag:
        return (GraphScope.GLOBAL, None)

    # Explicit project scope
    if project_flag:
        project_root = GraphSelector.find_project_root()
        if not project_root:
            raise typer.BadParameter(
                "Not in a git repository. Cannot use --project scope."
            )
        return (GraphScope.PROJECT, project_root)

    # Auto-detect scope (neither flag specified)
    return GraphSelector.determine_scope()
