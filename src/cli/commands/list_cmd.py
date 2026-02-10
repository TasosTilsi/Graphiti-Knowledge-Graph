"""List command for displaying entities in the knowledge graph.

Provides table, compact, and JSON output formats with filtering by scope,
type, and tags.
"""
from typing import Annotated, Optional
import typer
from src.cli.output import console, print_json, print_table, print_compact, print_warning
from src.cli.utils import resolve_scope, DEFAULT_LIMIT


def _list_entities() -> list[dict]:
    """Stub function that returns mock entity data.

    This will be replaced with actual GraphManager integration in future plans.

    Returns:
        List of entity dictionaries with name, type, created_at, tags, scope, relationship_count
    """
    return [
        {
            "name": "Python FastAPI",
            "type": "technology",
            "created_at": "2026-01-15T10:30:00Z",
            "tags": "web, framework, async",
            "scope": "project",
            "relationship_count": 12
        },
        {
            "name": "Database Design Pattern",
            "type": "concept",
            "created_at": "2026-01-20T14:22:00Z",
            "tags": "architecture, persistence",
            "scope": "project",
            "relationship_count": 8
        },
        {
            "name": "Claude Preferences",
            "type": "preference",
            "created_at": "2026-01-10T08:15:00Z",
            "tags": "ai, settings",
            "scope": "global",
            "relationship_count": 3
        },
        {
            "name": "Git Workflow",
            "type": "process",
            "created_at": "2026-01-18T11:45:00Z",
            "tags": "version-control, workflow",
            "scope": "global",
            "relationship_count": 15
        },
        {
            "name": "Project Dependencies",
            "type": "technical-detail",
            "created_at": "2026-01-22T09:10:00Z",
            "tags": "dependencies, pyproject",
            "scope": "project",
            "relationship_count": 24
        },
        {
            "name": "Security Best Practices",
            "type": "guideline",
            "created_at": "2026-01-12T16:30:00Z",
            "tags": "security, standards",
            "scope": "global",
            "relationship_count": 7
        },
        {
            "name": "API Authentication",
            "type": "implementation",
            "created_at": "2026-01-25T13:20:00Z",
            "tags": "auth, security, api",
            "scope": "project",
            "relationship_count": 9
        },
        {
            "name": "Testing Strategy",
            "type": "process",
            "created_at": "2026-01-14T10:00:00Z",
            "tags": "testing, qa, pytest",
            "scope": "project",
            "relationship_count": 11
        }
    ]


def list_command(
    global_scope: Annotated[bool, typer.Option("--global", "-g", help="List from global scope")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p", help="List from project scope")] = False,
    type_filter: Annotated[Optional[str], typer.Option("--type", help="Filter by type: entity, relationship")] = None,
    tag: Annotated[Optional[list[str]], typer.Option("--tag", "-t", help="Filter by tag")] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max items to show")] = DEFAULT_LIMIT,
    all_results: Annotated[bool, typer.Option("--all", help="Show all items")] = False,
    compact: Annotated[bool, typer.Option("--compact", "-c", help="One-line-per-item view")] = False,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Output format: json")] = None,
):
    """List entities in the knowledge graph.

    Shows entities in table format by default, with options for compact
    one-line view or JSON output. Supports filtering by scope, type, and tags.
    """
    # Resolve scope
    scope, project_root = resolve_scope(global_scope, project_scope)

    # Determine effective limit (None if --all)
    effective_limit = None if all_results else limit

    # Load entities with spinner
    with console.status("[cyan]Loading entities...", spinner="dots"):
        entities = _list_entities()

    # Check if empty
    if not entities:
        print_warning("No entities found.")
        raise typer.Exit(0)

    # Apply limit if specified
    total_count = len(entities)
    if effective_limit is not None:
        entities = entities[:effective_limit]

    # Output based on format
    if format == "json":
        print_json(entities)
    elif compact:
        # For compact view, add snippet field from tags
        for entity in entities:
            entity["snippet"] = entity.get("tags", "")
        print_compact(entities, name_key="name", type_key="type", snippet_key="snippet")
    else:
        # Table view with specific columns
        columns = ["name", "type", "tags", "relationship_count", "created_at"]
        # Rename relationship_count to "Relations" for display
        display_entities = []
        for entity in entities:
            display_entity = entity.copy()
            display_entity["Relations"] = display_entity.pop("relationship_count")
            display_entity["Created"] = display_entity.pop("created_at")
            display_entities.append(display_entity)

        print_table(
            display_entities,
            columns=["name", "type", "tags", "Relations", "Created"]
        )

    # Print count summary
    if effective_limit is not None and total_count > effective_limit:
        console.print(f"\n[dim]Showing {len(entities)} of {total_count} entities[/dim]")
    else:
        console.print(f"\n[dim]{len(entities)} entities[/dim]")
