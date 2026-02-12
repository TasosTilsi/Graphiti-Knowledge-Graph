"""List command for displaying entities in the knowledge graph.

Provides table, compact, and JSON output formats with filtering by scope,
type, and tags.
"""
from typing import Annotated, Optional
from pathlib import Path
import typer
from src.cli.output import console, print_json, print_table, print_compact, print_warning
from src.cli.utils import resolve_scope, DEFAULT_LIMIT
from src.models import GraphScope
from src.graph import get_service, run_graph_operation


def _list_entities(
    scope: GraphScope,
    project_root: Optional[Path],
    limit: Optional[int],
) -> list[dict]:
    """List entities from the knowledge graph via GraphService.

    Calls GraphService.list_entities() which queries the real Kuzu graph
    database for entities in the specified scope.

    Args:
        scope: Graph scope to list from
        project_root: Project root path (required for PROJECT scope)
        limit: Maximum number of entities to return

    Returns:
        List of entity dictionaries with name, type, created_at, tags, scope, relationship_count
    """
    # Get service and call list operation
    service = get_service()
    entities = run_graph_operation(
        service.list_entities(
            scope=scope,
            project_root=project_root,
            limit=limit,
        )
    )

    # Convert tags from list to string if needed (for table display)
    for entity in entities:
        if "tags" in entity and isinstance(entity["tags"], list):
            entity["tags"] = ", ".join(entity["tags"])

    return entities


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
        entities = _list_entities(scope, project_root, effective_limit)

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
