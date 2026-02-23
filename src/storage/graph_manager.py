import asyncio
import kuzu
import structlog
from pathlib import Path
from typing import Optional
from graphiti_core.driver.kuzu_driver import KuzuDriver, GraphProvider
from graphiti_core.graph_queries import get_fulltext_indices
from src.models import GraphScope
from src.config import GLOBAL_DB_PATH, get_project_db_path

logger = structlog.get_logger(__name__)


class GraphManager:
    """Manages dual-scope Kuzu database instances.

    Maintains singleton KuzuDriver instances for global and project scopes.
    Handles lazy initialization and proper cleanup.

    CRITICAL: Only one Database object should exist per database path.
    This class enforces that constraint via singleton pattern per scope.
    """

    def __init__(self):
        self._global_driver: Optional[KuzuDriver] = None
        self._project_driver: Optional[KuzuDriver] = None
        self._current_project_root: Optional[Path] = None

    def get_driver(
        self,
        scope: GraphScope,
        project_root: Optional[Path] = None
    ) -> KuzuDriver:
        """Get or create KuzuDriver for the specified scope.

        Args:
            scope: Which graph scope to access
            project_root: Required for PROJECT scope, ignored for GLOBAL

        Returns:
            KuzuDriver instance for the requested scope

        Raises:
            ValueError: If project_root not provided for PROJECT scope
        """
        if scope == GraphScope.GLOBAL:
            return self._get_global_driver()
        else:
            return self._get_project_driver(project_root)

    def _create_fts_indices(self, db: kuzu.Database) -> None:
        """Create Kuzu FTS indices if they don't exist.

        Workaround for graphiti-core v0.26.3 bug: KuzuDriver.build_indices_and_constraints()
        is a no-op and never calls get_fulltext_indices(KUZU). The FTS index
        (e.g. 'node_name_and_summary' on Entity) must be created before any
        QUERY_FTS_INDEX call or Kuzu raises a Binder exception.

        This is idempotent: errors are suppressed so re-running on an existing DB is safe.
        """
        conn = kuzu.Connection(db)
        for query in get_fulltext_indices(GraphProvider.KUZU):
            try:
                conn.execute(query)
            except Exception as e:
                # Index already exists or other non-fatal error — ignore
                logger.debug("FTS index creation skipped (may already exist)", error=str(e))
        conn.close()

    def _get_global_driver(self) -> KuzuDriver:
        """Get or create the global scope driver."""
        if self._global_driver is None:
            # Ensure directory exists
            GLOBAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._global_driver = KuzuDriver(db=str(GLOBAL_DB_PATH))
            # Workaround: graphiti-core KuzuDriver doesn't set _database,
            # but Graphiti.add_episode() accesses driver._database for group_id checks.
            self._global_driver._database = str(GLOBAL_DB_PATH)
            # Workaround: graphiti-core v0.26.3 KuzuDriver never creates FTS indices.
            self._create_fts_indices(self._global_driver.db)
        return self._global_driver

    def _get_project_driver(self, project_root: Optional[Path]) -> KuzuDriver:
        """Get or create project scope driver.

        Handles project switching: if project_root differs from cached,
        closes old connection and creates new one.
        """
        if project_root is None:
            raise ValueError("project_root is required for PROJECT scope")

        # Check if we need to switch projects
        if self._project_driver is not None and self._current_project_root != project_root:
            # Project changed, close old connection
            asyncio.run(self._project_driver.close())
            self._project_driver = None

        if self._project_driver is None:
            db_path = get_project_db_path(project_root)
            # Ensure directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._project_driver = KuzuDriver(db=str(db_path))
            # Workaround: see _get_global_driver comment
            self._project_driver._database = str(db_path)
            # Workaround: graphiti-core v0.26.3 KuzuDriver never creates FTS indices.
            self._create_fts_indices(self._project_driver.db)
            self._current_project_root = project_root

        return self._project_driver

    def reset_project(self) -> None:
        """Reset project scope connection.

        Call this when context changes (e.g., user changed directories).
        Next get_driver() for PROJECT scope will detect new project.
        """
        if self._project_driver is not None:
            asyncio.run(self._project_driver.close())
            self._project_driver = None
            self._current_project_root = None

    def close_all(self) -> None:
        """Close all database connections.

        Call this on application shutdown for clean resource release.
        """
        if self._global_driver is not None:
            asyncio.run(self._global_driver.close())
            self._global_driver = None

        if self._project_driver is not None:
            asyncio.run(self._project_driver.close())
            self._project_driver = None
            self._current_project_root = None
