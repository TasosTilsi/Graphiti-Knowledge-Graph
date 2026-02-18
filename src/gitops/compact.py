"""Journal compaction with TTL-based cleanup.

Provides cleanup of old journal entries beyond TTL threshold while respecting
checkpoint boundaries and safety buffers.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog

from src.gitops.checkpoint import get_checkpoint

logger = structlog.get_logger(__name__)

# Constants
DEFAULT_TTL_DAYS = 30  # Journal entries older than this and before checkpoint are deletable
SAFETY_BUFFER_DAYS = 7  # Never delete entries newer than checkpoint + buffer


def get_journal_stats(project_root: Path) -> dict:
    """Get statistics about the journal.

    Args:
        project_root: Project root directory

    Returns:
        Statistics dict with:
        - total_entries: Total number of journal entries
        - total_size_bytes: Total size of journal in bytes
        - oldest: Timestamp of oldest entry (ISO format) or None
        - newest: Timestamp of newest entry (ISO format) or None
        - before_checkpoint: Number of entries before checkpoint
        - after_checkpoint: Number of entries after checkpoint
    """
    journal_dir = project_root / ".graphiti" / "journal"

    if not journal_dir.exists():
        return {
            "total_entries": 0,
            "total_size_bytes": 0,
            "oldest": None,
            "newest": None,
            "before_checkpoint": 0,
            "after_checkpoint": 0,
        }

    # Get all journal entries (sorted by filename = chronological)
    entries = sorted(journal_dir.glob("*.json"))

    if not entries:
        return {
            "total_entries": 0,
            "total_size_bytes": 0,
            "oldest": None,
            "newest": None,
            "before_checkpoint": 0,
            "after_checkpoint": 0,
        }

    # Calculate total size
    total_size = sum(entry.stat().st_size for entry in entries)

    # Extract timestamps from filenames (YYYYMMDD_HHMMSS_ffffff_<uuid>.json)
    def parse_timestamp(filename: str) -> str | None:
        """Parse timestamp from journal filename."""
        try:
            # Extract YYYYMMDD_HHMMSS_ffffff portion
            parts = filename.replace(".json", "").split("_")
            if len(parts) >= 3:
                date_part = parts[0]  # YYYYMMDD
                time_part = parts[1]  # HHMMSS
                micro_part = parts[2]  # ffffff

                # Construct ISO timestamp
                year = date_part[:4]
                month = date_part[4:6]
                day = date_part[6:8]
                hour = time_part[:2]
                minute = time_part[2:4]
                second = time_part[4:6]

                return f"{year}-{month}-{day}T{hour}:{minute}:{second}.{micro_part}Z"
        except Exception:
            pass
        return None

    oldest_ts = parse_timestamp(entries[0].name)
    newest_ts = parse_timestamp(entries[-1].name)

    # Count entries before/after checkpoint
    checkpoint = get_checkpoint(project_root)
    before_checkpoint = 0
    after_checkpoint = 0

    if checkpoint:
        # Find checkpoint position
        for i, entry in enumerate(entries):
            if entry.name == checkpoint:
                before_checkpoint = i
                after_checkpoint = len(entries) - i
                break
        else:
            # Checkpoint not found (deleted or invalid) - treat all as after
            after_checkpoint = len(entries)
    else:
        # No checkpoint - all entries are "after" (can't safely delete any)
        after_checkpoint = len(entries)

    return {
        "total_entries": len(entries),
        "total_size_bytes": total_size,
        "oldest": oldest_ts,
        "newest": newest_ts,
        "before_checkpoint": before_checkpoint,
        "after_checkpoint": after_checkpoint,
    }


def compact_journal(
    project_root: Path,
    ttl_days: int = DEFAULT_TTL_DAYS,
    dry_run: bool = False,
) -> dict:
    """Compact journal by removing old entries beyond TTL.

    Only deletes entries that are:
    1. Before the checkpoint (already applied to database)
    2. Older than TTL threshold
    3. Outside the safety buffer (never delete very recent entries)

    Args:
        project_root: Project root directory
        ttl_days: Time-to-live in days (default: 30)
        dry_run: If True, don't actually delete files

    Returns:
        Result dict with:
        - deleted: Number of entries deleted
        - bytes_freed: Bytes freed by deletion
        - dry_run: Whether this was a dry run
        - remaining: Number of entries remaining
        - reason: Reason if no deletion occurred
    """
    journal_dir = project_root / ".graphiti" / "journal"

    if not journal_dir.exists():
        return {
            "deleted": 0,
            "bytes_freed": 0,
            "dry_run": dry_run,
            "remaining": 0,
            "reason": "No journal directory found",
        }

    # Get checkpoint - can't safely delete without one
    checkpoint = get_checkpoint(project_root)
    if not checkpoint:
        logger.info("No checkpoint set, cannot compact journal")
        return {
            "deleted": 0,
            "bytes_freed": 0,
            "dry_run": dry_run,
            "remaining": len(list(journal_dir.glob("*.json"))),
            "reason": "No checkpoint set. Run replay first.",
        }

    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=ttl_days)
    safety_cutoff = datetime.now(timezone.utc) - timedelta(days=SAFETY_BUFFER_DAYS)

    logger.info(
        "Starting journal compaction",
        ttl_days=ttl_days,
        cutoff_date=cutoff_date.isoformat(),
        dry_run=dry_run,
    )

    # Get all journal entries (sorted chronologically)
    entries = sorted(journal_dir.glob("*.json"))

    deleted_count = 0
    bytes_freed = 0

    for entry_file in entries:
        # Stop at checkpoint - never delete at or after checkpoint
        if entry_file.name >= checkpoint:
            logger.debug("Reached checkpoint, stopping deletion", checkpoint=checkpoint)
            break

        try:
            # Read entry to get timestamp
            content = entry_file.read_text(encoding="utf-8")
            data = json.loads(content)
            timestamp_str = data.get("timestamp")

            if not timestamp_str:
                logger.warning("Entry missing timestamp, skipping", file=entry_file.name)
                continue

            # Parse timestamp (ISO format)
            entry_timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            # Apply safety buffer - never delete entries within SAFETY_BUFFER_DAYS of now
            if entry_timestamp > safety_cutoff:
                logger.debug(
                    "Entry within safety buffer, skipping",
                    file=entry_file.name,
                    timestamp=timestamp_str,
                )
                continue

            # Check if entry is older than TTL
            if entry_timestamp < cutoff_date:
                # Entry is old enough and before checkpoint - eligible for deletion
                file_size = entry_file.stat().st_size

                if dry_run:
                    logger.info(
                        "Would delete journal entry",
                        file=entry_file.name,
                        timestamp=timestamp_str,
                        size_bytes=file_size,
                    )
                else:
                    logger.info(
                        "Deleting journal entry",
                        file=entry_file.name,
                        timestamp=timestamp_str,
                        size_bytes=file_size,
                    )
                    entry_file.unlink()

                deleted_count += 1
                bytes_freed += file_size

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse journal entry, skipping", file=entry_file.name, error=str(e))
            continue
        except Exception as e:
            logger.error("Error processing journal entry", file=entry_file.name, error=str(e))
            continue

    # Count remaining entries
    remaining = len(list(journal_dir.glob("*.json")))

    logger.info(
        "Journal compaction complete",
        deleted=deleted_count,
        bytes_freed=bytes_freed,
        remaining=remaining,
        dry_run=dry_run,
    )

    return {
        "deleted": deleted_count,
        "bytes_freed": bytes_freed,
        "dry_run": dry_run,
        "remaining": remaining,
    }
