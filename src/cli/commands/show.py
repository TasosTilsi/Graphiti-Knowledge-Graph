"""Show command for displaying detailed entity information.

Provides rich formatted view of entity details including relationships,
with JSON output option and ambiguous name resolution.
"""
from typing import Annotated, Optional
import typer
from rich.panel import Panel
from rich.text import Text
from src.cli.output import console, print_json, print_error
from src.cli.utils import resolve_scope, EXIT_ERROR


def _find_entity(name: str) -> dict | list[dict]:
    """Stub function that finds entity by name.

    This will be replaced with actual GraphManager integration in future plans.

    Args:
        name: Entity name or ID to find

    Returns:
        Entity dict if unique match found, list of matches if ambiguous, or empty dict if not found
    """
    # Mock entity database
    entities = {
        "Python FastAPI": {
            "id": "ent_001",
            "name": "Python FastAPI",
            "type": "technology",
            "scope": "project",
            "created_at": "2026-01-15T10:30:00Z",
            "updated_at": "2026-01-20T14:22:00Z",
            "tags": ["web", "framework", "async"],
            "content": "FastAPI is a modern, fast (high-performance) web framework for building APIs with Python 3.8+ based on standard Python type hints. Key features include automatic OpenAPI documentation, dependency injection, and async support.",
            "relationships": [
                {"type": "uses", "target": "Pydantic"},
                {"type": "depends_on", "target": "Starlette"},
                {"type": "integrates_with", "target": "SQLAlchemy"}
            ]
        },
        "Database Design": {
            "id": "ent_002",
            "name": "Database Design Pattern",
            "type": "concept",
            "scope": "project",
            "created_at": "2026-01-20T14:22:00Z",
            "updated_at": "2026-01-20T14:22:00Z",
            "tags": ["architecture", "persistence"],
            "content": "Design patterns for structuring database access layers, including repository pattern, unit of work, and data mapper approaches.",
            "relationships": [
                {"type": "related_to", "target": "SQLAlchemy"},
                {"type": "implements", "target": "Repository Pattern"}
            ]
        }
    }

    # Simulate ambiguous match scenario
    if name.lower() == "test":
        return [
            {"name": "Test Entity 1", "id": "test_001", "type": "entity"},
            {"name": "Test Entity 2", "id": "test_002", "type": "entity"},
            {"name": "Testing Framework", "id": "test_003", "type": "technology"}
        ]

    # Find exact or partial match
    if name in entities:
        return entities[name]

    # Try partial match (case-insensitive)
    for entity_name, entity_data in entities.items():
        if name.lower() in entity_name.lower():
            return entity_data

    # Not found
    return {}


def show_command(
    entity: Annotated[str, typer.Argument(help="Entity name or ID")],
    global_scope: Annotated[bool, typer.Option("--global", "-g")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p")] = False,
    format: Annotated[Optional[str], typer.Option("--format", help="Output format: json")] = None,
):
    """Show detailed entity information.

    Displays full entity details including relationships, metadata, and content.
    If entity name is ambiguous, prompts user to choose from matching entities.
    """
    # Resolve scope
    scope, project_root = resolve_scope(global_scope, project_scope)

    # Find entity
    result = _find_entity(entity)

    # Handle not found
    if not result or (isinstance(result, dict) and not result):
        print_error(
            f"Entity '{entity}' not found.",
            suggestion="Try 'graphiti list' to see available entities."
        )
        raise typer.Exit(EXIT_ERROR)

    # Handle ambiguous matches
    if isinstance(result, list):
        console.print(f"\n[yellow]Multiple entities match '{entity}':[/yellow]\n")

        # Display numbered list
        for idx, match in enumerate(result, 1):
            console.print(f"  {idx}. [cyan]{match['name']}[/cyan] ({match['type']}) - ID: {match['id']}")

        # Prompt user to choose
        choice = typer.prompt(f"\nSelect entity [1-{len(result)}]", type=int)

        # Validate choice
        if choice < 1 or choice > len(result):
            print_error(f"Invalid selection: {choice}")
            raise typer.Exit(EXIT_ERROR)

        # Get the selected entity by ID (would need another lookup in real implementation)
        selected_name = result[choice - 1]["name"]
        result = _find_entity(selected_name)

    # Now result is a single entity dict
    entity_data = result

    # JSON output
    if format == "json":
        print_json(entity_data)
        return

    # Rich formatted output
    # Title panel with entity name
    title = Text(entity_data["name"], style="bold cyan")
    console.print(Panel(title, border_style="cyan"))

    # Metadata section
    console.print("\n[bold]Metadata:[/bold]")
    console.print(f"  [dim]ID:[/dim]          {entity_data.get('id', 'N/A')}")
    console.print(f"  [dim]Type:[/dim]        [magenta]{entity_data['type']}[/magenta]")
    console.print(f"  [dim]Scope:[/dim]       {entity_data['scope']}")
    console.print(f"  [dim]Created:[/dim]     [green]{entity_data['created_at']}[/green]")
    console.print(f"  [dim]Updated:[/dim]     [green]{entity_data['updated_at']}[/green]")

    # Tags
    tags = entity_data.get("tags", [])
    if tags:
        tags_str = ", ".join(tags)
        console.print(f"  [dim]Tags:[/dim]        {tags_str}")

    # Content/description
    content = entity_data.get("content", "")
    if content:
        console.print("\n[bold]Content:[/bold]")
        console.print(Panel(content, border_style="dim", padding=(1, 2)))

    # Relationships
    relationships = entity_data.get("relationships", [])
    if relationships:
        console.print("\n[bold]Relationships:[/bold]")
        for rel in relationships:
            rel_type = rel.get("type", "related_to")
            target = rel.get("target", "Unknown")
            console.print(f"  • [yellow]{rel_type}[/yellow] → [cyan]{target}[/cyan]")
    else:
        console.print("\n[dim]No relationships[/dim]")

    console.print()  # Blank line at end
