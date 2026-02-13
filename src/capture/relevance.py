"""Content relevance filtering for capture pipeline.

Filters commit messages and content based on relevance categories:
- Decisions & rationale (why something was chosen)
- Architecture & patterns (system structure, design)
- Bug fixes & root causes (what went wrong and how it was fixed)
- Dependencies & config (libraries added/removed, config changes)

Also excludes routine content: WIP, fixup commits, formatting, routine tests.

All 4 categories are used by default (full set per user decision).
"""

import re
from typing import Optional

# Relevance category definitions with keyword indicators
RELEVANCE_CATEGORIES: dict[str, list[str]] = {
    "decisions": [
        "decided",
        "chose",
        "selected",
        "alternative",
        "option",
        "rejected",
        "tradeoff",
        "instead of",
        "rather than",
    ],
    "architecture": [
        "design",
        "structure",
        "pattern",
        "component",
        "interface",
        "layer",
        "module",
        "refactor",
        "architecture",
    ],
    "bugs": [
        "fix",
        "bug",
        "error",
        "issue",
        "crash",
        "regression",
        "root cause",
        "workaround",
        "patch",
    ],
    "dependencies": [
        "add",
        "install",
        "upgrade",
        "remove",
        "dependency",
        "library",
        "package",
        "version",
        "migrate",
    ],
}

# Exclude patterns for WIP/routine/scratch content
EXCLUDE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bfixup!", re.IGNORECASE),
    re.compile(r"\bwip\b", re.IGNORECASE),
    re.compile(r"\btypo\s", re.IGNORECASE),
    re.compile(r"^(format|formatted)\b", re.IGNORECASE),
    re.compile(r"^ran tests?\b", re.IGNORECASE),
    re.compile(r"^update[d]?\s+readme\b", re.IGNORECASE),
    re.compile(r"\bsquash!", re.IGNORECASE),
    re.compile(r"^lint\b", re.IGNORECASE),
    re.compile(r"^chore:\s*(format|lint)", re.IGNORECASE),
    re.compile(r"\btemporary\b.*\bexperiment\b", re.IGNORECASE),
    re.compile(r"\bdebugging\b.*\btrace\b", re.IGNORECASE),
]

# Default: all 4 categories (full set per user decision)
DEFAULT_CATEGORIES: list[str] = list(RELEVANCE_CATEGORIES.keys())


def filter_relevant_commit(
    commit_message: str,
    categories: list[str] | None = None,
) -> bool:
    """Check if commit message is relevant (contains knowledge worth capturing).
    
    A commit is relevant if:
    1. It matches at least one enabled category keyword
    2. It does NOT match any exclude pattern
    
    Args:
        commit_message: Git commit message to evaluate
        categories: Categories to check. None = DEFAULT_CATEGORIES (all 4)
    
    Returns:
        True if relevant (should be captured), False otherwise (skip)
    
    Example:
        >>> filter_relevant_commit("feat: decided to use Redis instead of Memcached")
        True  # Matches "decisions" category
        >>> filter_relevant_commit("fixup! typo in readme")
        False  # Matches exclude pattern
        >>> filter_relevant_commit("feat: add new dependency Redis")
        True  # Matches "dependencies" category
    """
    if categories is None:
        categories = DEFAULT_CATEGORIES
    
    # Normalize to lowercase for matching
    message_lower = commit_message.lower()
    
    # Check exclude patterns first (WIP, routine content)
    for pattern in EXCLUDE_PATTERNS:
        if pattern.search(commit_message):
            return False
    
    # Check for relevance in enabled categories
    for category in categories:
        if category not in RELEVANCE_CATEGORIES:
            continue
        
        keywords = RELEVANCE_CATEGORIES[category]
        if any(keyword in message_lower for keyword in keywords):
            return True
    
    # No category match and no exclude match = not relevant
    return False


def get_active_categories(config_categories: list[str] | None = None) -> list[str]:
    """Get active relevance categories from config.
    
    Validates that requested categories exist in RELEVANCE_CATEGORIES.
    Falls back to DEFAULT_CATEGORIES if config is None or invalid.
    
    Args:
        config_categories: Categories from config, or None for defaults
    
    Returns:
        List of valid category names
    
    Example:
        >>> get_active_categories(None)
        ['decisions', 'architecture', 'bugs', 'dependencies']
        >>> get_active_categories(['decisions', 'bugs'])
        ['decisions', 'bugs']
        >>> get_active_categories(['invalid'])
        ['decisions', 'architecture', 'bugs', 'dependencies']  # Falls back
    """
    if config_categories is None:
        return DEFAULT_CATEGORIES.copy()
    
    # Validate categories
    valid_categories = [
        cat for cat in config_categories
        if cat in RELEVANCE_CATEGORIES
    ]
    
    # If no valid categories, fall back to defaults
    if not valid_categories:
        return DEFAULT_CATEGORIES.copy()
    
    return valid_categories