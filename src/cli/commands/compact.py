"""Compact command for knowledge graph maintenance.

Merges and deduplicates graph content, rebuilding indexes for optimal performance.
This is a destructive operation that requires confirmation.
"""
import typer
from typing import Annotated, Optional

from src.models import GraphScope
from src.cli.output import console, print_error, print_json, print_success
from src.cli.utils import resolve_scope, confirm_action, EXIT_ERROR


def _get_graph_stats(scope: GraphScope) -> dict:
    """Get current graph statistics.

    Args:
        scope: Graph scope to query

    Returns:
        Dictionary with entity_count, relationship_count, duplicate_count, size_bytes

    TODO: Wire to actual graph statistics when available.
    For now, returns mock data to enable CLI flow testing.
    """
    # Mock data for CLI testing
    if scope == GraphScope.GLOBAL:
        return {
            "entity_count": 127,
            "relationship_count": 342,
            "duplicate_count": 18,
            "size_bytes": 4_567_890,
        }
    else:
        return {
            "entity_count": 43,
            "relationship_count": 89,
            "duplicate_count": 5,
            "size_bytes": 1_234_567,
        }


def _compact_graph(scope: GraphScope) -> dict:
    """Perform graph compaction operation.

    Args:
        scope: Graph scope to compact

    Returns:
        Dictionary with merged_count, removed_count, new_entity_count, new_size_bytes

    TODO: Wire to actual graph compaction logic when available.
    For now, returns mock results to enable CLI flow testing.
    """
    # Mock compaction results for CLI testing
    stats = _get_graph_stats(scope)
    duplicates = stats["duplicate_count"]

    return {
        "merged_count": duplicates,
        "removed_count": duplicates * 2,  # Some duplicates involve multiple entities
        "new_entity_count": stats["entity_count"] - duplicates,
        "new_size_bytes": int(stats["size_bytes"] * 0.85),  # 15% size reduction
    }


def compact_command(
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation prompt")
    ] = False,
    global_scope: Annotated[
        bool,
        typer.Option("--global", "-g", help="Use global scope")
    ] = False,
    project_scope: Annotated[
        bool,
        typer.Option("--project", "-p", help="Use project scope")
    ] = False,
    format: Annotated[
        Optional[str],
        typer.Option("--format", "-f", help="Output format: json")
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress non-essential output")
    ] = False,
):
    """Compact the knowledge graph by merging duplicates.

    This is a maintenance operation that:
    - Identifies and merges duplicate entities
    - Removes redundant relationships
    - Rebuilds indexes for optimal performance

    WARNING: This is a destructive operation that cannot be undone.
    Use --force to skip the confirmation prompt.

    Examples:
        graphiti compact
        graphiti compact --force
        graphiti compact --format json
    """
    try:
        # Resolve scope
        scope, _ = resolve_scope(global_scope, project_scope)

        # Load current graph statistics
        stats = _get_graph_stats(scope)

        # Display current state
        if not quiet and format != "json":
            console.print(
                f"\n[cyan]Knowledge graph:[/cyan] "
                f"{stats['entity_count']} entities, "
                f"{stats['relationship_count']} relationships, "
                f"~{stats['duplicate_count']} potential duplicates\n"
            )

        # Check if compaction needed
        if stats["duplicate_count"] == 0:
            print_success("No compaction needed. Graph is clean.")
            raise typer.Exit(0)

        # Confirmation for destructive operation
        confirmed = confirm_action(
            f"Compact the knowledge graph? This will merge {stats['duplicate_count']} duplicate entities.",
            force=force
        )

        if not confirmed:
            console.print("Cancelled")
            raise typer.Exit(0)

        # Perform compaction with spinner and progress updates
        with console.status("Compacting knowledge graph...") as status:
            # Simulate multi-step process
            status.update("Merging duplicates...")
            # Placeholder for actual merge logic

            status.update("Rebuilding indexes...")
            # Placeholder for index rebuild

            status.update("Finalizing...")
            # Placeholder for finalization

            # Execute compaction
            result = _compact_graph(scope)

        # Output results
        if format == "json":
            print_json(result)
        else:
            # Success message with summary
            print_success(
                f"Compacted: {result['merged_count']} merged, "
                f"{result['removed_count']} removed. "
                f"{result['new_entity_count']} entities remaining."
            )

            if not quiet:
                # Show size reduction
                old_size_mb = stats['size_bytes'] / (1024 * 1024)
                new_size_mb = result['new_size_bytes'] / (1024 * 1024)
                reduction_pct = ((stats['size_bytes'] - result['new_size_bytes']) / stats['size_bytes']) * 100

                console.print(
                    f"\n[dim]Size: {old_size_mb:.1f}MB → {new_size_mb:.1f}MB "
                    f"({reduction_pct:.1f}% reduction)[/dim]"
                )

    except Exception as e:
        print_error(f"Failed to compact graph: {str(e)}")
        raise typer.Exit(EXIT_ERROR)
