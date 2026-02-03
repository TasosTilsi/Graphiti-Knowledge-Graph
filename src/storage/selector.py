from pathlib import Path
from typing import Optional, Tuple
from src.models import GraphScope


class GraphSelector:
    """Selects appropriate graph scope based on context.

    Determines whether to use global or project scope by detecting
    if the current working directory is within a git repository.
    """

    @staticmethod
    def find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
        """Find project root by looking for .git directory.

        Args:
            start_path: Starting directory (defaults to current working directory)

        Returns:
            Path to project root if found, None if not in a git repository
        """
        current = start_path or Path.cwd()

        # Walk up directory tree looking for .git
        for parent in [current, *current.parents]:
            git_dir = parent / ".git"
            if git_dir.exists() and git_dir.is_dir():
                return parent

        return None

    @staticmethod
    def determine_scope(
        operation_type: str = "knowledge",
        prefer_project: bool = True,
        start_path: Optional[Path] = None
    ) -> Tuple[GraphScope, Optional[Path]]:
        """Determine which graph scope to use.

        Args:
            operation_type: Type of operation ('preference' always uses global,
                           other types use project if available)
            prefer_project: Whether to prefer project scope when available
            start_path: Starting path for project detection (defaults to cwd)

        Returns:
            Tuple of (scope, project_root_path). project_root_path is None for global scope.
        """
        # Preferences always use global scope
        if operation_type == "preference":
            return (GraphScope.GLOBAL, None)

        # Check if we're in a project
        project_root = GraphSelector.find_project_root(start_path)

        if project_root and prefer_project:
            return (GraphScope.PROJECT, project_root)
        else:
            return (GraphScope.GLOBAL, None)
