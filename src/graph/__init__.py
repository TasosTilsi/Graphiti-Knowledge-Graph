"""Graph integration layer for graphiti_core.

This package provides adapters that bridge our OllamaClient and GraphManager
to graphiti_core's interfaces, plus a high-level GraphService API for CLI commands.

Quick start:
    from src.graph import GraphService, get_service, run_graph_operation

    # Get service instance
    service = get_service()

    # Add content (async)
    result = run_graph_operation(
        service.add(content="...", scope=GraphScope.GLOBAL, ...)
    )
"""

from src.graph.adapters import OllamaLLMClient, OllamaEmbedder
from src.graph.service import GraphService, get_service, run_graph_operation

__all__ = [
    # Adapters
    "OllamaLLMClient",
    "OllamaEmbedder",
    # Service
    "GraphService",
    "get_service",
    "run_graph_operation",
]
