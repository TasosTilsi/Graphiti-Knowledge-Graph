"""Journal replay engine with incremental and full rebuild modes.

This module provides the core replay logic for synchronizing the database
with the journal. It supports:
- Incremental replay: process only new entries since last checkpoint
- Full rebuild: replay all entries from scratch
- Last-write-wins conflict resolution via timestamp ordering
"""

import json
from pathlib import Path
from typing import Callable

import structlog

from src.gitops.checkpoint import (
    clear_checkpoint,
    get_new_journal_entries,
    set_checkpoint,
)
from src.gitops.journal import JournalEntry

logger = structlog.get_logger(__name__)


class JournalReplayer:
    """Orchestrates journal replay with checkpoint management.

    The replayer processes journal entries in chronological order and
    updates the checkpoint after each entry to prevent duplicate
    processing on crash recovery.
    """

    def __init__(
        self,
        project_root: Path,
        apply_fn: Callable[[dict], bool] | None = None,
    ):
        """Initialize the replayer.

        Args:
            project_root: Project root directory
            apply_fn: Optional callback to apply each entry to database.
                      Receives entry dict, returns True on success.
                      If None, entries are tracked but not applied (dry-run mode).
        """
        self.project_root = project_root
        self.apply_fn = apply_fn
        self.logger = logger.bind(project_root=str(project_root))
        self.applied_entries: list[dict] = []

    def replay_journal(self) -> int:
        """Incrementally replay journal entries since last checkpoint.

        Processes only entries after the checkpoint (or all if no checkpoint).
        Updates checkpoint after EACH entry to prevent duplicate processing
        on crash recovery.

        Returns:
            Count of entries successfully applied
        """
        # Get new entries
        new_entries = get_new_journal_entries(self.project_root)

        if not new_entries:
            self.logger.info("No new journal entries to replay")
            return 0

        self.logger.info("Starting incremental journal replay", count=len(new_entries))

        applied_count = 0

        for entry_file in new_entries:
            try:
                # Read and parse entry
                content = entry_file.read_text(encoding="utf-8")
                data = json.loads(content)

                # Validate against schema
                try:
                    JournalEntry.model_validate(data)
                except Exception as e:
                    self.logger.warning(
                        "Invalid journal entry, skipping",
                        file=entry_file.name,
                        error=str(e),
                    )
                    continue

                # Apply entry
                if self._apply_entry(data):
                    applied_count += 1

                    # Update checkpoint after EACH entry (not batch)
                    # This prevents duplicate processing on crash
                    set_checkpoint(self.project_root, entry_file.name)

            except json.JSONDecodeError as e:
                self.logger.warning(
                    "Failed to parse journal entry, skipping",
                    file=entry_file.name,
                    error=str(e),
                )
                continue
            except Exception as e:
                self.logger.error(
                    "Unexpected error processing journal entry",
                    file=entry_file.name,
                    error=str(e),
                )
                # Continue processing other entries rather than failing entire replay
                continue

        self.logger.info("Completed journal replay", applied=applied_count)
        return applied_count

    def _apply_entry(self, entry: dict) -> bool:
        """Apply a single journal entry.

        This method tracks the entry and optionally applies it via the
        apply_fn callback. Last-write-wins is achieved by processing
        entries in chronological order (sorted filenames by timestamp).

        Args:
            entry: Parsed journal entry dict

        Returns:
            True if applied successfully, False otherwise
        """
        try:
            # Track entry for inspection/testing
            self.applied_entries.append(entry)

            # Apply via callback if provided
            if self.apply_fn is not None:
                return self.apply_fn(entry)

            # No callback = dry-run mode, always succeed
            return True

        except Exception as e:
            self.logger.error(
                "Failed to apply journal entry",
                operation=entry.get("operation"),
                error=str(e),
            )
            return False

    def rebuild_from_journal(self) -> int:
        """Rebuild database from journal (full replay from beginning).

        Clears checkpoint and replays all entries. This is the fallback
        path when LFS unavailable or database corrupted.

        Returns:
            Count of entries successfully applied
        """
        self.logger.info("Starting full rebuild from journal")

        # Clear checkpoint to start from beginning
        clear_checkpoint(self.project_root)

        # Replay all entries
        count = self.replay_journal()

        self.logger.info("Completed full rebuild", entries=count)
        return count


# Module-level convenience functions


def replay_journal(
    project_root: Path,
    apply_fn: Callable[[dict], bool] | None = None,
) -> int:
    """Incrementally replay journal entries (convenience function).

    Args:
        project_root: Project root directory
        apply_fn: Optional callback to apply entries

    Returns:
        Count of entries applied
    """
    replayer = JournalReplayer(project_root, apply_fn=apply_fn)
    return replayer.replay_journal()


def rebuild_from_journal(
    project_root: Path,
    apply_fn: Callable[[dict], bool] | None = None,
) -> int:
    """Rebuild database from journal (convenience function).

    Args:
        project_root: Project root directory
        apply_fn: Optional callback to apply entries

    Returns:
        Count of entries applied
    """
    replayer = JournalReplayer(project_root, apply_fn=apply_fn)
    return replayer.rebuild_from_journal()
