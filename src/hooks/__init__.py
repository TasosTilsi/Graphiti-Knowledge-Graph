"""Hook installation and management for automatic capture.

This package provides:
- Git post-commit hook installation (src/hooks/installer.py)
- Claude Code Stop hook configuration (src/hooks/installer.py)
- Hook lifecycle management (src/hooks/manager.py - added in Task 2)
"""

from .installer import (
    install_claude_hook,
    install_git_hook,
    is_git_hook_installed,
    uninstall_claude_hook,
    uninstall_git_hook,
)

__all__ = [
    "install_git_hook",
    "uninstall_git_hook",
    "is_git_hook_installed",
    "install_claude_hook",
    "uninstall_claude_hook",
]
