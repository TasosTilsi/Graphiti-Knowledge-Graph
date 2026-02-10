"""Search command for Graphiti CLI.

Searches the knowledge graph with semantic (default) or exact matching,
supporting filters, result formatting, and pagination.
"""
import typer
from typing import Annotated, Optional
from datetime import datetime

from src.cli.output import console, print_table, print_compact, print_json, print_warning
from src.cli.utils import resolve_scope, DEFAULT_LIMIT, EXIT_SUCCESS, EXIT_ERROR
from src.models import GraphScope


def _search_entities(
    query: str,
    scope: GraphScope,
    exact: bool,
    since: Optional[str],
    before: Optional[str],
    type_filter: Optional[str],
    tags: Optional[list[str]],
    limit: Optional[int],
) -> list[dict]:
    """Stub function to search entities in the knowledge graph.

    This is a temporary stub that returns mock results for testing the
    CLI flow. Will be replaced with actual graph search operations when
    storage and LLM layers are fully integrated.

    Args:
        query: Search query string
        scope: Graph scope to search in
        exact: Whether to use exact matching (True) or semantic (False)
        since: Filter results after this date/duration
        before: Filter results before this date
        type_filter: Filter by type (entity, relationship)
        tags: Filter by tags
        limit: Maximum number of results (None for unlimited)

    Returns:
        List of result dictionaries with name, type, snippet, score, created_at, scope, tags
    """
    # Log search parameters
    mode = "exact" if exact else "semantic"
    console.log(f"[dim]Searching in {scope.value} scope using {mode} mode[/dim]")
    console.log(f"[dim]Query: {query}[/dim]")
    if since:
        console.log(f"[dim]Since: {since}[/dim]")
    if before:
        console.log(f"[dim]Before: {before}[/dim]")
    if type_filter:
        console.log(f"[dim]Type filter: {type_filter}[/dim]")
    if tags:
        console.log(f"[dim]Tags: {', '.join(tags)}[/dim]")
    if limit:
        console.log(f"[dim]Limit: {limit}[/dim]")

    # Return mock results for testing
    # In real implementation, this would:
    # 1. Get database connection for scope
    # 2. If semantic: use LLM to generate query embedding
    # 3. If exact: use literal string matching
    # 4. Apply filters (since, before, type, tags)
    # 5. Execute graph query with filters
    # 6. Return actual results with relevance scores

    mock_results = [
        {
            "name": "meeting_notes_20260211",
            "type": "entity",
            "snippet": f"Meeting notes discussing {query} and related topics...",
            "score": 0.95,
            "created_at": "2026-02-11T00:00:00",
            "scope": scope.value,
            "tags": ["meeting", "notes"],
        },
        {
            "name": "project_roadmap",
            "type": "entity",
            "snippet": f"Roadmap entry mentioning {query} as a key milestone",
            "score": 0.87,
            "created_at": "2026-02-10T14:30:00",
            "scope": scope.value,
            "tags": ["roadmap", "planning"],
        },
        {
            "name": "research_findings",
            "type": "entity",
            "snippet": f"Research document about {query} with detailed analysis",
            "score": 0.82,
            "created_at": "2026-02-09T09:15:00",
            "scope": scope.value,
            "tags": ["research"],
        },
    ]

    # Apply limit if specified
    if limit is not None:
        mock_results = mock_results[:limit]

    return mock_results


def search_command(
    query: Annotated[str, typer.Argument(help="Search query")],
    exact: Annotated[bool, typer.Option("--exact", "-e", help="Literal string matching instead of semantic")] = False,
    global_scope: Annotated[bool, typer.Option("--global", "-g", help="Search global scope only")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p", help="Search project scope only")] = False,
    since: Annotated[Optional[str], typer.Option("--since", help="Filter results after date/duration (e.g., '7d', '2024-01-01')")] = None,
    before: Annotated[Optional[str], typer.Option("--before", help="Filter results before date")] = None,
    type_filter: Annotated[Optional[str], typer.Option("--type", help="Filter by type: entity, relationship")] = None,
    tag: Annotated[Optional[list[str]], typer.Option("--tag", "-t", help="Filter by tag")] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max results to return")] = DEFAULT_LIMIT,
    all_results: Annotated[bool, typer.Option("--all", help="Return all results (no limit)")] = False,
    compact: Annotated[bool, typer.Option("--compact", "-c", help="One-line-per-result view")] = False,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Output format: json")] = None,
):
    """Search the knowledge graph.

    Supports semantic search (default) and exact literal matching with various
    filters and formatting options.

    Examples:
        graphiti search "meeting notes"
        graphiti search "API design" --exact
        graphiti search "roadmap" --since 7d --tag planning
        graphiti search "architecture" --compact
        graphiti search "decisions" --format json
    """
    try:
        # 1. Resolve scope
        scope, _ = resolve_scope(global_scope, project_scope)

        # 2. Determine effective limit
        effective_limit = None if all_results else limit

        # 3. Search with spinner
        with console.status("Searching knowledge graph..."):
            results = _search_entities(
                query=query,
                scope=scope,
                exact=exact,
                since=since,
                before=before,
                type_filter=type_filter,
                tags=tag,
                limit=effective_limit,
            )

        # 4. Handle no results
        if not results:
            print_warning(f"No results found for '{query}'")
            return

        # 5. Format output based on flags
        if format == "json":
            print_json(results)
        elif compact:
            print_compact(results)
        else:
            # Default: table view
            # Reformat results for table with selected columns
            table_data = []
            for r in results:
                table_data.append({
                    "Name": r["name"],
                    "Type": r["type"],
                    "Snippet": r["snippet"][:60] + "..." if len(r["snippet"]) > 60 else r["snippet"],
                    "Score": f"{r['score']:.2f}" if "score" in r else "N/A",
                    "Created": r["created_at"].split("T")[0],  # Just the date
                })
            print_table(table_data, columns=["Name", "Type", "Snippet", "Score", "Created"])

        # 6. Print result count
        result_count = len(results)
        if all_results or effective_limit is None:
            console.print(f"\n[dim]{result_count} results[/dim]")
        else:
            # Show total available if we're limiting
            console.print(f"\n[dim]{result_count} of {result_count} results[/dim]")
            if result_count >= limit:
                console.print("[dim](use --all for complete list)[/dim]")

    except typer.BadParameter:
        # Re-raise parameter errors (already formatted by typer)
        raise
    except Exception as e:
        from src.cli.output import print_error
        print_error(f"Search failed: {str(e)}")
        raise typer.Exit(EXIT_ERROR)
