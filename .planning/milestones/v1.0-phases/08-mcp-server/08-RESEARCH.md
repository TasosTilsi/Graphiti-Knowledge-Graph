# Phase 8: MCP Server - Research

**Researched:** 2026-02-21
**Domain:** Model Context Protocol Python SDK, FastMCP, TOON encoding, Claude Code Skills/SKILL.md
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Phase deliverables:**
- Phase 8 ships two things: SKILL.md first, then MCP Server alongside it
- Not splitting into separate phases — both land in Phase 8

**Tool interface:**
- All CLI commands exposed as MCP tools (full parity with CLI): add, search, list, show, delete, summarize, compact, capture, health, config
- Tool naming: `graphiti_` prefix (e.g., `graphiti_add`, `graphiti_search`) — avoids collision with other MCP servers
- Implementation: MCP tools call the graphiti CLI via subprocess — preserves CLI-first architecture, single source of truth

**Response format (TOON):**
- All MCP tool responses are encoded in TOON (Token-Oriented Object Notation) — not plain text, not JSON
- TOON gives ~40% token reduction vs JSON for uniform arrays of objects (entity lists, search results, etc.)
- SKILL.md instructs Claude to present TOON responses as human-readable prose to the user — no TOON ever shown to the end user
- No extra transformation cost: Claude reads TOON naturally and incorporates into its response; the SKILL.md instruction is a one-time system prompt cost (~10-15 tokens), not per-call
- Context injection (`graphiti://context` resource) also encoded as TOON

**SKILL.md behaviors (automatic):**
- Inject context at session start (pull relevant knowledge when a session begins)
- Capture after key moments (run `graphiti add` after decisions, architecture discussions, bug resolutions)
- Surface knowledge on relevant topics (when user mentions a file/topic, proactively check if graphiti has context)
- Respond when explicitly asked
- SKILL.md instructs Claude to: use `--limit` flags for self-managed token budget, and always present tool results as natural human-readable prose (never expose TOON or raw CLI output to user)

**Context injection:**
- Signals at session start: current working directory / git project, recent git commits, recently modified files
- Content priority: decisions + architecture first (most durable, valuable context)
- Injection point: system prompt / MCP resource (`graphiti://context`) — invisible to user, appears before conversation
- Empty graph behavior: silent — inject nothing, no prompt to capture
- Source of truth: local Kuzu DB built by Phase 7.1 on-demand indexer — NOT journal replay. If index is stale (new commits since last index), trigger re-index before injecting.

**Token budget:**
- Default: 8K tokens (8192)
- User-configurable via: `mcp.context_tokens` config key (consistent with existing dotted key path convention)
- Trimming strategy: oldest entries first — most recent knowledge preserved
- SKILL.md: instructs Claude to self-limit results using `--limit` flags

**Transport & config:**
- Default transport: stdio (Claude Code spawns and manages the process)
- Also supported: HTTP / SSE (for running server independently or multi-client)
- Project context: auto-detect from current working directory at server startup (same behavior as CLI)
- Configuration method: `graphiti mcp install` command writes correct JSON to `~/.claude.json` automatically, plus documentation explaining what it does
- MCP resources: expose `graphiti://context` resource for session-start injection (in addition to tools)

### Claude's Discretion
- Exact subprocess invocation details for MCP → CLI calls
- HTTP transport implementation details (port, endpoint structure)
- Internal token counting method for budget enforcement
- SKILL.md exact wording and formatting
- TOON library choice (use existing toon-format library or implement minimal encoder)

### Deferred Ideas (OUT OF SCOPE)

**Phase 9 cleanup: TOON retrofit for existing LLM prompt boundaries** — Apply TOON encoding to structured data passed to the LLM in earlier phases (Phase 4, Phase 6, Phase 7.1). Out of scope for Phase 8.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| R6.1 | MCP Server Tools — MCP tools wrapping CLI operations; stdio transport for Claude Desktop; HTTP transport for other clients; tool definitions following MCP 2024-11-05 spec | FastMCP `@mcp.tool()` decorator + `subprocess.run()` pattern; `mcp` package 1.26.0 with both transports; `graphiti_` prefix convention |
| R6.2 | Context Injection Hooks — Hook on Claude Code session start; inject relevant context from graph; semantic search based on current file + recent commits; limit to top-K relevant nodes (<8K tokens) | MCP resource `@mcp.resource("graphiti://context")` pattern; stale detection via git HEAD; `python-toon` for TOON encoding; character-count approximation for token budget; `mcp.context_tokens` config key |
| R6.3 | Conversation Capture Hook — Hook after every 5-10 turns; async capture (non-blocking); extract decisions and preferences | Existing `capture_conversation()` in `src/capture/conversation.py`; MCP tool `graphiti_capture` wrapping subprocess; background threading for non-blocking |
</phase_requirements>

---

## Summary

Phase 8 delivers two artifacts: a **SKILL.md** file that teaches Claude Code how to use graphiti autonomously (inject context, capture decisions, surface knowledge), and a **Python MCP server** that exposes all 10 CLI commands as MCP tools plus a `graphiti://context` resource for session-start context injection.

The MCP server is implemented using the official `mcp` Python SDK (version 1.26.0, FastMCP framework). All tools wrap the graphiti CLI via `subprocess.run()` — preserving the CLI-first architecture. Tool responses are TOON-encoded using `python-toon` (version 0.1.3) for ~40% token reduction on uniform arrays (search results, entity lists). The `graphiti://context` resource queries the local Kuzu DB (built by Phase 7.1) for relevant context, encodes it in TOON, and enforces the 8K token budget by character-count approximation.

The `graphiti mcp install` command writes the stdio server registration to `~/.claude.json` automatically (zero manual config). HTTP transport is supported for non-Claude-Code clients, binding to localhost:8000 with Streamable HTTP transport (the 2025 MCP standard replacing SSE).

**Primary recommendation:** Use `mcp` SDK 1.26.0 with FastMCP for server creation, `python-toon` for TOON encoding, and `subprocess.run()` for all tool implementations. Write SKILL.md to `~/.claude/skills/graphiti/SKILL.md` using the Agent Skills standard format.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp` | 1.26.0 | MCP protocol SDK — FastMCP server framework, stdio and HTTP transports | Official Anthropic SDK; FastMCP is the blessed high-level API; 1.x stable branch |
| `python-toon` | 0.1.3 | TOON encoding/decoding — 30-60% token reduction for uniform arrays | Only Python TOON implementation; MIT license; 100% compatible with TypeScript reference |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `anyio` | (bundled with mcp) | Async HTTP server for streamable-http transport | Included as mcp dependency; needed for HTTP transport |
| `tiktoken` | 0.x | Token counting for budget enforcement | Use if accurate token count needed; falls back to char-count approximation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `mcp` SDK FastMCP | Low-level `mcp.server.Server` | FastMCP is simpler, decorator-based; low-level gives more control but not needed |
| `python-toon` | Custom minimal encoder | python-toon is 5 lines of install; custom encoder is ~50 lines and risks spec drift |
| Character-count for token budget | `tiktoken` | Tiktoken is OpenAI-specific (12% error for Claude); char-count with 4 chars/token is sufficient for budget trimming |

**Installation:**
```bash
pip install "mcp[cli]>=1.26.0" python-toon>=0.1.3
```

Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing deps ...
    "mcp[cli]>=1.26.0",
    "python-toon>=0.1.3",
]
```

---

## Architecture Patterns

### Recommended Project Structure
```
src/
├── mcp_server/           # Phase 8: MCP server module
│   ├── __init__.py
│   ├── server.py         # FastMCP app, tool registrations, resource
│   ├── tools.py          # Tool handler functions (subprocess wrappers)
│   ├── context.py        # graphiti://context resource — query + TOON encode
│   └── install.py        # graphiti mcp install command implementation
└── cli/
    └── commands/
        └── mcp.py         # graphiti mcp CLI subcommand group

# SKILL.md (user-facing, not in src/)
# Written to: ~/.claude/skills/graphiti/SKILL.md  (global: all projects)
# OR: .claude/skills/graphiti/SKILL.md            (project-scoped)
```

### Pattern 1: FastMCP Server with Subprocess Tools

**What:** Each MCP tool calls `graphiti <command>` via subprocess. Captures stdout, TOON-encodes structured output, returns to Claude.
**When to use:** All tool implementations in Phase 8.

```python
# Source: Official MCP Python SDK (https://github.com/modelcontextprotocol/python-sdk)
# Source: pypi.org/project/mcp/1.26.0

import subprocess
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("graphiti", instructions=(
    "graphiti is a personal knowledge graph for coding projects. "
    "Always present tool results as human-readable prose — never show TOON format to users. "
    "Use --limit flags to self-manage token budget."
))

@mcp.tool()
def graphiti_search(query: str, limit: int = 10) -> str:
    """Search the knowledge graph for relevant context.

    Returns TOON-encoded results. Present as natural prose to the user.
    """
    result = subprocess.run(
        ["graphiti", "search", query, "--limit", str(limit), "--format", "json"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"graphiti search failed: {result.stderr.strip()}")
    # Parse JSON output from CLI, re-encode as TOON
    data = json.loads(result.stdout)
    from toon import encode
    return encode(data)

@mcp.tool()
def graphiti_add(content: str, tags: str = "") -> str:
    """Add knowledge to the graph.

    Args:
        content: Knowledge to store (decision, architecture choice, bug fix)
        tags: Optional comma-separated tags
    """
    cmd = ["graphiti", "add", content]
    if tags:
        cmd += ["--tags", tags]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"graphiti add failed: {result.stderr.strip()}")
    return result.stdout.strip() or "Knowledge added successfully."
```

### Pattern 2: MCP Resource for Context Injection

**What:** `graphiti://context` resource is called at session start. Queries local Kuzu DB, encodes result as TOON, enforces token budget.
**When to use:** Session-start context injection for Claude Code.

```python
# Source: FastMCP resource pattern (modelcontextprotocol.github.io/python-sdk/)
import os
from pathlib import Path
from toon import encode

@mcp.resource("graphiti://context")
def get_context() -> str:
    """Session-start context from the local knowledge graph.

    Returns TOON-encoded decisions and architecture context.
    Present to user as conversational context, not raw data.
    """
    # Auto-detect project from CWD (same as CLI)
    from src.storage import GraphSelector
    scope, project_root = GraphSelector.determine_scope()

    # Check for stale index (new commits since last index)
    _ensure_index_fresh(project_root)

    # Query for high-priority context: decisions + architecture first
    import subprocess, json
    result = subprocess.run(
        ["graphiti", "search", "decisions architecture", "--limit", "20", "--format", "json"],
        capture_output=True, text=True, timeout=30,
        cwd=str(project_root) if project_root else None
    )
    if result.returncode != 0 or not result.stdout.strip():
        return ""  # Empty graph: silent, inject nothing

    data = json.loads(result.stdout)
    if not data:
        return ""

    # Encode as TOON and trim to token budget
    toon_output = encode(data)
    budget = _get_token_budget()  # reads mcp.context_tokens from config
    return _trim_to_budget(toon_output, budget)


def _get_token_budget() -> int:
    """Read mcp.context_tokens from config, default 8192."""
    import subprocess
    result = subprocess.run(
        ["graphiti", "config", "get", "mcp.context_tokens"],
        capture_output=True, text=True, timeout=5
    )
    if result.returncode == 0 and result.stdout.strip().isdigit():
        return int(result.stdout.strip())
    return 8192  # default per decision


def _trim_to_budget(text: str, token_budget: int) -> str:
    """Trim text to approximate token budget.

    Uses 4 chars per token approximation (sufficient for budget enforcement).
    Trims oldest entries first (TOON newline-delimited rows).
    """
    char_budget = token_budget * 4
    if len(text) <= char_budget:
        return text
    # TOON rows are newline-delimited — trim from top (oldest first)
    lines = text.split("\n")
    while len("\n".join(lines)) > char_budget and len(lines) > 1:
        lines.pop(0)  # remove oldest entry
    return "\n".join(lines)
```

### Pattern 3: Transport Selection and Server Entry Point

**What:** Single server.py with both stdio and HTTP transports selectable via CLI arg.
**When to use:** Main MCP server entry point.

```python
# Source: FastMCP docs (modelcontextprotocol.github.io/python-sdk/)
import argparse

def main():
    parser = argparse.ArgumentParser(description="Graphiti MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport type (default: stdio)"
    )
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (streamable-http only)")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http", port=args.port)

if __name__ == "__main__":
    main()
```

### Pattern 4: `graphiti mcp install` Command

**What:** Writes stdio server config to `~/.claude.json` so Claude Code picks it up automatically.
**When to use:** Zero-config user onboarding.

```python
# Claude Code MCP config location: ~/.claude.json
# Source: code.claude.com/docs/en/mcp (Official Claude Code docs)
import json
from pathlib import Path
import sys


def install_mcp_server() -> None:
    """Write graphiti MCP server config to ~/.claude.json.

    Format confirmed by official Claude Code docs:
    ~/.claude.json holds mcpServers for user-scope (all projects) configuration.
    """
    claude_json_path = Path.home() / ".claude.json"

    # Load existing config or create new
    if claude_json_path.exists():
        with open(claude_json_path) as f:
            config = json.load(f)
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Get the graphiti executable path
    graphiti_path = _find_graphiti_executable()

    # Write graphiti server config
    config["mcpServers"]["graphiti"] = {
        "type": "stdio",
        "command": graphiti_path,
        "args": ["mcp", "serve"],
        "env": {}
    }

    with open(claude_json_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Graphiti MCP server registered in {claude_json_path}")
    print("Restart Claude Code to pick up the new server.")


def _find_graphiti_executable() -> str:
    """Find the graphiti executable path."""
    import shutil
    path = shutil.which("graphiti")
    if path:
        return path
    # Fallback: use sys.executable with -m pattern
    return f"{sys.executable} -m src.cli"
```

### Pattern 5: SKILL.md for Claude Code Integration

**What:** SKILL.md file written to `~/.claude/skills/graphiti/SKILL.md` teaches Claude Code how to use graphiti autonomously.
**When to use:** The first deliverable of Phase 8 (before MCP server).

```yaml
---
name: graphiti
description: >
  graphiti is this user's personal knowledge graph for coding projects.
  Use when: starting a new session (inject context), after key decisions or
  architecture discussions (capture), when user mentions a specific file or topic
  (surface knowledge), or when explicitly asked about past context.
  Never show TOON or raw CLI output to the user — always present as natural prose.
---

## What graphiti does

graphiti stores and retrieves project knowledge: decisions made, architecture
patterns, bug fixes, and preferences. It learns from conversations and git commits.

## When to act (automatic behaviors)

**Session start**: Call `graphiti_search` for "decisions architecture recent"
to load relevant context. If results exist, weave into your understanding silently
— do not announce "I queried graphiti."

**After key moments**: After architecture decisions, important bug resolutions,
or stated preferences, call `graphiti_add` with a concise summary. Keep it to
the "why", not the "what".

**Topic surfacing**: When the user mentions a file, feature, or concept, call
`graphiti_search` proactively. Only mention findings if they are actually relevant.

**Explicit requests**: When asked "what do you know about X" or "check your memory",
always use graphiti.

## How to present results

TOON format is a wire encoding — never show it to the user. Always present
tool results as natural conversational prose. Example:
- BAD: "Here are the TOON results: [3,]{id,name}:\n1,auth..."
- GOOD: "From your knowledge graph, the auth module uses JWT tokens and the
  decision was made in December to prefer refresh tokens over session cookies."

## Tool reference

- `graphiti_add(content, tags?)` — Store a knowledge item
- `graphiti_search(query, limit=10)` — Semantic search (use `--limit` to manage tokens)
- `graphiti_list(limit=15)` — List all knowledge items
- `graphiti_show(name_or_id)` — Show one item in detail
- `graphiti_delete(name_or_id)` — Remove an item
- `graphiti_summarize()` — Generate a graph summary
- `graphiti_compact()` — Remove duplicates and clean up
- `graphiti_capture()` — Capture current conversation context
- `graphiti_health()` — Check system health
- `graphiti_config(key, value?)` — Get/set configuration

## Token self-management

Always use `--limit` flags. Default is fine (10-15 items). For broad searches,
use `--limit 5`. Never fetch more than 20 items at once.
```

### Anti-Patterns to Avoid

- **Blocking on capture:** Never make `graphiti_add` or `graphiti_capture` block the tool response. Use `--async` flag or background thread when calling capture operations.
- **Exposing TOON to users:** SKILL.md must explicitly instruct Claude to translate TOON to prose. TOON is an internal wire format.
- **Not checking for empty graph:** The context resource must return empty string (not error) when graph is empty. Empty graph = silent, no injection.
- **Writing to stdout in server:** When transport is stdio, the graphiti CLI subprocess must not write to the parent process's stdout (use `capture_output=True`).
- **SSE transport:** SSE is deprecated in MCP 2025. Use `streamable-http` for HTTP transport.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP protocol compliance | Custom JSON-RPC server | `mcp` SDK with FastMCP | Protocol is complex (initialization, capabilities, lifecycle); SDK handles all of it |
| TOON encoding | Custom encoder | `python-toon` 0.1.3 | Spec-compliant, MIT, 5 lines to install; custom encoder risks spec drift |
| Token counting | Character regex parser | 4 chars/token approximation OR `tiktoken` | Budget trimming needs approximation, not exactness; tiktoken adds dependency for marginal gain |
| Transport negotiation | Custom HTTP/stdio multiplexer | `mcp.run(transport=...)` | FastMCP handles transport selection, connection lifecycle, message routing |

**Key insight:** The MCP SDK handles all protocol complexity. Every tool is just: validate args → run subprocess → return string/TOON. The hard part is the subprocess invocation pattern, not the protocol.

---

## Common Pitfalls

### Pitfall 1: Stdout Contamination in Stdio Mode
**What goes wrong:** Any `print()` or `console.print()` call in the server process writes to stdout, which stdio transport uses for JSON-RPC messages. This corrupts the protocol.
**Why it happens:** The server imports modules that write to stdout on import (structlog, Rich console, etc.).
**How to avoid:** In the MCP server module, redirect all logging to stderr (`logging.basicConfig(stream=sys.stderr)`). Do not import Rich console in the server module. Use `structlog` with stderr sink.
**Warning signs:** Claude Code reports "invalid JSON" or "connection error" immediately on startup.

### Pitfall 2: Subprocess CWD for Scope Detection
**What goes wrong:** The graphiti CLI uses `GraphSelector.determine_scope()` which checks the current working directory for a `.git` folder. If the subprocess inherits the wrong CWD, it routes to global scope instead of project scope.
**Why it happens:** `subprocess.run()` inherits the parent's CWD. The MCP server CWD is wherever Claude Code launched it from (usually the project root, but not guaranteed).
**How to avoid:** Always pass `cwd=` to subprocess calls when a project root is known. For the context resource, detect CWD at request time (not server startup).
**Warning signs:** Context always comes from global graph even when in a project.

### Pitfall 3: Blocking on Async Capture
**What goes wrong:** `graphiti_capture()` tool blocks for 5-10 seconds while the LLM processes the conversation. Claude Code shows a spinner and the user sees a delay.
**Why it happens:** Capture involves LLM summarization which is slow.
**How to avoid:** Use `subprocess.Popen()` with `--async` flag (non-blocking subprocess launch), or run capture in a daemon thread. Return immediately: "Capture started in background."
**Warning signs:** `graphiti_capture` tool takes >2 seconds to return.

### Pitfall 4: Stale Index Detection Blocking Context
**What goes wrong:** Checking if index is stale (comparing git HEAD to last indexed SHA) triggers a full re-index before returning context, making context injection >100ms.
**Why it happens:** Re-indexing can take 10-60 seconds for large repos.
**How to avoid:** Stale detection should trigger a background re-index, not block context injection. Return current (possibly slightly stale) context immediately. Log that re-index was triggered.
**Warning signs:** Context injection latency >100ms at p95.

### Pitfall 5: MCP v2 Breaking Changes
**What goes wrong:** MCP v2 is planned for Q1 2026 (per search results). If it releases during Phase 8, the 1.x API may break.
**Why it happens:** Major version change with transport layer rework.
**How to avoid:** Pin `mcp>=1.26.0,<2.0.0` in pyproject.toml. Test with 1.26.0 specifically.
**Warning signs:** Import errors after pip upgrade.

### Pitfall 6: TOON Encoding Non-Array Data
**What goes wrong:** TOON's token savings are greatest for uniform arrays of objects (search results). For single-entity responses or plain text, TOON adds overhead vs plain text.
**Why it happens:** TOON header overhead is fixed cost; savings only appear at 3+ items.
**How to avoid:** Only TOON-encode responses that contain arrays with 3+ items. Return plain text for single-item responses (`graphiti_show`, `graphiti_add`, `graphiti_health`).
**Warning signs:** TOON output is larger than raw JSON for simple responses.

---

## Code Examples

Verified patterns from official sources:

### FastMCP Server Initialization
```python
# Source: modelcontextprotocol.github.io/python-sdk/
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "graphiti",
    instructions=(
        "graphiti is a knowledge graph for coding projects. "
        "All tool responses use TOON format — present to users as natural prose, never as raw data."
    )
)
```

### Running with Both Transports
```python
# Source: modelcontextprotocol.github.io/python-sdk/
# stdio (default, Claude Code managed subprocess)
mcp.run(transport="stdio")

# Streamable HTTP (standalone server, port 8000)
mcp.run(transport="streamable-http")
# Note: "sse" transport is deprecated per MCP spec 2025-03-26
```

### TOON Encoding a Search Result List
```python
# Source: pypi.org/project/python-toon/ (verified)
# Source: github.com/xaviviro/python-toon
from toon import encode

search_results = [
    {"id": "abc123", "name": "JWT Auth Decision", "summary": "Use refresh tokens"},
    {"id": "def456", "name": "Database Choice", "summary": "Switched to Kuzu"},
]
toon_output = encode(search_results)
# Output:
# [2,]{id,name,summary}:
# abc123,JWT Auth Decision,Use refresh tokens
# def456,Database Choice,Switched to Kuzu
```

### Subprocess Tool Pattern
```python
# Source: Verified against existing codebase patterns (src/hooks/manager.py)
import subprocess
import json

def _run_graphiti(args: list[str], timeout: int = 30, cwd: str | None = None) -> dict:
    """Run graphiti CLI and return parsed JSON output."""
    result = subprocess.run(
        ["graphiti"] + args + ["--format", "json"],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"graphiti {args[0]} failed")
    if not result.stdout.strip():
        return {}
    return json.loads(result.stdout)
```

### Claude Code Config Registration (mcp install)
```python
# Source: code.claude.com/docs/en/mcp (Official docs, verified)
# ~/.claude.json format for user-scope MCP servers (available all projects)
config_entry = {
    "mcpServers": {
        "graphiti": {
            "type": "stdio",
            "command": "/path/to/graphiti",  # or full python path
            "args": ["mcp", "serve"],
            "env": {}
        }
    }
}
# This is the "user scope" — stored in ~/.claude.json
# Also used: ~/.claude.json under project paths for "local scope"
```

### SKILL.md Location (Agent Skills standard)
```bash
# Personal skill (all projects): standard location per Claude Code docs
~/.claude/skills/graphiti/SKILL.md

# Project skill (this project only):
.claude/skills/graphiti/SKILL.md
```

### Token Budget Enforcement
```python
# Approximation: 4 characters per token (sufficient for budget enforcement)
# Source: Research — Anthropic does not ship a local tokenizer for Claude 3+
# tiktoken (OpenAI) has ~12% error rate for Claude models — not worth the dependency

def trim_to_token_budget(text: str, token_budget: int) -> str:
    """Trim TOON text to approximate token budget."""
    char_budget = token_budget * 4  # 4 chars per token approximation
    if len(text) <= char_budget:
        return text
    # TOON rows are newline-delimited — trim oldest (top) rows first
    lines = text.split("\n")
    header_lines = []
    data_lines = []
    # Preserve TOON header (first 1-2 lines with schema)
    for i, line in enumerate(lines):
        if line.startswith("[") or "{" in line:
            header_lines.append(line)
        else:
            data_lines = lines[i:]
            break
    # Remove oldest data rows until within budget
    while data_lines and len("\n".join(header_lines + data_lines)) > char_budget:
        data_lines.pop(0)
    return "\n".join(header_lines + data_lines)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SSE (Server-Sent Events) HTTP transport | Streamable HTTP transport | MCP spec 2025-03-26 | SSE deprecated; use `transport="streamable-http"` not `"sse"` |
| HTTP+SSE separate endpoints | Single MCP endpoint (POST + GET) | MCP spec 2025-03-26 | One endpoint handles both directions |
| `mcp.server.Server` low-level API | `FastMCP` decorator API | mcp SDK v0.9+ | FastMCP is the blessed high-level interface; less boilerplate |
| Claude Desktop `claude_desktop_config.json` | Claude Code `~/.claude.json` | 2025 | Claude Code uses `~/.claude.json` for user-scope MCP; `.mcp.json` for project-scope |
| Manual MCP config editing | `claude mcp add` CLI | 2025 | Preferred setup method; `graphiti mcp install` wraps this pattern |

**Deprecated/outdated:**
- `"sse"` transport: deprecated per MCP spec 2025-03-26; replace with `"streamable-http"`
- `claude_desktop_config.json`: This is for Claude Desktop. Claude Code uses `~/.claude.json`
- MCP spec 2024-11-05: R6.1 references this spec version. Implement against latest (2025-03-26). Backward compat is maintained.

---

## Open Questions

1. **MCP v2 timeline risk**
   - What we know: v2 is planned for Q1 2026, current is 1.26.0. v2 will change transport layer.
   - What's unclear: Whether v2 will drop 1.x compat; actual release date.
   - Recommendation: Pin `mcp>=1.26.0,<2.0.0`. Monitor GitHub releases. Phase 8 will complete before v2 is ready.

2. **Stale index triggering during context injection**
   - What we know: Re-indexing can be slow (10-60s). Context injection must be <100ms (p95).
   - What's unclear: Best async pattern for background re-index that doesn't block context.
   - Recommendation: In context resource, check staleness in <10ms (compare HEAD SHA to stored SHA), start background subprocess if stale, return current context from existing index without waiting. Accept slightly stale context rather than blocking.

3. **TOON header in trimmed output**
   - What we know: TOON format has a header line with `[N,]{field1,field2}:` followed by data rows.
   - What's unclear: After trimming rows, the `[N,]` count is wrong.
   - Recommendation: Update the count in the header after trimming. Or omit the count (TOON spec allows `[,]` without count). Needs implementation testing.

4. **`graphiti mcp serve` vs entry point**
   - What we know: `graphiti mcp install` writes `"args": ["mcp", "serve"]` to ~/.claude.json.
   - What's unclear: Whether to register as `app.add_typer(mcp_app)` in CLI or as `app.command("mcp")`.
   - Recommendation: Use `app.add_typer(mcp_app, name="mcp")` (consistent with `hooks` and `queue` command groups). Add `graphiti mcp serve` and `graphiti mcp install` as subcommands.

---

## Sources

### Primary (HIGH confidence)
- Official MCP Python SDK GitHub (modelcontextprotocol/python-sdk) — server creation, FastMCP, transports, resource/tool decorators, Claude Desktop config
- Official Claude Code docs (code.claude.com/docs/en/mcp) — `~/.claude.json` format, `claude mcp add` command, scope hierarchy (user/project/local)
- Official Claude Code docs (code.claude.com/docs/en/skills) — SKILL.md format, YAML frontmatter, Agent Skills standard, skill discovery
- PyPI: mcp 1.26.0 (released January 24, 2026) — confirmed current stable version
- PyPI: python-toon 0.1.3 (released November 4, 2025) — confirmed correct Python TOON package
- MCP Spec 2025-03-26 (modelcontextprotocol.io) — transports, stdio, streamable-http, SSE deprecation, session management

### Secondary (MEDIUM confidence)
- TOON format benchmarks (toonformat.dev, InfoQ article Nov 2025) — ~40% token reduction for uniform arrays; 99.4% accuracy with latest models
- python-toon README (github.com/xaviviro/python-toon) — encode/decode API, list-of-dicts encoding
- WebSearch: MCP v2 Q1 2026 roadmap — v2 in development, 1.x maintained for stability

### Tertiary (LOW confidence)
- Token counting approximation (4 chars/token for Claude) — multiple blog posts agree; Anthropic's tokenizer is not public for local use
- Stale index detection pattern — derived from existing codebase patterns in `src/indexer/state.py`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — mcp 1.26.0 confirmed on PyPI; python-toon 0.1.3 confirmed; FastMCP is official SDK pattern
- Architecture: HIGH — subprocess pattern matches existing codebase (manager.py, hooks); FastMCP decorator pattern verified
- Pitfalls: HIGH — stdout contamination is well-documented MCP pitfall; others derived from codebase analysis
- SKILL.md format: HIGH — official Claude Code docs verified format, location, frontmatter fields
- Token budget: MEDIUM — char-count approximation is pragmatic; exact token count for Claude requires Anthropic API call
- TOON trimming header fix: LOW — implementation detail that requires testing

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (30 days; MCP SDK v2 could change things, pin 1.x)
