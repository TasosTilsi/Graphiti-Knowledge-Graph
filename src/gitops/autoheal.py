"""Auto-heal and auto-setup for git integration.

Provides post-merge auto-heal to replay new journal entries and first-run
auto-setup to bootstrap git configuration and hooks.
"""

from pathlib import Path
from typing import Callable

import structlog

from src.gitops.config import ensure_git_config
from src.gitops.replay import replay_journal

logger = structlog.get_logger(__name__)


def auto_heal(
    project_root: Path,
    apply_fn: Callable[[dict], bool] | None = None,
) -> int:
    """Auto-heal graph after merge by replaying new journal entries.

    Called by post-merge hook to incrementally sync database with merged
    journal entries. Uses incremental replay (only new entries since checkpoint).

    Args:
        project_root: Project root directory
        apply_fn: Optional callback to apply entries to database

    Returns:
        Count of entries replayed (0 if none or on error)
    """
    try:
        logger.info("Auto-healing graph after merge", project_root=str(project_root))

        # Replay new journal entries
        count = replay_journal(project_root, apply_fn=apply_fn)

        if count > 0:
            logger.info("Auto-heal complete", replayed_entries=count)
        else:
            logger.info("No new journal entries to replay")

        return count

    except Exception as e:
        # Never block merge - log error and return 0
        logger.error("Auto-heal failed", error=str(e), exc_info=True)
        return 0


def auto_setup(project_root: Path) -> dict[str, bool]:
    """Bootstrap git integration on first graphiti command.

    Sets up git configuration files and installs hooks for seamless
    git integration. All steps are best-effort (never raise exceptions).

    Args:
        project_root: Project root directory

    Returns:
        Status dict: {"git_config": bool, "hooks": bool, "lfs": bool}
    """
    status = {"git_config": False, "hooks": False, "lfs": False}

    try:
        logger.info("Auto-setup: bootstrapping git integration", project_root=str(project_root))

        # Step 1: Ensure git config files exist
        try:
            ensure_git_config(project_root)
            status["git_config"] = True
            logger.info("Auto-setup: git config files generated")
        except Exception as e:
            logger.warning("Auto-setup: failed to generate git config", error=str(e))

        # Step 2 & 3: Check and install hooks
        # Import here to avoid circular dependency
        try:
            from src.hooks.installer import (
                is_git_hook_installed,
                install_precommit_hook,
                install_postmerge_hook,
            )

            # Check if hooks are already installed
            precommit_installed = is_precommit_hook_installed(project_root)
            postmerge_installed = is_postmerge_hook_installed(project_root)

            if not precommit_installed or not postmerge_installed:
                logger.info(
                    "Auto-setup: installing git hooks",
                    precommit_installed=precommit_installed,
                    postmerge_installed=postmerge_installed,
                )

                # Install missing hooks
                if not precommit_installed:
                    try:
                        install_precommit_hook(project_root)
                    except Exception as e:
                        logger.warning("Auto-setup: failed to install pre-commit hook", error=str(e))

                if not postmerge_installed:
                    try:
                        install_postmerge_hook(project_root)
                    except Exception as e:
                        logger.warning("Auto-setup: failed to install post-merge hook", error=str(e))

            # Consider hooks setup successful if at least one is installed
            status["hooks"] = (
                is_precommit_hook_installed(project_root)
                or is_postmerge_hook_installed(project_root)
            )

            logger.info("Auto-setup: hooks check complete", hooks_ok=status["hooks"])

        except Exception as e:
            logger.warning("Auto-setup: failed to install hooks", error=str(e))

        # Step 4: Check LFS availability and set up tracking if available
        try:
            from src.gitops.lfs import is_lfs_available, setup_lfs_tracking

            if is_lfs_available():
                setup_lfs_tracking(project_root)
                status["lfs"] = True
                logger.info("Auto-setup: LFS tracking configured")
            else:
                logger.info("Auto-setup: LFS not available, skipping")

        except Exception as e:
            logger.warning("Auto-setup: failed to setup LFS", error=str(e))

        logger.info("Auto-setup complete", status=status)
        return status

    except Exception as e:
        # Best-effort pattern: log but never raise
        logger.error("Auto-setup failed", error=str(e), exc_info=True)
        return status
