"""Compact command for knowledge graph maintenance.

Merges and deduplicates graph content, rebuilding indexes for optimal performance.
This is a destructive operation that requires confirmation.
"""
import typer
from typing import Annotated, Optional
from pathlib import Path

from src.models import GraphScope
from src.cli.output import console, print_error, print_json, print_success
from src.cli.utils import resolve_scope, confirm_action, EXIT_ERROR
from src.graph import get_service, run_graph_operation


def _get_graph_stats(scope: GraphScope, project_root: Optional[Path] = None) -> dict:
    """Get current graph statistics.

    Args:
        scope: Graph scope to query
        project_root: Project root path (required for PROJECT scope)

    Returns:
        Dictionary with entity_count, relationship_count, duplicate_count, size_bytes
    """
    stats = run_graph_operation(get_service().get_stats(scope=scope, project_root=project_root))
    return stats


def _compact_graph(scope: GraphScope, project_root: Optional[Path] = None) -> dict:
    """Perform graph compaction operation.

    Args:
        scope: Graph scope to compact
        project_root: Project root path (required for PROJECT scope)

    Returns:
        Dictionary with merged_count, removed_count, new_entity_count, new_size_bytes
    """
    result = run_graph_operation(get_service().compact(scope=scope, project_root=project_root))
    return result


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
    journal: Annotated[
        bool,
        typer.Option("--journal", help="Also compact journal (remove old entries)")
    ] = False,
    ttl_days: Annotated[
        int,
        typer.Option("--ttl-days", help="Journal TTL in days (default: 30)")
    ] = 30,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview what would be deleted without deleting")
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
    - Optionally cleans up old journal entries (--journal)

    WARNING: This is a destructive operation that cannot be undone.
    Use --force to skip the confirmation prompt.

    Examples:
        graphiti compact
        graphiti compact --force
        graphiti compact --journal --ttl-days 30
        graphiti compact --journal --dry-run
        graphiti compact --format json
    """
    try:
        # Resolve scope
        scope, project_root = resolve_scope(global_scope, project_scope)

        # Load current graph statistics
        stats = _get_graph_stats(scope, project_root)

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
            result = _compact_graph(scope, project_root)

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

        # Journal compaction (if requested)
        if journal:
            from src.gitops.compact import compact_journal, get_journal_stats
            from rich.table import Table

            if not quiet and format != "json":
                console.print("\n[cyan]Journal Compaction[/cyan]")

            # Get journal stats before compaction
            journal_stats = get_journal_stats(project_root)

            if journal_stats["total_entries"] == 0:
                if not quiet:
                    console.print("[dim]No journal entries found[/dim]")
            else:
                # Display journal stats
                if not quiet and format != "json":
                    table = Table(show_header=True, header_style="bold cyan")
                    table.add_column("Metric")
                    table.add_column("Value", justify="right")

                    table.add_row("Total entries", str(journal_stats["total_entries"]))
                    size_mb = journal_stats["total_size_bytes"] / (1024 * 1024)
                    table.add_row("Total size", f"{size_mb:.2f} MB")
                    table.add_row("Before checkpoint", str(journal_stats["before_checkpoint"]))
                    table.add_row("After checkpoint", str(journal_stats["after_checkpoint"]))

                    if journal_stats["oldest"]:
                        table.add_row("Oldest entry", journal_stats["oldest"])
                    if journal_stats["newest"]:
                        table.add_row("Newest entry", journal_stats["newest"])

                    console.print(table)

                # Perform journal compaction
                compact_result = compact_journal(project_root, ttl_days=ttl_days, dry_run=dry_run)

                if format == "json":
                    print_json({"graph": result, "journal": compact_result})
                else:
                    if "reason" in compact_result:
                        console.print(f"\n[yellow]{compact_result['reason']}[/yellow]")
                    elif compact_result["deleted"] > 0:
                        freed_mb = compact_result["bytes_freed"] / (1024 * 1024)
                        if dry_run:
                            print_success(
                                f"Dry run: Would delete {compact_result['deleted']} entries "
                                f"({freed_mb:.2f} MB). {compact_result['remaining']} entries would remain."
                            )
                        else:
                            print_success(
                                f"Deleted {compact_result['deleted']} old journal entries "
                                f"({freed_mb:.2f} MB freed). {compact_result['remaining']} entries remain."
                            )
                    else:
                        console.print("\n[dim]No journal entries eligible for deletion[/dim]")

    except Exception as e:
        print_error(f"Failed to compact graph: {str(e)}")
        raise typer.Exit(EXIT_ERROR)
