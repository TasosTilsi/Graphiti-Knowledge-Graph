"""Journal entry data model and writer for migration-style timestamped operation logs.

Journal entries provide a git-safe foundation for knowledge graphs by recording each
operation as an individual timestamped JSON file. This eliminates merge conflicts
(two devs never edit the same file) and provides an authoritative source of truth
that can rebuild the Kuzu database.
"""

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict


class JournalOperation(str, Enum):
    """Types of operations that can be recorded in journal entries."""

    ADD_ENTITY = "add_entity"
    ADD_EDGE = "add_edge"
    UPDATE_ENTITY = "update_entity"
    DELETE_ENTITY = "delete_entity"
    DELETE_EDGE = "delete_edge"
    BULK_IMPORT = "bulk_import"


class JournalAuthor(BaseModel):
    """Author information from git config."""

    name: str
    email: str


class JournalEntry(BaseModel):
    """Immutable journal entry recording a single knowledge graph operation.

    Journal entries use a frozen Pydantic model for immutability, consistent with
    the project pattern of frozen dataclasses for important data structures.
    """

    version: str = "1.0"
    timestamp: datetime
    operation: JournalOperation
    author: JournalAuthor
    entity_id: str | None = None
    data: dict[str, Any]

    model_config = ConfigDict(frozen=True)


def get_git_author() -> JournalAuthor:
    """Get git author information from git config.

    Returns:
        JournalAuthor with name and email from git config.
        Falls back to "unknown"/"unknown@local" if git is not available
        or user is not configured.
    """
    try:
        # Import at function level to handle missing GitPython gracefully
        import git

        repo = git.Repo(search_parent_directories=True)
        config = repo.config_reader()

        name = config.get_value("user", "name", default="unknown")
        email = config.get_value("user", "email", default="unknown@local")

        return JournalAuthor(name=name, email=email)
    except Exception:
        # Any error (not a git repo, no user configured, GitPython missing, etc.)
        return JournalAuthor(name="unknown", email="unknown@local")


def create_journal_entry(
    operation: JournalOperation,
    data: dict[str, Any],
    entity_id: str | None = None,
    project_root: Path | None = None,
) -> Path:
    """Create a timestamped journal entry file.

    The filename format YYYYMMDD_HHMMSS_<uuid6hex>.json ensures:
    - Chronological sorting by filename
    - Uniqueness even if multiple entries created in the same second
    - Human-readable timestamps for debugging

    Args:
        operation: The type of operation being recorded
        data: Operation-specific payload (entity data, edge info, etc.)
        entity_id: Optional entity ID for targeted operations
        project_root: Optional project root path. If not provided, will attempt
                     to find it via git or use current directory.

    Returns:
        Path to the created journal file.
    """
    # Generate timestamp (UTC, timezone-aware for cross-timezone deterministic sorting)
    timestamp = datetime.now(timezone.utc)

    # Generate filename: YYYYMMDD_HHMMSS_<uuid6hex>.json
    date_part = timestamp.strftime("%Y%m%d_%H%M%S")
    uuid_part = uuid4().hex[:6]
    filename = f"{date_part}_{uuid_part}.json"

    # Determine journal directory
    if project_root is None:
        # Try to find project root via git
        try:
            import git

            repo = git.Repo(search_parent_directories=True)
            project_root = Path(repo.working_dir)
        except Exception:
            # Fall back to current directory
            project_root = Path.cwd()

    journal_dir = project_root / ".graphiti" / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)

    # Build journal entry
    author = get_git_author()
    entry = JournalEntry(
        timestamp=timestamp,
        operation=operation,
        author=author,
        entity_id=entity_id,
        data=data,
    )

    # Write JSON with indent=2 for human-readable diffs
    journal_path = journal_dir / filename
    journal_path.write_text(entry.model_dump_json(indent=2), encoding="utf-8")

    return journal_path


def list_journal_entries(project_root: Path | None = None) -> list[Path]:
    """List all journal entries in chronological order.

    The filename format ensures that sorted() produces chronological ordering.

    Args:
        project_root: Optional project root path. If not provided, will attempt
                     to find it via git or use current directory.

    Returns:
        Sorted list of journal entry file paths (chronological order).
        Returns empty list if journal directory doesn't exist.
    """
    # Determine journal directory
    if project_root is None:
        # Try to find project root via git
        try:
            import git

            repo = git.Repo(search_parent_directories=True)
            project_root = Path(repo.working_dir)
        except Exception:
            # Fall back to current directory
            project_root = Path.cwd()

    journal_dir = project_root / ".graphiti" / "journal"

    if not journal_dir.exists():
        return []

    return sorted(journal_dir.glob("*.json"))
