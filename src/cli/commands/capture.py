"""Capture command for Graphiti CLI.

Captures knowledge from the current Claude Code conversation (manual or automatic).
Supports both manual capture (user-triggered) and auto capture (hook-triggered).
"""
import typer
from typing import Annotated, Optional
from pathlib import Path

from src.cli.output import console, print_success, print_json, print_error
from src.cli.utils import EXIT_SUCCESS, EXIT_ERROR
from src.graph import run_graph_operation
from src.llm import LLMUnavailableError


def capture_command(
    auto: Annotated[bool, typer.Option("--auto", help="Auto-capture mode (incremental, for hooks)")] = False,
    transcript_path: Annotated[Optional[str], typer.Option("--transcript-path", help="Path to Claude Code transcript JSONL")] = None,
    session_id: Annotated[Optional[str], typer.Option("--session-id", help="Claude Code session ID for tracking")] = None,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Output format: json")] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
):
    """Capture knowledge from the current Claude Code conversation.

    This command extracts entities and relationships from conversation transcripts
    and stores them in the knowledge graph. It supports two modes:

    1. Manual mode (default): Captures the current conversation session
    2. Auto mode (--auto): Incremental capture for hook-triggered processing

    Examples:
        graphiti capture                          # Manual capture of current session
        graphiti capture --auto --transcript-path /path/to/transcript --session-id abc123
    """
    try:
        # Import capture functions here to avoid circular imports
        from src.capture.conversation import capture_conversation, capture_manual

        # Auto mode: Called from Stop hook, requires transcript_path and session_id
        if auto:
            # Validate required parameters for auto mode
            if not transcript_path:
                raise typer.BadParameter(
                    "--transcript-path is required when using --auto mode"
                )
            if not session_id:
                raise typer.BadParameter(
                    "--session-id is required when using --auto mode"
                )

            # Convert transcript_path to Path object
            transcript = Path(transcript_path)

            # Call auto capture (incremental)
            result = run_graph_operation(
                capture_conversation(transcript, session_id, auto=True)
            )

            # If no new turns to capture, exit quietly
            if result is None:
                if not quiet:
                    console.print("[dim]No new turns to capture[/dim]")
                raise typer.Exit(EXIT_SUCCESS)

            # Output result based on format/quiet flags
            if format == "json":
                print_json(result)
            elif not quiet:
                entity_count = result.get("entities_created", 0)
                print_success(f"Auto-captured {entity_count} entities from session {session_id}")

        # Manual mode: User-triggered capture
        else:
            # Convert transcript_path to Path if provided, else None
            transcript = Path(transcript_path) if transcript_path else None

            # Show progress spinner during capture
            with console.status("Capturing conversation knowledge..."):
                result = run_graph_operation(capture_manual(transcript))

            # Output result
            if format == "json":
                print_json(result)
            elif not quiet:
                entity_count = result.get("entities_created", 0)
                edge_count = result.get("edges_created", 0)
                print_success(
                    f"Captured {entity_count} entities and {edge_count} relationships"
                )

    except ValueError as e:
        # No transcript found or invalid path
        print_error(
            str(e),
            suggestion="Run this command inside a Claude Code session with an active transcript"
        )
        raise typer.Exit(EXIT_ERROR)

    except LLMUnavailableError as e:
        # LLM service unavailable
        print_error(
            f"Cannot capture: LLM service unavailable. {str(e)}",
            suggestion="Check your Ollama configuration with 'graphiti health'"
        )
        raise typer.Exit(EXIT_ERROR)

    except Exception as e:
        print_error(f"Failed to capture conversation: {str(e)}")
        raise typer.Exit(EXIT_ERROR)
