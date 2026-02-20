"""Commit quality gate — filters out commits not worth indexing.

Provides should_skip_commit() which returns (skip: bool, reason: str).
Commits are skipped if they are from bots, have tiny diffs, are
version-bump-only, or are pure merge commits with no substantive diff.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from git import Commit

# Bot author email patterns (case-insensitive regex)
BOT_EMAIL_PATTERNS = [
    r'\[bot\]@users\.noreply\.github\.com$',
    r'@dependabot\.com$',
    r'noreply@github\.com$',
    r'\d+\+[a-z\-]+\[bot\]@',
]

# Bot commit message prefixes (case-insensitive prefix check)
BOT_MESSAGE_PREFIXES = [
    'chore(deps):',
    'chore(deps-dev):',
    'build(deps):',
    'chore(release):',
]

# File name patterns that indicate a version-bump-only commit
VERSION_FILE_PATTERNS = [
    'package.json',
    'pyproject.toml',
    '__version__',
    'CHANGELOG',
    'setup.py',
    'setup.cfg',
]

# Minimum line changes to be worth indexing
TINY_COMMIT_THRESHOLD = 3  # lines (insertions + deletions)


def _has_substantive_diff(commit: "Commit") -> bool:
    """Check if a merge commit has a substantive diff (more than zero files).

    Args:
        commit: git.Commit object

    Returns:
        True if the commit has any files changed, False for empty merges.
        Returns True on exception (conservative: assume substantive).
    """
    try:
        return commit.stats.total.get('files', 0) > 0
    except Exception:
        # Conservative: assume substantive on error
        return True


def should_skip_commit(commit: "Commit") -> tuple[bool, str]:
    """Decide whether a commit should be skipped during indexing.

    Applies filters in priority order:
    1. Bot author email
    2. Bot commit message prefix
    3. Pure merge with no substantive diff
    4. Tiny commit (too few lines changed)
    5. Version-bump-only (only touches version/changelog files)

    Args:
        commit: git.Commit object from GitPython

    Returns:
        (True, reason_string) if commit should be skipped,
        (False, "") if commit should be processed.
    """
    # 1. Check bot author email
    email = commit.author.email or ""
    for pattern in BOT_EMAIL_PATTERNS:
        if re.search(pattern, email, re.IGNORECASE):
            return (True, f"bot_author:{email}")

    # 2. Check bot message prefix
    message = (commit.message or "").strip()
    lower_message = message.lower()
    for prefix in BOT_MESSAGE_PREFIXES:
        if lower_message.startswith(prefix.lower()):
            return (True, f"bot_message:{prefix}")

    # 3. Check pure merge with no substantive diff
    if len(commit.parents) > 1:
        if not _has_substantive_diff(commit):
            return (True, "pure_merge_no_diff")

    # 4 & 5. Stats-based checks — wrap in try/except (stats calls git subprocess)
    try:
        total_lines = commit.stats.total.get('insertions', 0) + commit.stats.total.get('deletions', 0)

        # Tiny commit check
        if total_lines <= TINY_COMMIT_THRESHOLD:
            return (True, f"tiny:{total_lines}_lines")

        # Version-bump-only check
        changed_files = list(commit.stats.files.keys())
        if changed_files:
            def _is_version_file(filename: str) -> bool:
                basename = filename.split('/')[-1]
                return any(pattern.lower() in basename.lower() for pattern in VERSION_FILE_PATTERNS)

            if all(_is_version_file(f) for f in changed_files):
                return (True, "version_bump_only")

    except Exception:
        # Fail open: if we can't determine stats, process the commit
        return (False, "")

    return (False, "")
