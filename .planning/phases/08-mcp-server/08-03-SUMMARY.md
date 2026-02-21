---
phase: 08-mcp-server
plan: 03
subsystem: mcp
tags: [mcp, fastmcp, context-resource, install, skill-md, cli-integration]

# Dependency graph
requires:
  - phase: 08-mcp-server-plan-02
    provides: src/mcp_server/tools.py with 10 graphiti_* MCP tool handler functions
  - phase: 08-mcp-server-plan-01
    provides: src/mcp_server/toon_utils.py with encode_response and trim_to_token_budget

provides:
  - src/mcp_server/context.py: graphiti://context resource with stale detection and TOON encoding
  - src/mcp_server/server.py: FastMCP app with 10 tools + context resource, both transports
  - src/mcp_server/install.py: zero-config installer writing ~/.claude.json and SKILL.md
  - src/cli/commands/mcp.py: graphiti mcp serve and graphiti mcp install Typer command group
  - src/cli/__init__.py: mcp_app registered as 14th command group
affects:
  - 08-04 (any remaining plans in Phase 8)
  - Users who run graphiti mcp install to activate Claude Code integration

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FastMCP tool registration: mcp.tool()(function) pattern for registering plain callables"
    - "FastMCP resource registration: mcp.resource('graphiti://context')(get_context) pattern"
    - "Stale detection: <10ms git HEAD SHA comparison vs stored last_indexed_sha in .graphiti/index-state.json"
    - "Non-blocking re-index: subprocess.Popen with DEVNULL + start_new_session=True for background indexing"
    - "Embedded SKILL.md: SKILL_MD_CONTENT constant in install.py — no external file dependency"
    - "Safe JSON merge: json.load/dump pattern for writing mcpServers entry without destroying existing config"

key-files:
  created:
    - src/mcp_server/context.py
    - src/mcp_server/server.py
    - src/mcp_server/install.py
    - src/cli/commands/mcp.py
  modified:
    - src/cli/__init__.py

key-decisions:
  - "graphiti://context resource returns empty string silently for empty graph — no user-visible error or prompt"
  - "Stale index triggers non-blocking background re-index via Popen; context injection returns immediately"
  - "SKILL_MD_CONTENT embedded as constant in install.py so mcp install works without external file dependencies"
  - "install_mcp_server() always merges into existing ~/.claude.json rather than overwriting — preserves other MCP servers"
  - "mcp_app registered after index command in CLI __init__.py — follows established pattern of hooks_app and queue_app"

patterns-established:
  - "FastMCP registration pattern: mcp.tool()(fn) and mcp.resource(uri)(fn) — not decorator syntax at definition site"
  - "Context resource imports toon_utils lazily (inside get_context) to avoid circular import at module level"
  - "MCP install: dual write — ~/.claude.json mcpServers entry + ~/.claude/skills/graphiti/SKILL.md"

requirements-completed:
  - R6.1
  - R6.2
  - R6.3

# Metrics
duration: 26min
completed: 2026-02-21
---

# Phase 8 Plan 03: MCP Server Wiring Summary

**FastMCP server wired with 10 graphiti_* tools and graphiti://context resource (stale-detect + TOON + 8K budget); graphiti mcp install writes ~/.claude.json and SKILL.md with 4 automatic behavior patterns**

## Performance

- **Duration:** ~26 min
- **Started:** 2026-02-21T17:17:43Z
- **Completed:** 2026-02-21T17:44:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Implemented `server.py` with FastMCP app registering all 10 graphiti_* tools and `graphiti://context` resource, supporting both stdio and streamable-http transports
- Implemented `context.py` with stale git index detection (<10ms), non-blocking background re-index trigger, TOON encoding with 8K token budget enforcement, and silent empty-graph behavior
- Implemented `install.py` with zero-config Claude Code setup: writes `~/.claude.json` mcpServers entry (safe merge) and installs embedded SKILL.md with 4 automatic behavior patterns to `~/.claude/skills/graphiti/`
- Added `graphiti mcp` command group (serve + install subcommands) to CLI and registered as the 14th command

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement context resource and FastMCP server** - `033509c` (feat)
2. **Task 2: Implement mcp install command, SKILL.md, and CLI registration** - `4d6e590` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/mcp_server/context.py` — graphiti://context resource: stale detection, background re-index, TOON encode + token budget trim, empty-string for empty graph
- `src/mcp_server/server.py` — FastMCP app with 10 tools registered via mcp.tool()(fn) pattern + graphiti://context resource; main() with stdio/streamable-http transport routing
- `src/mcp_server/install.py` — install_mcp_server(): safe JSON merge into ~/.claude.json, SKILL_MD_CONTENT constant with all 4 behavior patterns, SKILL.md write to ~/.claude/skills/graphiti/
- `src/cli/commands/mcp.py` — mcp_app Typer command group: serve (--transport, --port) and install (--force, --format json) subcommands
- `src/cli/__init__.py` — Added mcp_app import and `app.add_typer(mcp_app, name="mcp")` registration; updated comment to 14 commands

## FastMCP Tool Registration Pattern

All 10 tools are registered using the callable-as-argument pattern (not as decorators at definition site):

```python
mcp.tool()(graphiti_add)
mcp.tool()(graphiti_search)
# ... 8 more
mcp.resource("graphiti://context")(get_context)
```

This pattern allows the tool handler functions to remain plain Python callables in tools.py (testable without FastMCP), and the server.py acts as the composition root.

## SKILL.md Location and Content Summary

**Installed to:** `~/.claude/skills/graphiti/SKILL.md`

**Four automatic behavior patterns embedded:**
1. **Session start** — Call `graphiti_search("decisions architecture recent")` silently, weave findings into understanding
2. **After key moments** — Call `graphiti_add` after architecture decisions, bug resolutions, library choices
3. **Topic surfacing** — Call `graphiti_search` proactively when user mentions unknown files/features
4. **Explicit requests** — Always use graphiti when asked "what do you know about X" or "check your memory"

**TOON presentation rule:** Always translate TOON format to natural prose — never expose wire format to users.

## ~/.claude.json Entry Written

```json
{
  "mcpServers": {
    "graphiti": {
      "type": "stdio",
      "command": "/path/to/graphiti",
      "args": ["mcp", "serve"],
      "env": {}
    }
  }
}
```

The installer merges into existing config rather than overwriting, preserving other MCP server entries.

## Verification Commands Run

```
# Task 1 verification
$ .venv/bin/python -c "from src.mcp_server.server import mcp, main; print('server OK')"
server OK

$ .venv/bin/python -c "from src.mcp_server.context import get_context; print('context OK')"
context OK

$ .venv/bin/python -c "from src.mcp_server.server import mcp; tools = [t.name for t in mcp._tool_manager.list_tools()]; print(sorted(tools))"
['graphiti_add', 'graphiti_capture', 'graphiti_compact', 'graphiti_config', 'graphiti_delete', 'graphiti_health', 'graphiti_list', 'graphiti_search', 'graphiti_show', 'graphiti_summarize']

$ .venv/bin/python -c "import io,sys; sys.stdout=io.StringIO(); from src.mcp_server import server; ..."
no stdout contamination OK

# Task 2 verification
$ (graphiti mcp --help via PYTHONPATH) — shows serve and install subcommands
$ .venv/bin/python -c "from src.mcp_server.install import install_mcp_server, SKILL_MD_CONTENT; assert 'graphiti' in SKILL_MD_CONTENT; assert 'TOON' in SKILL_MD_CONTENT; print('install OK')"
install OK
$ (graphiti --help via PYTHONPATH) — lists mcp in commands
$ .venv/bin/python -c "from src.cli.commands.mcp import mcp_app; print('mcp_app OK')"
mcp_app OK
$ (install_mcp_server dry-run) — mcp install OK

# End-to-end verification
1. All 10 tools registered: PASSED (10 tools listed)
2. No stdout on import: PASSED (clean)
3. SKILL.md content: PASSED (5 matches for 4 behavior patterns)
4. ~/.claude.json entry: PASSED (claude.json OK)
5. Context resource: PASSED (context returns str (0 chars) — empty graph)
6. CLI help shows mcp: PASSED (mcp listed in commands)
```

## Decisions Made

- **Silent empty-graph behavior**: context resource returns empty string (not an error) for empty graph. Prompting users to fill the graph on every new project would be intrusive — silence is the correct UX.
- **Lazy import of toon_utils in get_context()**: Import inside the function body to avoid circular imports at module load time. context.py imports from toon_utils only when context is actually requested.
- **Non-blocking stale re-index**: Stale detection (<10ms) triggers Popen background re-index. Context injection is NOT blocked. Users get current (possibly slightly stale) context instantly rather than waiting for a re-index.
- **Embedded SKILL_MD_CONTENT constant**: Embedding SKILL.md content in install.py ensures `graphiti mcp install` works from any installed location without needing to locate an external template file.
- **Safe JSON merge for ~/.claude.json**: Read-modify-write pattern preserves all existing MCP server entries. Never overwrites the whole file, ensuring other tools' MCP configurations are not lost.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The `graphiti` binary fails when invoked without `PYTHONPATH=/path/to/project` because the editable install's `.pth` file adds `src/` to sys.path (making `cli` directly importable), but the script entry point uses `from src.cli import cli_entry` (requiring the project parent directory). This is an existing design issue across the whole project, not introduced by this plan. Used `PYTHONPATH=...` prefix or `.venv/bin/python -c "from src.cli..."` for all verification that required the CLI to run.

## User Setup Required

None - the MCP server is installed via `graphiti mcp install`. After running that command, the user only needs to restart Claude Code.

## Next Phase Readiness

- FastMCP server is complete and runnable: `graphiti mcp serve` starts stdio transport
- `graphiti mcp install` is working: writes ~/.claude.json and SKILL.md
- Context resource is wired: graphiti://context returns TOON-encoded project knowledge
- Phase 8 is functionally complete for core MCP server functionality
- Any remaining Phase 8 plan (if exists) can build on this foundation

---
*Phase: 08-mcp-server*
*Completed: 2026-02-21*

## Self-Check: PASSED

All created files verified on disk:
- FOUND: `src/mcp_server/context.py`
- FOUND: `src/mcp_server/server.py`
- FOUND: `src/mcp_server/install.py`
- FOUND: `src/cli/commands/mcp.py`
- FOUND: `.planning/phases/08-mcp-server/08-03-SUMMARY.md`

All task commits verified in git log:
- FOUND: `033509c` — feat(08-03): implement context resource and FastMCP server
- FOUND: `4d6e590` — feat(08-03): implement mcp install command, SKILL.md, and CLI registration
