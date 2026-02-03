from pathlib import Path

# Global scope database path: ~/.graphiti/global/graphiti.kuzu
GLOBAL_DB_DIR = Path.home() / ".graphiti" / "global"
GLOBAL_DB_PATH = GLOBAL_DB_DIR / "graphiti.kuzu"

# Project scope database is relative to project root
PROJECT_DB_DIR_NAME = ".graphiti"
PROJECT_DB_NAME = "graphiti.kuzu"

def get_project_db_path(project_root: Path) -> Path:
    """Get the database path for a project scope"""
    return project_root / PROJECT_DB_DIR_NAME / PROJECT_DB_NAME
