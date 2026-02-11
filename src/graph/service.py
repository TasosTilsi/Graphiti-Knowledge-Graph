"""High-level GraphService wrapping graphiti_core's Graphiti class.

This service provides the main API that all CLI commands use for graph operations.
It handles:
- Per-scope Graphiti initialization (global vs project)
- Adapter wiring (OllamaLLMClient, OllamaEmbedder, KuzuDriver)
- Async/sync bridging for CLI context
- Content sanitization
- Error handling and logging
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

from src.config.paths import GLOBAL_DB_PATH, get_project_db_path
from src.graph.adapters import OllamaEmbedder, OllamaLLMClient
from src.llm import LLMUnavailableError
from src.llm import chat as ollama_chat
from src.models import GraphScope
from src.security import sanitize_content as secure_content
from src.storage import GraphManager

logger = logging.getLogger(__name__)

# Singleton instance
_service: Optional["GraphService"] = None


def get_service() -> "GraphService":
    """Get or create the singleton GraphService.

    Returns:
        GraphService instance
    """
    global _service
    if _service is None:
        _service = GraphService()
    return _service


def reset_service() -> None:
    """Reset the singleton service. Useful for testing."""
    global _service
    _service = None


def run_graph_operation(coro):
    """Run an async graph operation from sync context.

    This helper allows CLI commands (which are sync) to call async
    GraphService methods cleanly.

    Args:
        coro: Coroutine to run

    Returns:
        Result from the coroutine

    Example:
        result = run_graph_operation(service.add(...))
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in async context, can't use asyncio.run()
            # This shouldn't happen from CLI but handle gracefully
            raise RuntimeError(
                "run_graph_operation called from async context. Use await instead."
            )
        return asyncio.run(coro)
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(coro)


class GraphService:
    """High-level service for graph operations.

    Provides the main API used by CLI commands. Handles Graphiti initialization
    per scope, adapter wiring, and exposes methods for add, search, list, get,
    delete, summarize, compact, and stats operations.
    """

    def __init__(self):
        """Initialize GraphService with adapters and manager."""
        # Create storage manager
        self._graph_manager = GraphManager()

        # Create adapters (reused across all scopes)
        self._llm_client = OllamaLLMClient()
        self._embedder = OllamaEmbedder()

        # Cache Graphiti instances per scope
        self._graphiti_instances: dict[str, Graphiti] = {}

        logger.debug("GraphService initialized")

    def _get_cache_key(self, scope: GraphScope, project_root: Optional[Path]) -> str:
        """Get cache key for Graphiti instance.

        Args:
            scope: Graph scope
            project_root: Project root path (for PROJECT scope)

        Returns:
            Cache key string
        """
        if scope == GraphScope.GLOBAL:
            return "global"
        else:
            # Use resolved path string as key
            return f"project:{project_root.resolve()}" if project_root else "project:none"

    def _get_graphiti(
        self, scope: GraphScope, project_root: Optional[Path] = None
    ) -> Graphiti:
        """Get or create Graphiti instance for scope.

        Args:
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)

        Returns:
            Graphiti instance configured for the scope

        Raises:
            ValueError: If project_root not provided for PROJECT scope
        """
        cache_key = self._get_cache_key(scope, project_root)

        # Return cached instance if exists
        if cache_key in self._graphiti_instances:
            logger.debug("Using cached Graphiti instance", cache_key=cache_key)
            return self._graphiti_instances[cache_key]

        # Create new Graphiti instance
        logger.debug("Creating new Graphiti instance", cache_key=cache_key)

        # Get KuzuDriver for this scope
        driver = self._graph_manager.get_driver(scope, project_root)

        # Create Graphiti with our adapters
        # Note: cross_encoder=None skips reranking (not needed for local Kuzu)
        graphiti = Graphiti(
            graph_driver=driver,
            llm_client=self._llm_client,
            embedder=self._embedder,
        )

        # Cache and return
        self._graphiti_instances[cache_key] = graphiti
        return graphiti

    def _get_group_id(self, scope: GraphScope, project_root: Optional[Path]) -> str:
        """Get group ID for scope.

        Args:
            scope: Graph scope
            project_root: Project root path

        Returns:
            Group ID string for use in graphiti_core
        """
        if scope == GraphScope.GLOBAL:
            return "global"
        else:
            return project_root.name if project_root else "unknown_project"

    async def add(
        self,
        content: str,
        scope: GraphScope,
        project_root: Optional[Path],
        tags: Optional[list[str]] = None,
        source: str = "cli",
    ) -> dict:
        """Add content to the knowledge graph.

        Args:
            content: Text content to add
            scope: Graph scope (GLOBAL or PROJECT)
            project_root: Project root path (required for PROJECT scope)
            tags: Optional tags for the content
            source: Source description (default: "cli")

        Returns:
            Dict with: name, type, scope, created_at, tags, source, content_length,
                      nodes_created, edges_created

        Raises:
            LLMUnavailableError: If LLM is unavailable for extraction
        """
        logger.info(
            "Adding content to graph",
            scope=scope.value,
            content_length=len(content),
            has_tags=bool(tags),
        )

        # Sanitize content for secrets
        sanitization_result = secure_content(content, project_root=project_root)
        sanitized_content = sanitization_result.sanitized_content

        if sanitization_result.was_modified:
            logger.warning(
                "Content sanitized - secrets detected",
                num_findings=len(sanitization_result.findings),
            )

        # Get Graphiti instance
        graphiti = self._get_graphiti(scope, project_root)
        group_id = self._get_group_id(scope, project_root)

        # Generate episode name
        episode_name = f"cli_add_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # Add episode to graph
            await graphiti.add_episode(
                name=episode_name,
                episode_body=sanitized_content,
                source_description=source,
                reference_time=datetime.now(),
                source=EpisodeType.text,
                group_id=group_id,
            )

            # Return success result
            # Note: graphiti.add_episode doesn't return created nodes/edges count
            # We'd need to query the graph to get accurate counts
            # For now, return placeholder values (will be improved in integration phase)
            return {
                "name": episode_name,
                "type": "episode",
                "scope": scope.value,
                "created_at": datetime.now().isoformat(),
                "tags": tags or [],
                "source": source,
                "content_length": len(sanitized_content),
                "nodes_created": 0,  # TODO: Query graph for actual count
                "edges_created": 0,  # TODO: Query graph for actual count
            }

        except Exception as e:
            logger.error(
                "Failed to add content to graph",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def search(
        self,
        query: str,
        scope: GraphScope,
        project_root: Optional[Path],
        exact: bool = False,
        limit: int = 15,
    ) -> list[dict]:
        """Search the knowledge graph.

        Args:
            query: Search query text
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)
            exact: If True, use exact string matching; if False, use semantic search
            limit: Maximum number of results

        Returns:
            List of result dicts with: name, type, snippet, score, created_at, scope, tags

        Raises:
            LLMUnavailableError: If semantic search fails due to LLM unavailability
        """
        logger.info(
            "Searching graph",
            scope=scope.value,
            query_length=len(query),
            exact=exact,
            limit=limit,
        )

        graphiti = self._get_graphiti(scope, project_root)
        group_id = self._get_group_id(scope, project_root)

        try:
            if exact:
                # TODO: Implement exact search via raw Kuzu query
                # For now, fall back to semantic search
                logger.warning("Exact search not yet implemented, using semantic search")

            # Semantic search
            results = await graphiti.search(
                query=query,
                group_ids=[group_id],
                num_results=limit,
            )

            # Convert results to dict format
            result_list = []
            for edge in results:
                result_list.append(
                    {
                        "name": getattr(edge, "name", None)
                        or getattr(edge, "fact", "Unknown"),
                        "type": "relationship",
                        "snippet": getattr(edge, "fact", "")[:200],  # Truncate to 200 chars
                        "score": 0.0,  # graphiti.search doesn't return scores
                        "created_at": getattr(edge, "created_at", datetime.now()).isoformat()
                        if hasattr(edge, "created_at")
                        else datetime.now().isoformat(),
                        "scope": scope.value,
                        "tags": [],  # TODO: Extract from edge if available
                    }
                )

            logger.info("Search completed", num_results=len(result_list))
            return result_list

        except Exception as e:
            logger.error(
                "Search failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def list_entities(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
        limit: Optional[int] = 50,
    ) -> list[dict]:
        """List entities in the knowledge graph.

        Args:
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)
            limit: Maximum number of entities to return

        Returns:
            List of entity dicts with: name, type, created_at, tags, scope, relationship_count
        """
        logger.info("Listing entities", scope=scope.value, limit=limit)

        # Get driver for direct Kuzu queries
        driver = self._graph_manager.get_driver(scope, project_root)
        group_id = self._get_group_id(scope, project_root)

        try:
            # Query entities from graph
            # TODO: Implement with actual Kuzu queries once schema is confirmed
            # For now, return empty list (will be wired in integration phase)
            logger.warning("list_entities not yet implemented, returning empty list")
            return []

        except Exception as e:
            logger.error(
                "Failed to list entities",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def get_entity(
        self,
        name: str,
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> dict | list[dict] | None:
        """Get entity details by name.

        Args:
            name: Entity name to search for
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)

        Returns:
            - Single dict if one match found (with full details and relationships)
            - List of dicts if multiple matches (for disambiguation)
            - None if no matches found
        """
        logger.info("Getting entity", name=name, scope=scope.value)

        # TODO: Implement with actual Kuzu queries
        logger.warning("get_entity not yet implemented, returning None")
        return None

    async def delete_entities(
        self,
        names: list[str],
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> int:
        """Delete entities by name.

        Args:
            names: List of entity names to delete
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)

        Returns:
            Count of deleted entities
        """
        logger.info("Deleting entities", names=names, scope=scope.value)

        # TODO: Implement with actual entity deletion logic
        logger.warning("delete_entities not yet implemented, returning 0")
        return 0

    async def summarize(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
        topic: Optional[str] = None,
    ) -> tuple[str, int]:
        """Generate a summary of the knowledge graph.

        Args:
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)
            topic: Optional topic filter

        Returns:
            Tuple of (summary_text, entity_count)

        Raises:
            LLMUnavailableError: If LLM is unavailable for summarization
        """
        logger.info("Generating summary", scope=scope.value, topic=topic)

        # TODO: Implement with actual graph querying and LLM summarization
        logger.warning("summarize not yet implemented, returning placeholder")
        return ("Summary generation not yet implemented", 0)

    async def compact(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> dict:
        """Compact the knowledge graph by removing duplicates.

        Args:
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)

        Returns:
            Dict with: merged_count, removed_count, new_entity_count, new_size_bytes
        """
        logger.info("Compacting graph", scope=scope.value)

        # TODO: Implement deduplication logic
        logger.warning("compact not yet implemented, returning placeholder")
        return {
            "merged_count": 0,
            "removed_count": 0,
            "new_entity_count": 0,
            "new_size_bytes": 0,
        }

    async def get_stats(
        self,
        scope: GraphScope,
        project_root: Optional[Path],
    ) -> dict:
        """Get knowledge graph statistics.

        Args:
            scope: Graph scope
            project_root: Project root path (required for PROJECT scope)

        Returns:
            Dict with: entity_count, relationship_count, duplicate_count, size_bytes
        """
        logger.info("Getting graph stats", scope=scope.value)

        # TODO: Implement with actual Kuzu queries
        logger.warning("get_stats not yet implemented, returning placeholder")
        return {
            "entity_count": 0,
            "relationship_count": 0,
            "duplicate_count": 0,
            "size_bytes": 0,
        }
