"""Add command for Graphiti CLI.

Adds content to the knowledge graph with automatic scope detection,
tagging, and source provenance tracking.
"""
import typer
from typing import Annotated, Optional
from datetime import datetime
from pathlib import Path

from src.cli.input import read_content
from src.cli.output import console, print_success, print_json, print_error
from src.cli.utils import resolve_scope, EXIT_SUCCESS, EXIT_ERROR
from src.models import GraphScope
from src.config.paths import get_project_db_path


def _detect_source() -> str:
    """Auto-detect source provenance.

    Returns:
        Source string (git remote URL if in repo, else "manual")
    """
    try:
        import subprocess
        # Try to get git remote URL
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Default to manual if not in git repo or git not available
    return "manual"


def _ensure_project_directory(project_root: Path) -> None:
    """Ensure .graphiti/ directory exists for project scope.

    Args:
        project_root: Root directory of the project
    """
    graphiti_dir = project_root / ".graphiti"
    if not graphiti_dir.exists():
        graphiti_dir.mkdir(parents=True, exist_ok=True)


def _add_entity(
    content: str,
    scope: GraphScope,
    project_root: Optional[Path],
    tags: Optional[list[str]],
    source: str,
) -> dict:
    """Stub function to prepare entity data for storage layer.

    This is a temporary stub that prepares the data structure and returns
    a mock result. Will be replaced with actual graph operations when
    storage layer is fully wired.

    Args:
        content: Content to add to knowledge graph
        scope: Graph scope (GLOBAL or PROJECT)
        project_root: Project root path (if PROJECT scope)
        tags: Optional list of tags for categorization
        source: Source provenance

    Returns:
        Dictionary with entity metadata (name, type, scope, created_at)
    """
    # Log what would be done
    scope_str = f"{scope.value} ({project_root})" if project_root else scope.value
    console.log(f"[dim]Would add entity to {scope_str} scope[/dim]")
    console.log(f"[dim]Content: {content[:100]}...[/dim]" if len(content) > 100 else f"[dim]Content: {content}[/dim]")
    console.log(f"[dim]Source: {source}[/dim]")
    if tags:
        console.log(f"[dim]Tags: {', '.join(tags)}[/dim]")

    # Return mock result with realistic data
    # In real implementation, this would:
    # 1. Get database connection for scope
    # 2. Sanitize content (security layer)
    # 3. Extract entities/relationships (LLM layer)
    # 4. Write to graph (storage layer)
    # 5. Return actual entity metadata

    return {
        "name": f"entity_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "type": "entity",
        "scope": scope.value,
        "created_at": datetime.now().isoformat(),
        "tags": tags or [],
        "source": source,
        "content_length": len(content),
    }


def add_command(
    content: Annotated[Optional[str], typer.Argument(help="Content to add to knowledge graph")] = None,
    tag: Annotated[Optional[list[str]], typer.Option("--tag", "-t", help="Tags for categorization (can repeat)")] = None,
    source: Annotated[Optional[str], typer.Option("--source", "-s", help="Source provenance (auto-detected if omitted)")] = None,
    global_scope: Annotated[bool, typer.Option("--global", "-g", help="Use global scope")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p", help="Use project scope")] = False,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Output format: json")] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress success messages")] = False,
):
    """Add content to the knowledge graph.

    Content can be provided as a positional argument or piped via stdin.

    Examples:
        graphiti add "Meeting notes from 2026-02-11"
        echo "Important concept" | graphiti add
        graphiti add "Feature idea" --tag roadmap --tag feature
        graphiti add "Global preference" --global
    """
    try:
        # 1. Resolve content from positional arg or stdin
        resolved_content = read_content(content)

        # 2. Resolve scope
        scope, root = resolve_scope(global_scope, project_scope)

        # 3. Auto-detect source if not provided
        if source is None:
            source = _detect_source()

        # 4. Auto-init .graphiti/ directory for project scope
        if scope == GraphScope.PROJECT and root:
            _ensure_project_directory(root)

        # 5. Add entity with spinner
        with console.status("Adding to knowledge graph..."):
            result = _add_entity(
                content=resolved_content,
                scope=scope,
                project_root=root,
                tags=tag,
                source=source,
            )

        # 6. Output result
        if format == "json":
            print_json(result)
        elif not quiet:
            entity_name = result.get("name", "entity")
            tags_str = f" (tags: {', '.join(result['tags'])})" if result.get("tags") else ""
            print_success(f"Added {entity_name} to {scope.value} scope{tags_str}")

    except typer.BadParameter:
        # Re-raise parameter errors (already formatted by typer)
        raise
    except Exception as e:
        print_error(f"Failed to add content: {str(e)}")
        raise typer.Exit(EXIT_ERROR)


# Note: Tag handling is implemented via --tag flag
# Future enhancement: LLM-based auto-categorization when tags not provided
# This would analyze content and suggest/apply relevant tags automatically
