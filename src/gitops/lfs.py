"""Git LFS detection and setup helpers for Graphiti.

This module provides utilities to detect Git LFS availability, identify LFS pointer files,
and ensure database files are available (either through LFS pull or journal rebuild).
"""

import subprocess
from pathlib import Path
from typing import Callable

import structlog

logger = structlog.get_logger(__name__)


def is_lfs_available() -> bool:
    """Check if Git LFS is available on the system.

    Returns:
        True if Git LFS is installed and working, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "lfs", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        is_available = result.returncode == 0 and "git-lfs" in result.stdout
        logger.debug("lfs_availability_check", available=is_available)
        return is_available
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.debug("lfs_not_available", error=str(e))
        return False


def is_lfs_pointer(filepath: Path) -> bool:
    """Check if a file is a Git LFS pointer file.

    LFS pointer files are small text files that start with a version identifier.

    Args:
        filepath: Path to the file to check

    Returns:
        True if the file is an LFS pointer, False otherwise
    """
    try:
        if not filepath.exists():
            return False

        # LFS pointers are small (typically < 200 bytes)
        if filepath.stat().st_size > 200:
            return False

        # Read content and check for LFS pointer signature
        content = filepath.read_text(errors="ignore")
        is_pointer = content.startswith("version https://git-lfs.github.com/spec/v1")
        logger.debug("lfs_pointer_check", path=str(filepath), is_pointer=is_pointer)
        return is_pointer
    except Exception as e:
        logger.debug("lfs_pointer_check_failed", path=str(filepath), error=str(e))
        return False


def setup_lfs_tracking(project_root: Path) -> bool:
    """Setup Git LFS tracking for Graphiti database files.

    Args:
        project_root: Root directory of the project

    Returns:
        True on success, False if LFS is not available or setup failed
    """
    if not is_lfs_available():
        logger.warning("lfs_not_available_for_setup", project_root=str(project_root))
        return False

    try:
        result = subprocess.run(
            ["git", "lfs", "track", ".graphiti/database/**"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            logger.info("lfs_tracking_configured", project_root=str(project_root))
            return True
        else:
            logger.warning(
                "lfs_tracking_failed",
                project_root=str(project_root),
                error=result.stderr,
            )
            return False
    except Exception as e:
        logger.error("lfs_setup_exception", project_root=str(project_root), error=str(e))
        return False


def ensure_database_available(
    project_root: Path, rebuild_fn: Callable | None = None
) -> bool:
    """Ensure the database is available and not an LFS pointer.

    This function handles three scenarios:
    1. Database doesn't exist: call rebuild_fn if provided
    2. Database is an LFS pointer: try to pull, or rebuild if LFS unavailable
    3. Database exists and is not a pointer: return True

    Args:
        project_root: Root directory of the project
        rebuild_fn: Optional callable to rebuild database from journal

    Returns:
        True if database is available, False if unavailable and cannot be rebuilt
    """
    db_dir = project_root / ".graphiti" / "database"

    # Check if database directory exists
    if not db_dir.exists():
        logger.info("database_not_found", project_root=str(project_root))
        if rebuild_fn:
            logger.info("rebuilding_database_from_journal")
            rebuild_fn()
            return True
        logger.warning("no_rebuild_function_provided")
        return False

    # Check if any database files are LFS pointers
    db_files = list(db_dir.rglob("*"))
    pointer_files = [f for f in db_files if f.is_file() and is_lfs_pointer(f)]

    if pointer_files:
        logger.info(
            "lfs_pointers_detected",
            count=len(pointer_files),
            files=[str(f.relative_to(project_root)) for f in pointer_files[:3]],
        )

        # Try to pull from LFS if available
        if is_lfs_available():
            try:
                logger.info("pulling_from_lfs", project_root=str(project_root))
                result = subprocess.run(
                    ["git", "lfs", "pull"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    logger.info("lfs_pull_successful")
                    return True
                else:
                    logger.warning("lfs_pull_failed", error=result.stderr)
            except Exception as e:
                logger.error("lfs_pull_exception", error=str(e))

        # LFS not available or pull failed, try rebuild
        if rebuild_fn:
            logger.info("rebuilding_database_from_journal_after_lfs_failure")
            rebuild_fn()
            return True
        else:
            logger.error(
                "lfs_unavailable_and_no_rebuild",
                message=(
                    "Git LFS is required but not available. "
                    "Install Git LFS (https://git-lfs.github.com/) or provide a rebuild function."
                ),
            )
            return False

    # Database exists and is not a pointer
    logger.debug("database_available", project_root=str(project_root))
    return True
