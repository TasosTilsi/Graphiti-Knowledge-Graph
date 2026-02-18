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

__all__ = [
    "JournalAuthor",
    "JournalEntry",
    "JournalOperation",
    "check_graphiti_size",
    "create_journal_entry",
    "ensure_database_available",
    "ensure_git_config",
    "generate_gitattributes",
    "generate_gitignore",
    "is_lfs_available",
    "is_lfs_pointer",
    "list_journal_entries",
    "run_precommit_validation",
    "scan_journal_secrets",
    "setup_lfs_tracking",
    "stage_journal_entries",
    "validate_journal_schemas",
]
