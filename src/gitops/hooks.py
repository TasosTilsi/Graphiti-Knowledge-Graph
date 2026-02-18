"""Pre-commit validation hooks for journal auto-staging, schema validation, and security checks.

This module provides the "belt" for ensuring journal entries are always committed with code changes,
validated against the schema, scanned for secrets, and monitored for size. These hooks run fast
(delta-only scanning) and can be skipped with GRAPHITI_SKIP=1 for WIP commits.
"""

import json
import os
import sys
from pathlib import Path

import structlog

from src.gitops.journal import JournalEntry
from src.security import sanitize_content

logger = structlog.get_logger()

# Constants
SIZE_WARNING_MB = 50
SIZE_STRONG_WARNING_MB = 100
SKIP_ENV_VAR = "GRAPHITI_SKIP"


def _is_skip_enabled() -> bool:
    """Check if GRAPHITI_SKIP environment variable is set to bypass all checks.

    Returns:
        True if GRAPHITI_SKIP=1, False otherwise.
    """
    return os.environ.get(SKIP_ENV_VAR) == "1"


def stage_journal_entries(project_root: Path) -> int:
    """Auto-stage untracked and modified journal files before commit.

    This hook ensures journal entries created by operations are included in commits
    alongside code changes. It runs on a best-effort basis and never blocks commits.

    Args:
        project_root: Path to project root containing .git directory.

    Returns:
        Count of journal files staged (0 if GRAPHITI_SKIP=1 or on errors).
    """
    if _is_skip_enabled():
        return 0

    try:
        import git

        repo = git.Repo(project_root)
        journal_dir = project_root / ".graphiti" / "journal"

        if not journal_dir.exists():
            return 0

        files_to_stage = []

        # Find untracked journal files
        for untracked in repo.untracked_files:
            untracked_path = project_root / untracked
            if (
                untracked_path.is_relative_to(journal_dir)
                and untracked_path.suffix == ".json"
            ):
                files_to_stage.append(untracked)

        # Find modified but unstaged journal files
        for diff_item in repo.index.diff(None):
            modified_path = project_root / diff_item.a_path
            if (
                modified_path.is_relative_to(journal_dir)
                and modified_path.suffix == ".json"
            ):
                files_to_stage.append(diff_item.a_path)

        # Stage all found files
        if files_to_stage:
            repo.index.add(files_to_stage)
            logger.info(
                "staged_journal_entries",
                count=len(files_to_stage),
                files=files_to_stage,
            )

        return len(files_to_stage)

    except Exception as e:
        # Best-effort: log warning but don't block commits
        logger.warning("failed_to_stage_journal_entries", error=str(e))
        return 0


def validate_journal_schemas(project_root: Path) -> list[str]:
    """Validate staged journal files against the JournalEntry schema.

    This hook catches malformed journal entries before they enter git, preventing
    data corruption and ensuring all entries can be parsed for database rebuilds.

    Args:
        project_root: Path to project root containing .git directory.

    Returns:
        List of validation error messages (empty if all valid or GRAPHITI_SKIP=1).
    """
    if _is_skip_enabled():
        return []

    errors = []

    try:
        import git

        repo = git.Repo(project_root)
        journal_dir = project_root / ".graphiti" / "journal"

        if not journal_dir.exists():
            return []

        # Find staged journal files (comparing index to HEAD)
        try:
            staged_diffs = repo.index.diff("HEAD")
        except git.exc.BadName:
            # No HEAD yet (initial commit) - check all files in index
            staged_diffs = repo.index.diff(git.NULL_TREE)

        for diff_item in staged_diffs:
            # Skip deleted files
            if diff_item.deleted_file:
                continue

            file_path = project_root / diff_item.a_path
            if not file_path.is_relative_to(journal_dir) or file_path.suffix != ".json":
                continue

            try:
                # Read and validate the file
                content = file_path.read_text(encoding="utf-8")
                data = json.loads(content)
                # Validate against Pydantic model
                JournalEntry.model_validate(data)
            except FileNotFoundError:
                # File was deleted between detection and validation - skip
                continue
            except json.JSONDecodeError as e:
                errors.append(f"{file_path.name}: Invalid JSON - {e}")
            except Exception as e:
                errors.append(f"{file_path.name}: Schema validation failed - {e}")

        if errors:
            logger.warning(
                "journal_schema_validation_failed", error_count=len(errors)
            )

    except Exception as e:
        # Unexpected error - log and continue
        logger.warning("journal_schema_validation_error", error=str(e))

    return errors


def scan_journal_secrets(project_root: Path) -> list[str]:
    """Scan staged journal files for secrets using Phase 2's sanitize_content.

    This is the "belt" scanning (with .gitattributes/LFS as "suspenders") to catch
    secrets before they enter git history. Runs on delta-only (staged files) for
    performance.

    Args:
        project_root: Path to project root containing .git directory.

    Returns:
        List of secret detection warnings (empty if clean or GRAPHITI_SKIP=1).
    """
    if _is_skip_enabled():
        return []

    warnings = []

    try:
        import git

        repo = git.Repo(project_root)
        journal_dir = project_root / ".graphiti" / "journal"

        if not journal_dir.exists():
            return []

        # Find staged journal files
        try:
            staged_diffs = repo.index.diff("HEAD")
        except git.exc.BadName:
            # No HEAD yet (initial commit)
            staged_diffs = repo.index.diff(git.NULL_TREE)

        for diff_item in staged_diffs:
            # Skip deleted files
            if diff_item.deleted_file:
                continue

            file_path = project_root / diff_item.a_path
            if not file_path.is_relative_to(journal_dir) or file_path.suffix != ".json":
                continue

            try:
                # Read file content
                content = file_path.read_text(encoding="utf-8")

                # Scan for secrets using Phase 2's sanitize_content
                result = sanitize_content(content)

                if result.was_modified:
                    # Secrets found
                    warnings.append(
                        f"{file_path.name}: secrets detected - {len(result.findings)} finding(s)"
                    )
            except FileNotFoundError:
                # File was deleted between detection and scan - skip
                continue
            except Exception as e:
                # Log but don't fail on scanning errors
                logger.warning("secret_scan_error", file=str(file_path), error=str(e))

        if warnings:
            logger.warning("journal_secrets_detected", warning_count=len(warnings))

    except ImportError:
        # Security module not available - log warning but continue
        logger.warning("security_module_unavailable", msg="Secret scanning disabled")
    except Exception as e:
        # Unexpected error - log and continue
        logger.warning("journal_secret_scan_error", error=str(e))

    return warnings


def check_graphiti_size(project_root: Path) -> tuple[float, str | None]:
    """Check .graphiti/ directory size and return warnings if thresholds exceeded.

    Monitors .graphiti/ size (excluding LFS-tracked database/) to inform developers
    when they should run 'graphiti compact' to clean up deduplicated entities and
    expired journal entries.

    Args:
        project_root: Path to project root containing .graphiti directory.

    Returns:
        Tuple of (size_mb, warning_message). warning_message is None if below thresholds
        or if GRAPHITI_SKIP=1.
    """
    if _is_skip_enabled():
        return (0.0, None)

    try:
        graphiti_dir = project_root / ".graphiti"

        if not graphiti_dir.exists():
            return (0.0, None)

        # Calculate total size excluding database directory (LFS-tracked)
        total_bytes = 0
        for file_path in graphiti_dir.rglob("*"):
            if file_path.is_file() and "database" not in file_path.parts:
                total_bytes += file_path.stat().st_size

        # Convert to MB
        size_mb = total_bytes / (1024 * 1024)

        # Check thresholds
        if size_mb > SIZE_STRONG_WARNING_MB:
            return (
                size_mb,
                f"STRONG_WARNING: .graphiti/ is {size_mb:.1f}MB. Run 'graphiti compact' to clean up.",
            )
        elif size_mb > SIZE_WARNING_MB:
            return (
                size_mb,
                f"WARNING: .graphiti/ is {size_mb:.1f}MB. Consider running 'graphiti compact'.",
            )
        else:
            return (size_mb, None)

    except Exception as e:
        # On error, return zero size with no warning
        logger.warning("graphiti_size_check_error", error=str(e))
        return (0.0, None)


def run_precommit_validation(project_root: Path) -> int:
    """Main entry point for pre-commit hook validation.

    Orchestrates all pre-commit checks:
    1. Auto-stage journal entries
    2. Validate journal schemas
    3. Scan for secrets
    4. Check repository size

    Can be bypassed with GRAPHITI_SKIP=1 environment variable.

    Args:
        project_root: Path to project root containing .git directory.

    Returns:
        0 if validation passes (or warnings only), 1 if errors block commit.
    """
    if _is_skip_enabled():
        print("Graphiti: skipping (GRAPHITI_SKIP=1)", file=sys.stderr)
        return 0

    # Step 1: Auto-stage journal entries (always first)
    staged_count = stage_journal_entries(project_root)
    if staged_count > 0:
        logger.info("auto_staged_journal_entries", count=staged_count)

    # Step 2: Validate schemas
    schema_errors = validate_journal_schemas(project_root)

    # Step 3: Scan for secrets
    secret_warnings = scan_journal_secrets(project_root)

    # Step 4: Check size
    size_mb, size_warning = check_graphiti_size(project_root)

    # Print size warning if present (warnings don't block)
    if size_warning:
        print(size_warning, file=sys.stderr)

    # Print errors and warnings
    if schema_errors:
        print("\nGraphiti schema validation errors:", file=sys.stderr)
        for error in schema_errors:
            print(f"  - {error}", file=sys.stderr)

    if secret_warnings:
        print("\nGraphiti secret detection warnings:", file=sys.stderr)
        for warning in secret_warnings:
            print(f"  - {warning}", file=sys.stderr)

    # Block commit only if schema errors or secrets detected
    if schema_errors or secret_warnings:
        print("\nCommit blocked. Fix errors above or use GRAPHITI_SKIP=1 to bypass.", file=sys.stderr)
        return 1

    return 0
