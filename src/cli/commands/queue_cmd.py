"""Queue management commands for background job processing."""
import sys
from typing import Annotated, Optional

import typer
from rich.table import Table

from src.cli.output import console, err_console, print_json, print_error, print_success
from src.cli.utils import EXIT_ERROR, EXIT_SUCCESS
from src.queue import get_status, process_queue, get_queue

# Create queue command group
queue_app = typer.Typer(
    name="queue",
    help="Manage the background processing queue",
    no_args_is_help=True
)


@queue_app.command(name="status")
def status_command(
    format: Annotated[
        Optional[str],
        typer.Option("--format", "-f", help="Output format: text or json")
    ] = "text"
):
    """Show queue status and health.

    Displays pending job count, dead letter count, worker status, and health indicator.
    Health levels match 'graphiti health' pattern:
    - ok: pending < 80% of capacity
    - warning: pending >= 80% of capacity (queue nearly full)
    - error: pending >= 100% of capacity (queue at/over capacity)

    Examples:
        graphiti queue status              # Show status table
        graphiti queue status --format json  # JSON output for programmatic use
    """
    # Get queue status
    status = get_status()

    # Determine health message
    if status["health"] == "error":
        health_msg = "Queue at or over capacity"
    elif status["health"] == "warning":
        health_msg = "Queue nearly full"
    else:
        health_msg = "Healthy"

    # JSON output mode
    if format == "json":
        output = {
            "health": status["health"],
            "pending": status["pending"],
            "dead_letter": status["dead_letter"],
            "capacity": {
                "used": status["pending"],
                "max": status["max_size"],
                "percent": status["capacity_pct"]
            },
            "worker": "running" if status["worker_running"] else "stopped",
            "message": health_msg
        }
        print_json(output)
        sys.exit(EXIT_SUCCESS)

    # Rich table output
    table = Table(
        title="Queue Status",
        show_header=True,
        header_style="bold cyan"
    )
    table.add_column("Status", style="white")
    table.add_column("Pending Jobs", style="cyan")
    table.add_column("Capacity", style="white")
    table.add_column("Dead Letter", style="yellow")
    table.add_column("Worker", style="white")
    table.add_column("Message", style="dim")

    # Color-coded health indicator
    health_icons = {
        "ok": "[green]ok[/green]",
        "warning": "[yellow]warning[/yellow]",
        "error": "[red]error[/red]"
    }
    health_display = health_icons.get(status["health"], "unknown")

    # Worker status
    worker_status = "[green]running[/green]" if status["worker_running"] else "[dim]stopped[/dim]"

    # Capacity format: "45/100"
    capacity_display = f"{status['pending']}/{status['max_size']}"

    table.add_row(
        health_display,
        str(status["pending"]),
        capacity_display,
        str(status["dead_letter"]),
        worker_status,
        health_msg
    )

    console.print(table)

    # Add dead letter hint if jobs exist
    if status["dead_letter"] > 0:
        console.print(
            f"\n[yellow]⚠[/yellow] {status['dead_letter']} failed job(s) in dead letter queue"
        )
        console.print("[dim]Run 'graphiti queue retry <job_id>' to reprocess failed jobs[/dim]")

    sys.exit(EXIT_SUCCESS)


@queue_app.command(name="process")
def process_command():
    """Process pending jobs manually (CLI fallback).

    Starts the background worker and processes all pending jobs until the queue is empty.
    This is a fallback for manual processing when the MCP server isn't running.

    The command blocks until all jobs are processed or the worker is stopped.

    Examples:
        graphiti queue process    # Process all pending jobs
    """
    console.print("[cyan]Processing queue...[/cyan]")

    try:
        # Process queue (blocks until empty)
        success_count, failure_count = process_queue()

        # Show results
        total = success_count + failure_count
        if total == 0:
            console.print("[dim]Queue was empty - no jobs to process[/dim]")
        else:
            result_msg = f"Processed {total} job(s)"
            if failure_count > 0:
                result_msg += f" ([green]{success_count}[/green] success, [red]{failure_count}[/red] failed)"
            else:
                result_msg += f" ([green]all successful[/green])"

            console.print(result_msg)

        sys.exit(EXIT_SUCCESS)

    except Exception as e:
        print_error(f"Failed to process queue: {str(e)}")
        sys.exit(EXIT_ERROR)


@queue_app.command(name="retry")
def retry_command(
    job_id: Annotated[
        str,
        typer.Argument(help="Dead letter job ID to retry, or 'all' to retry all")
    ]
):
    """Retry failed jobs from dead letter queue.

    Moves a dead letter job (or all dead letter jobs) back to the main queue
    for reprocessing. The job will be retried with reset attempt counter.

    Examples:
        graphiti queue retry abc-123-def    # Retry specific job
        graphiti queue retry all            # Retry all failed jobs
    """
    queue = get_queue()

    if job_id.lower() == "all":
        # Retry all dead letter jobs
        dead_letter_jobs = queue.get_dead_letter_jobs()

        if not dead_letter_jobs:
            console.print("[dim]No jobs in dead letter queue[/dim]")
            sys.exit(EXIT_SUCCESS)

        # Retry each job
        requeued_count = 0
        for job in dead_letter_jobs:
            if queue.retry_dead_letter(job.id):
                requeued_count += 1

        if requeued_count > 0:
            print_success(f"Moved {requeued_count} job(s) back to queue for retry")
        else:
            print_error("Failed to retry any jobs")
            sys.exit(EXIT_ERROR)

    else:
        # Retry specific job
        if queue.retry_dead_letter(job_id):
            print_success(f"Job {job_id} moved back to queue for retry")
        else:
            print_error(f"Job {job_id} not found in dead letter queue")
            sys.exit(EXIT_ERROR)

    sys.exit(EXIT_SUCCESS)
