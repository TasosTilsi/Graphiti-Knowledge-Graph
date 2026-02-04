"""File exclusion system for security filtering.

Provides pattern-based file exclusion with symlink resolution
to prevent bypass attacks through symlinked sensitive files.
"""
from pathlib import Path
from typing import Optional
import fnmatch

from src.config.security import DEFAULT_FILE_EXCLUSIONS
from src.models.security import FileExclusionResult


class FileExcluder:
    """Handles file exclusion logic with configurable patterns."""

    def __init__(self, exclusion_patterns: list[str] | None = None):
        """Initialize with exclusion patterns.

        Args:
            exclusion_patterns: List of glob patterns. Uses defaults if None.
        """
        self.patterns = exclusion_patterns or DEFAULT_FILE_EXCLUSIONS

    def check(self, file_path: Path) -> FileExclusionResult:
        """Check if file should be excluded from security scanning.

        Resolves symlinks to prevent bypass attacks where .env
        is accessed through an innocuously-named symlink.

        Args:
            file_path: Path to check

        Returns:
            FileExclusionResult with exclusion status and matched pattern
        """
        # CRITICAL: Resolve symlinks to prevent bypass
        try:
            resolved_path = file_path.resolve()
        except (OSError, RuntimeError):
            # If resolution fails, be conservative and exclude
            return FileExclusionResult(
                file_path=file_path,
                is_excluded=True,
                matched_pattern="<unresolvable_path>"
            )

        path_str = str(resolved_path)
        path_name = resolved_path.name

        for pattern in self.patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith('/'):
                dir_pattern = pattern.rstrip('/')
                # Check if any parent directory matches
                for parent in resolved_path.parents:
                    if fnmatch.fnmatch(parent.name, dir_pattern):
                        return FileExclusionResult(
                            file_path=file_path,
                            is_excluded=True,
                            matched_pattern=pattern
                        )

            # Handle ** glob patterns
            elif '**' in pattern:
                # Use pathlib.match() for proper ** globbing
                # This correctly handles **/test_*.py (any test_ file in any subdir)
                try:
                    if resolved_path.match(pattern):
                        return FileExclusionResult(
                            file_path=file_path,
                            is_excluded=True,
                            matched_pattern=pattern
                        )
                except (ValueError, OSError):
                    # Invalid pattern, skip
                    pass

            # Handle simple glob patterns
            else:
                # Match against full path or just filename
                if fnmatch.fnmatch(path_str, f"*{pattern}*") or \
                   fnmatch.fnmatch(path_name, pattern):
                    return FileExclusionResult(
                        file_path=file_path,
                        is_excluded=True,
                        matched_pattern=pattern
                    )

        return FileExclusionResult(
            file_path=file_path,
            is_excluded=False,
            matched_pattern=None
        )


def is_excluded_file(
    file_path: Path,
    exclusion_patterns: list[str] | None = None
) -> bool:
    """Convenience function to check if file is excluded.

    Args:
        file_path: Path to check
        exclusion_patterns: Optional custom patterns

    Returns:
        True if file should be excluded from scanning
    """
    excluder = FileExcluder(exclusion_patterns)
    return excluder.check(file_path).is_excluded
