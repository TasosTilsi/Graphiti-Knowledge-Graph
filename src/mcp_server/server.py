"""FastMCP server for graphiti knowledge graph.

Entry point: `graphiti mcp serve` (via CLI command group in src/cli/commands/mcp.py)

Transports:
  stdio          — default, Claude Code manages lifecycle
  streamable-http — standalone server on localhost:8000

All tool responses use TOON format for arrays, JSON/plain text for scalars.
Context resource returns TOON-encoded decisions + architecture context.

IMPORTANT: All output goes to stderr only. The MCP stdio transport uses stdout
for JSON-RPC messages — any stdout write (including print()) corrupts the
protocol. logging.basicConfig(stream=sys.stderr) is set before any imports
that might log.
"""
import logging
import sys

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

from mcp.server.fastmcp import FastMCP

from src.mcp_server.tools import (
    graphiti_add,
    graphiti_search,
    graphiti_list,
    graphiti_show,
    graphiti_delete,
    graphiti_summarize,
    graphiti_compact,
    graphiti_index,
    graphiti_capture,
    graphiti_health,
    graphiti_config,
)
from src.mcp_server.context import get_context

# Create the FastMCP server with instructions for Claude
mcp = FastMCP(
    "graphiti",
    instructions=(
        "graphiti is this user's personal knowledge graph for coding projects. "
        "Tool responses use TOON format (a compact wire encoding) — always present "
        "results as natural human-readable prose, never show TOON to the user. "
        "Use --limit flags to self-manage token budgets. "
        "Capture important decisions with graphiti_add after architecture discussions."
    )
)

# Register all 11 CLI tools with graphiti_ prefix
mcp.tool()(graphiti_add)
mcp.tool()(graphiti_search)
mcp.tool()(graphiti_list)
mcp.tool()(graphiti_show)
mcp.tool()(graphiti_delete)
mcp.tool()(graphiti_summarize)
mcp.tool()(graphiti_compact)
mcp.tool()(graphiti_index)
mcp.tool()(graphiti_capture)
mcp.tool()(graphiti_health)
mcp.tool()(graphiti_config)

# Register context resource for session-start injection
mcp.resource("graphiti://context")(get_context)


def main(transport: str = "stdio", port: int = 8000) -> None:
    """Start the MCP server with the specified transport.

    Args:
        transport: "stdio" (default) or "streamable-http"
        port: HTTP port for streamable-http transport (default 8000)
    """
    if transport == "streamable-http":
        mcp.run(transport="streamable-http", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
