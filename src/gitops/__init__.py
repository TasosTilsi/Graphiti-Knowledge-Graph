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

__all__ = [
    "ensure_git_config",
    "generate_gitattributes",
    "generate_gitignore",
]
