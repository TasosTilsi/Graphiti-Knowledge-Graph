"""Hook context detection for background job queue.

This module provides detection logic to determine if the CLI is running in a
non-interactive context (hooks, CI/CD) where silent operation is preferred.

Detection strategy:
1. Check for Claude Code environment variables (CLAUDE_* prefix)
2. Check if stdin is a TTY (interactive terminal)
3. Check for common CI/CD environment markers

Use this to switch between:
- Silent mode (hook context): Queue jobs without user feedback
- Verbose mode (interactive CLI): Provide confirmation messages
"""

import os
import sys


def is_hook_context() -> bool:
    """Detect if running in Claude Code hook or automated context.

    Returns True (silent mode) when:
    1. Any environment variable starting with CLAUDE_ exists (Claude Code hook marker)
    2. sys.stdin.isatty() returns False (piped/non-interactive execution)
    3. Any CI/CD environment variable exists (CI, GITHUB_ACTIONS, etc.)

    Returns False (interactive CLI mode) otherwise.

    This enables context-aware feedback:
    - Hook context: Silent queueing without user output
    - Interactive CLI: Confirmation messages and progress updates

    Returns:
        True if in hook/automated context (use silent mode)
        False if in interactive terminal (provide user feedback)

    Examples:
        >>> # In interactive terminal
        >>> is_hook_context()
        False

        >>> # In Claude Code hook (CLAUDE_HOOK_TYPE=post-commit)
        >>> is_hook_context()
        True

        >>> # In GitHub Actions (CI=true, GITHUB_ACTIONS=true)
        >>> is_hook_context()
        True
    """
    # Check for Claude Code environment variables
    # Claude Code sets CLAUDE_* vars when executing hooks
    if any(key.startswith("CLAUDE_") for key in os.environ):
        return True

    # Check if stdin is a TTY (interactive terminal)
    # Piped input or hooks will have non-TTY stdin
    if not sys.stdin.isatty():
        return True

    # Check for common CI/CD environment markers
    # These environments should operate silently without user interaction
    ci_markers = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_HOME"]
    if any(marker in os.environ for marker in ci_markers):
        return True

    # Interactive terminal - provide user feedback
    return False
