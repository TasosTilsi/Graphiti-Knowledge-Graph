"""Checkpoint tracking for incremental journal replay.

The checkpoint file tracks the last-applied journal entry to enable
fast incremental replay (only process new entries) instead of full
rebuild every time. Critical for post-merge auto-heal performance.
"""

from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


def get_checkpoint(project_root: Path) -> str | None:
    """Get the filename of the last-applied journal entry.

    Args:
        project_root: Project root directory

    Returns:
        Filename of last checkpoint (e.g., "20260218_164500_abc123.json")
        or None if no checkpoint exists
    """
    checkpoint_file = project_root / ".graphiti" / "checkpoint"

    if not checkpoint_file.exists():
        return None

    try:
        content = checkpoint_file.read_text().strip()
        return content if content else None
    except Exception as e:
        logger.warning("Failed to read checkpoint", error=str(e), path=str(checkpoint_file))
        return None


def set_checkpoint(project_root: Path, filename: str) -> None:
    """Atomically update checkpoint to given journal entry filename.

    Uses atomic write pattern: write to temp file, then rename to target.
    Path.replace() is atomic on POSIX systems.

    Args:
        project_root: Project root directory
        filename: Journal entry filename (not full path)
    """
    graphiti_dir = project_root / ".graphiti"
    graphiti_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_file = graphiti_dir / "checkpoint"
    temp_file = graphiti_dir / "checkpoint.tmp"

    # Write to temp file
    temp_file.write_text(filename)

    # Atomic rename
    temp_file.replace(checkpoint_file)

    logger.debug("Updated checkpoint", filename=filename)


def clear_checkpoint(project_root: Path) -> None:
    """Remove checkpoint file (used for full rebuild scenarios).

    Args:
        project_root: Project root directory
    """
    checkpoint_file = project_root / ".graphiti" / "checkpoint"

    if checkpoint_file.exists():
        checkpoint_file.unlink()
        logger.info("Cleared checkpoint for full rebuild")


def get_new_journal_entries(project_root: Path) -> list[Path]:
    """Get journal entries that haven't been applied yet.

    Returns entries after the checkpoint (or all if no checkpoint).
    Entries are sorted chronologically by filename.

    Args:
        project_root: Project root directory

    Returns:
        List of journal entry file paths to process
    """
    journal_dir = project_root / ".graphiti" / "journal"

    if not journal_dir.exists():
        return []

    # Get all entries sorted chronologically
    all_entries = sorted(journal_dir.glob("*.json"))

    if not all_entries:
        return []

    # Get checkpoint
    checkpoint = get_checkpoint(project_root)

    # No checkpoint means process all entries (first-time setup)
    if checkpoint is None:
        return all_entries

    # Find checkpoint position
    try:
        checkpoint_entry = journal_dir / checkpoint
        checkpoint_index = all_entries.index(checkpoint_entry)
        # Return entries after checkpoint
        return all_entries[checkpoint_index + 1:]
    except (ValueError, FileNotFoundError):
        # Checkpoint not found in list - treat as corrupted, process all
        logger.warning(
            "Checkpoint references missing entry, processing all",
            checkpoint=checkpoint
        )
        return all_entries


def validate_checkpoint(project_root: Path) -> bool:
    """Check if checkpoint references a journal entry that still exists.

    Used by health check to detect corruption.

    Args:
        project_root: Project root directory

    Returns:
        True if checkpoint is valid or doesn't exist, False if orphaned
    """
    checkpoint = get_checkpoint(project_root)

    # No checkpoint is valid state
    if checkpoint is None:
        return True

    # Check if referenced file exists
    journal_dir = project_root / ".graphiti" / "journal"
    checkpoint_file = journal_dir / checkpoint

    exists = checkpoint_file.exists()

    if not exists:
        logger.warning(
            "Checkpoint references deleted entry",
            checkpoint=checkpoint
        )

    return exists
