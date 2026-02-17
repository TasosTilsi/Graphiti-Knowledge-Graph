"""Git configuration file generators for Graphiti.

This module provides utilities to generate and maintain .gitignore and .gitattributes
files for proper version control of Graphiti knowledge graphs.
"""

from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Gitignore content for .graphiti directory
GRAPHITI_GITIGNORE = """# Graphiti Knowledge Graph - Git Ignores
# Transient per-developer state (not shared)

# SQLite queue database (per-developer processing state)
queue.db
queue.db-wal
queue.db-shm

# Temporary files
*.tmp
*.lock

# Rebuild-in-progress markers
.rebuilding

# Debug and log artifacts
*.log
audit.log
"""

# Gitattributes content for LFS tracking
GRAPHITI_GITATTRIBUTES = """# Graphiti Knowledge Graph - Git Attributes
# LFS tracking for binary database files

.graphiti/database/** filter=lfs diff=lfs merge=lfs -text
"""


def generate_gitignore(project_root: Path) -> Path:
    """Generate .gitignore file for .graphiti directory.

    Args:
        project_root: Root directory of the project

    Returns:
        Path to the created .gitignore file
    """
    graphiti_dir = project_root / ".graphiti"
    graphiti_dir.mkdir(parents=True, exist_ok=True)

    gitignore_path = graphiti_dir / ".gitignore"
    gitignore_path.write_text(GRAPHITI_GITIGNORE.lstrip())

    logger.info("generated_gitignore", path=str(gitignore_path))
    return gitignore_path


def generate_gitattributes(project_root: Path) -> Path:
    """Generate or update .gitattributes file with LFS tracking.

    If the file exists, checks for existing LFS tracking configuration and only
    appends if not present (idempotent).

    Args:
        project_root: Root directory of the project

    Returns:
        Path to the .gitattributes file
    """
    gitattributes_path = project_root / ".gitattributes"

    if gitattributes_path.exists():
        content = gitattributes_path.read_text()

        # Check if LFS tracking is already configured
        if "filter=lfs" in content and ".graphiti/database/" in content:
            logger.debug("gitattributes_already_configured", path=str(gitattributes_path))
            return gitattributes_path

        # Append LFS configuration
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + GRAPHITI_GITATTRIBUTES.lstrip()
        gitattributes_path.write_text(content)
        logger.info("updated_gitattributes", path=str(gitattributes_path))
    else:
        # Create new file
        gitattributes_path.write_text(GRAPHITI_GITATTRIBUTES.lstrip())
        logger.info("generated_gitattributes", path=str(gitattributes_path))

    return gitattributes_path


def ensure_git_config(project_root: Path) -> dict[str, bool]:
    """Ensure all git configuration files are generated.

    Best-effort pattern: catches and logs errors, never raises exceptions.

    Args:
        project_root: Root directory of the project

    Returns:
        Dictionary with status of each configuration file:
        {"gitignore": bool, "gitattributes": bool}
    """
    result = {"gitignore": False, "gitattributes": False}

    # Generate gitignore
    try:
        generate_gitignore(project_root)
        result["gitignore"] = True
    except Exception as e:
        logger.warning("gitignore_generation_failed", error=str(e))

    # Generate gitattributes
    try:
        generate_gitattributes(project_root)
        result["gitattributes"] = True
    except Exception as e:
        logger.warning("gitattributes_generation_failed", error=str(e))

    return result
