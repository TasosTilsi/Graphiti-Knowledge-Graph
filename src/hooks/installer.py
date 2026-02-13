"""Hook installation logic for git and Claude Code.

Provides non-destructive installation of capture hooks with marker-based detection
for idempotent and reversible operations.
"""

import json
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

HOOK_START_MARKER = "# GRAPHITI_HOOK_START"
HOOK_END_MARKER = "# GRAPHITI_HOOK_END"


def _get_hook_template() -> str:
    """Read the post-commit.sh template from the templates directory.

    Returns:
        Template content as string

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_path = Path(__file__).parent / "templates" / "post-commit.sh"
    return template_path.read_text()


def _get_graphiti_section() -> str:
    """Extract the graphiti section (between markers) from the template.

    Returns:
        Just the section between GRAPHITI_HOOK_START and GRAPHITI_HOOK_END markers (inclusive)
    """
    template = _get_hook_template()

    # Find start and end marker positions
    start_idx = template.find(HOOK_START_MARKER)
    end_idx = template.find(HOOK_END_MARKER)

    if start_idx == -1 or end_idx == -1:
        raise ValueError("Template missing GRAPHITI_HOOK_START or GRAPHITI_HOOK_END marker")

    # Include the end marker line (find the newline after END marker)
    end_line_end = template.find('\n', end_idx)
    if end_line_end == -1:
        end_line_end = len(template)
    else:
        end_line_end += 1  # Include the newline

    return template[start_idx:end_line_end]


def is_git_hook_installed(repo_path: Path) -> bool:
    """Check if graphiti post-commit hook is already installed.

    Args:
        repo_path: Path to git repository

    Returns:
        True if hook exists and contains GRAPHITI_HOOK_START marker
    """
    hook_path = repo_path / ".git" / "hooks" / "post-commit"

    if not hook_path.exists():
        return False

    try:
        content = hook_path.read_text()
        return HOOK_START_MARKER in content
    except Exception as e:
        logger.warning("Failed to read hook file", path=str(hook_path), error=str(e))
        return False


def install_git_hook(repo_path: Path, force: bool = False) -> bool:
    """Install post-commit hook non-destructively.

    If an existing hook is present, appends graphiti section. If no hook exists,
    creates new hook with full template. Uses markers for idempotent detection.

    Args:
        repo_path: Path to git repository
        force: If True, reinstall even if already installed (not currently used)

    Returns:
        True if hook was installed, False if already installed

    Raises:
        ValueError: If repo_path is not a git repository
    """
    # Verify this is a git repo
    git_dir = repo_path / ".git"
    if not git_dir.exists() or not git_dir.is_dir():
        raise ValueError(f"Not a git repository: {repo_path}")

    # Check if already installed (idempotent)
    if is_git_hook_installed(repo_path):
        logger.info("Graphiti hook already installed", repo=str(repo_path))
        return False

    hook_path = git_dir / "hooks" / "post-commit"

    # Ensure hooks directory exists
    hook_path.parent.mkdir(parents=True, exist_ok=True)

    if hook_path.exists():
        # Existing hook from another tool - append our section
        logger.info("Existing post-commit hook found, appending graphiti section",
                   path=str(hook_path))

        existing_content = hook_path.read_text()

        # Detect pre-commit framework
        if "# pre-commit" in existing_content or "pre-commit hook" in existing_content:
            logger.warning(
                "pre-commit framework detected - appending graphiti hook",
                suggestion="Consider pre-commit integration for better compatibility"
            )

        # Append our section with spacing
        graphiti_section = _get_graphiti_section()
        new_content = existing_content.rstrip() + "\n\n" + graphiti_section
        hook_path.write_text(new_content)

    else:
        # No existing hook - create new one with full template
        logger.info("Creating new post-commit hook", path=str(hook_path))
        template = _get_hook_template()
        hook_path.write_text(template)

    # Set executable permission
    hook_path.chmod(0o755)

    logger.info("Graphiti post-commit hook installed successfully", repo=str(repo_path))
    return True


def uninstall_git_hook(repo_path: Path) -> bool:
    """Remove graphiti section from post-commit hook.

    If hook only contains graphiti content, removes entire file.
    If hook contains other content, removes only graphiti section.

    Args:
        repo_path: Path to git repository

    Returns:
        True if hook was uninstalled, False if not installed
    """
    # Check if installed
    if not is_git_hook_installed(repo_path):
        logger.info("Graphiti hook not installed, nothing to uninstall", repo=str(repo_path))
        return False

    hook_path = repo_path / ".git" / "hooks" / "post-commit"
    content = hook_path.read_text()

    # Find graphiti section boundaries
    start_idx = content.find(HOOK_START_MARKER)
    end_idx = content.find(HOOK_END_MARKER)

    if start_idx == -1 or end_idx == -1:
        logger.error("Hook markers not found despite is_git_hook_installed check",
                    path=str(hook_path))
        return False

    # Find the end of the end marker line
    end_line_end = content.find('\n', end_idx)
    if end_line_end == -1:
        end_line_end = len(content)
    else:
        end_line_end += 1  # Include the newline

    # Extract content before and after graphiti section
    before = content[:start_idx]
    after = content[end_line_end:]

    # Remove surrounding blank lines
    before = before.rstrip()
    after = after.lstrip()

    remaining_content = before + ("\n\n" + after if after else "")
    remaining_content = remaining_content.strip()

    if not remaining_content or remaining_content == "#!/bin/sh":
        # Hook only contained graphiti content - remove entire file
        hook_path.unlink()
        logger.info("Removed entire post-commit hook (only graphiti content)",
                   path=str(hook_path))
    else:
        # Other content exists - write back without graphiti section
        hook_path.write_text(remaining_content + "\n")
        logger.info("Removed graphiti section from post-commit hook",
                   path=str(hook_path))

    return True


def install_claude_hook(project_path: Path) -> bool:
    """Create/update .claude/settings.json with Stop hook for auto-capture.

    Adds graphiti capture command to Stop hooks array with async execution.
    Project-local settings only (not global).

    Args:
        project_path: Path to project root

    Returns:
        True if hook was installed, False if already exists
    """
    settings_dir = project_path / ".claude"
    settings_path = settings_dir / "settings.json"

    # Graphiti Stop hook configuration
    graphiti_hook = {
        "command": 'graphiti capture --auto --transcript-path "$transcript_path" --session-id "$session_id"',
        "async": True,
        "timeout": 10
    }

    # Load existing settings or create new
    if settings_path.exists():
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse .claude/settings.json",
                        path=str(settings_path), error=str(e))
            return False
    else:
        settings = {}

    # Ensure hooks.Stop array exists
    if "hooks" not in settings:
        settings["hooks"] = {}

    if "Stop" not in settings["hooks"]:
        settings["hooks"]["Stop"] = []

    # Check if graphiti hook already exists (idempotent)
    for hook in settings["hooks"]["Stop"]:
        if isinstance(hook, dict) and "graphiti capture" in hook.get("command", ""):
            logger.info("Graphiti Claude Code hook already installed",
                       project=str(project_path))
            return False

    # Add graphiti hook
    settings["hooks"]["Stop"].append(graphiti_hook)

    # Ensure directory exists and write settings
    settings_dir.mkdir(parents=True, exist_ok=True)
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)

    logger.info("Graphiti Claude Code Stop hook installed", project=str(project_path))
    return True


def uninstall_claude_hook(project_path: Path) -> bool:
    """Remove graphiti entry from .claude/settings.json hooks.Stop array.

    Args:
        project_path: Path to project root

    Returns:
        True if hook was removed, False if not installed
    """
    settings_path = project_path / ".claude" / "settings.json"

    if not settings_path.exists():
        logger.info("No .claude/settings.json found, nothing to uninstall",
                   project=str(project_path))
        return False

    try:
        with open(settings_path, 'r') as f:
            settings = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse .claude/settings.json",
                    path=str(settings_path), error=str(e))
        return False

    # Check if graphiti hook exists
    if "hooks" not in settings or "Stop" not in settings["hooks"]:
        logger.info("No Stop hooks found, nothing to uninstall",
                   project=str(project_path))
        return False

    # Filter out graphiti hooks
    original_count = len(settings["hooks"]["Stop"])
    settings["hooks"]["Stop"] = [
        hook for hook in settings["hooks"]["Stop"]
        if not (isinstance(hook, dict) and "graphiti capture" in hook.get("command", ""))
    ]

    if len(settings["hooks"]["Stop"]) == original_count:
        logger.info("Graphiti hook not found in Stop hooks", project=str(project_path))
        return False

    # Clean up empty structures
    if not settings["hooks"]["Stop"]:
        del settings["hooks"]["Stop"]

    if not settings["hooks"]:
        del settings["hooks"]

    # Write back settings
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2)

    logger.info("Graphiti Claude Code hook removed", project=str(project_path))
    return True
