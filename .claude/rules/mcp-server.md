---
paths:
  - "src/mcp_server/**"
---

# MCP Server Rules

These rules apply when working in `src/mcp_server/`.

- **Never use `structlog`** — use standard `logging` only
- **All log output must go to stderr** — stdout is the stdio transport channel
- **Never print to stdout** — any stray print/structlog output corrupts the JSON-RPC stream
- Use `logging.getLogger(__name__)` and route handlers to stderr explicitly
- FastMCP handles the transport — do not add custom stdio wrappers
