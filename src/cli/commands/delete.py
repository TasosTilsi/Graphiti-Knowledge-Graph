"""Delete command for removing entities from the knowledge graph.

Provides bulk entity deletion with confirmation prompts, ambiguous name
resolution, and JSON/quiet output modes.
"""
from typing import Annotated, Optional
import typer
from rich.table import Table
from src.cli.output import console, print_json, print_error, print_success
from src.cli.utils import resolve_scope, confirm_action, EXIT_ERROR, EXIT_SUCCESS


def _resolve_entity(name: str) -> dict | list[dict] | None:
    """Stub function that resolves entity name to entity object.

    This will be replaced with actual GraphManager integration in future plans.

    Args:
        name: Entity name or ID to resolve

    Returns:
        Entity dict if unique match, list of matches if ambiguous, None if not found
    """
    # Mock entity database
    entities = {
        "Python FastAPI": {
            "id": "ent_001",
            "name": "Python FastAPI",
            "type": "technology",
            "scope": "project"
        },
        "Database Design Pattern": {
            "id": "ent_002",
            "name": "Database Design Pattern",
            "type": "concept",
            "scope": "project"
        },
        "Claude Preferences": {
            "id": "ent_003",
            "name": "Claude Preferences",
            "type": "preference",
            "scope": "global"
        },
        "test_entity": {
            "id": "ent_999",
            "name": "test_entity",
            "type": "test",
            "scope": "project"
        }
    }

    # Simulate ambiguous match scenario
    if name.lower() == "test":
        return [
            {"id": "test_001", "name": "Test Entity 1", "type": "entity", "scope": "project"},
            {"id": "test_002", "name": "Test Entity 2", "type": "entity", "scope": "project"},
            {"id": "test_003", "name": "Testing Framework", "type": "technology", "scope": "project"}
        ]

    # Find exact or partial match
    if name in entities:
        return entities[name]

    # Try partial match (case-insensitive)
    for entity_name, entity_data in entities.items():
        if name.lower() in entity_name.lower():
            return entity_data

    # Not found
    return None


def _delete_entities(entities: list[dict]) -> int:
    """Stub function that deletes entities from the graph.

    This will be replaced with actual GraphManager integration in future plans.

    Args:
        entities: List of entity dicts to delete

    Returns:
        Count of entities successfully deleted
    """
    # Mock deletion - always succeeds
    return len(entities)


def delete_command(
    entities: Annotated[list[str], typer.Argument(help="Entity names or IDs to delete")],
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation prompt")] = False,
    global_scope: Annotated[bool, typer.Option("--global", "-g")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p")] = False,
    format: Annotated[Optional[str], typer.Option("--format", help="Output format: json")] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
):
    """Delete entities from the knowledge graph.

    Supports bulk deletion with confirmation prompts. Use --force to skip
    confirmation. Resolves ambiguous entity names by prompting user to choose.
    """
    # Resolve scope
    scope, project_root = resolve_scope(global_scope, project_scope)

    # Resolve all entity names to actual entities
    resolved_entities = []
    for entity_name in entities:
        result = _resolve_entity(entity_name)

        # Handle not found
        if result is None:
            print_error(
                f"Entity '{entity_name}' not found.",
                suggestion="Try 'graphiti list' to see available entities."
            )
            raise typer.Exit(EXIT_ERROR)

        # Handle ambiguous matches
        if isinstance(result, list):
            console.print(f"\n[yellow]Multiple entities match '{entity_name}':[/yellow]\n")

            # Display numbered list
            for idx, match in enumerate(result, 1):
                console.print(f"  {idx}. [cyan]{match['name']}[/cyan] ({match['type']}) - ID: {match['id']}")

            # Prompt user to choose
            choice = typer.prompt(f"\nSelect entity [1-{len(result)}]", type=int)

            # Validate choice
            if choice < 1 or choice > len(result):
                print_error(f"Invalid selection: {choice}")
                raise typer.Exit(EXIT_ERROR)

            # Use selected entity
            resolved_entities.append(result[choice - 1])
        else:
            # Single match
            resolved_entities.append(result)

    # Display what will be deleted and confirm
    if not force:
        console.print("\n[yellow]The following entities will be deleted:[/yellow]\n")

        # Create table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Scope")

        for entity in resolved_entities:
            table.add_row(entity["name"], entity["type"], entity["scope"])

        console.print(table)
        console.print()

        # Confirm action
        if not confirm_action(f"Delete {len(resolved_entities)} entities?", force=force):
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(EXIT_SUCCESS)

    # Delete entities with spinner
    with console.status(f"[cyan]Deleting {len(resolved_entities)} entities...", spinner="dots"):
        deleted_count = _delete_entities(resolved_entities)

    # Output results
    entity_names = [e["name"] for e in resolved_entities]

    if format == "json":
        print_json({
            "deleted": deleted_count,
            "entities": entity_names
        })
    elif not quiet:
        if deleted_count == 1:
            print_success(f"Deleted 1 entity: {entity_names[0]}")
        else:
            print_success(f"Deleted {deleted_count} entities")

    raise typer.Exit(EXIT_SUCCESS)
