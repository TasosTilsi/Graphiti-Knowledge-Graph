"""Git operations and configuration management for Graphiti.

This module provides journal-based storage for knowledge graph operations,
enabling git-safe collaboration through migration-style timestamped logs.
Each operation is recorded as a separate JSON file to eliminate merge conflicts.
"""

from src.gitops.config import (
    ensure_git_config,
    generate_gitattributes,
    generate_gitignore,
)
from src.gitops.journal import (
    JournalAuthor,
    JournalEntry,
    JournalOperation,
    create_journal_entry,
    list_journal_entries,
)
from src.gitops.lfs import (
    ensure_database_available,
    is_lfs_available,
    is_lfs_pointer,
    setup_lfs_tracking,
)
from src.gitops.hooks import (
    check_graphiti_size,
    run_precommit_validation,
    scan_journal_secrets,
    stage_journal_entries,
    validate_journal_schemas,
)
from src.gitops.checkpoint import (
    get_checkpoint,
    set_checkpoint,
    get_new_journal_entries,
    validate_checkpoint,
)
from src.gitops.replay import (
    JournalReplayer,
    replay_journal,
    rebuild_from_journal,
)
from src.gitops.autoheal import (
    auto_heal,
    auto_setup,
)
from src.gitops.compact import (
    compact_journal,
    get_journal_stats,
)

__all__ = [
    "JournalAuthor",
    "JournalEntry",
    "JournalOperation",
    "JournalReplayer",
    "auto_heal",
    "auto_setup",
    "check_graphiti_size",
    "compact_journal",
    "create_journal_entry",
    "ensure_database_available",
    "ensure_git_config",
    "generate_gitattributes",
    "generate_gitignore",
    "get_checkpoint",
    "get_journal_stats",
    "get_new_journal_entries",
    "is_lfs_available",
    "is_lfs_pointer",
    "list_journal_entries",
    "rebuild_from_journal",
    "replay_journal",
    "run_precommit_validation",
    "scan_journal_secrets",
    "set_checkpoint",
    "setup_lfs_tracking",
    "stage_journal_entries",
    "validate_checkpoint",
    "validate_journal_schemas",
]
