---
phase: 08-mcp-server
plan: 02
subsystem: api
tags: [mcp, subprocess, fastmcp, toon, tools, graphiti-cli]

# Dependency graph
requires:
  - phase: 08-mcp-server-plan-01
    provides: src/mcp_server/toon_utils.py with encode_response and trim_to_token_budget

provides:
  - src/mcp_server/tools.py with 10 graphiti_* MCP tool handler functions
  - _run_graphiti() subprocess helper with GRAPHITI_PROJECT_ROOT env var support
  - _get_cwd() scope-detection helper
  - Non-blocking graphiti_capture using subprocess.Popen + DEVNULL + start_new_session
affects:
  - 08-03 (server.py that registers these tools with @mcp.tool())
  - 08-04 (install.py and mcp install command)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subprocess CLI wrapper pattern: all tools call graphiti CLI via _run_graphiti()"
    - "GRAPHITI_PROJECT_ROOT env var override for CWD/scope detection"
    - "Non-blocking Popen with DEVNULL for LLM-heavy async operations"
    - "ImportError fallback for encode_response (plan ordering tolerance)"
    - "RuntimeError with actionable message on non-zero subprocess exit"
    - "graphiti_health: informational — returns warning string, never raises"

key-files:
  created:
    - src/mcp_server/tools.py
  modified: []

key-decisions:
  - "Always pass --force to graphiti_delete: MCP callers have no interactive TTY for confirmation"
  - "graphiti_health never raises on non-zero exit: health check failures are informational, not errors"
  - "graphiti_capture uses subprocess.Popen with start_new_session=True and DEVNULL to prevent stdio corruption"
  - "encode_response ImportError fallback to json.dumps ensures tools.py works even before toon_utils.py is created"
  - "_scope_flags() extracts flag generation into shared helper to avoid repetition across tools"
  - "logging.basicConfig(stream=sys.stderr) at module level ensures all logger.* calls go to stderr"

patterns-established:
  - "Subprocess CLI wrapper: _run_graphiti(args, timeout, cwd) returns (returncode, stdout, stderr) tuple"
  - "CWD precedence: GRAPHITI_PROJECT_ROOT > caller-supplied cwd > inherited process CWD"
  - "RuntimeError with f-string including stripped stderr for actionable error messages"

requirements-completed:
  - R6.1
  - R6.3

# Metrics
duration: 8min
completed: 2026-02-21
---

# Phase 8 Plan 02: MCP Tool Handlers Summary

**10 graphiti_* CLI-wrapper tool handlers in tools.py using subprocess.run (read tools) and Popen (capture) with TOON encoding for array results**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-02-21T16:44:36Z
- **Completed:** 2026-02-21T16:52:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Implemented all 10 graphiti_* MCP tool functions ready for @mcp.tool() registration
- _run_graphiti helper respects GRAPHITI_PROJECT_ROOT env var for correct project scope detection
- graphiti_capture uses non-blocking subprocess.Popen with DEVNULL and start_new_session=True preventing stdio corruption
- encode_response imported with ImportError fallback ensuring tools.py works regardless of plan ordering

## Task Commits

Each task was committed atomically:

1. **Task 1: _run_graphiti helper and 5 read tools** - `1e1c196` (feat) — includes all 10 tools since file was created atomically
2. **Task 2: 5 write/action tools and __all__** — included in `1e1c196` (file written complete in Task 1)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/mcp_server/tools.py` - 10 graphiti_* tool handler functions, _run_graphiti helper, _get_cwd helper, _scope_flags helper

## Tool Signatures and Subprocess Commands

| Tool | Subprocess Command | Notes |
|------|--------------------|-------|
| `graphiti_search(query, limit, exact, scope)` | `graphiti search <query> --limit N --format json [--exact] [--global\|--project]` | TOON for 3+ results |
| `graphiti_list(limit, scope)` | `graphiti list --limit N --format json [--global\|--project]` | TOON for 3+ results |
| `graphiti_show(name_or_id)` | `graphiti show <id> --format json` | JSON (single dict) |
| `graphiti_summarize(scope)` | `graphiti summarize --format json [--global\|--project]` | JSON (single dict) |
| `graphiti_health()` | `graphiti health --format json` | Plain stdout; warning on failure |
| `graphiti_add(content, tags, scope)` | `graphiti add <content> [--tags T] [--global\|--project]` | timeout=60s |
| `graphiti_delete(name_or_id, force)` | `graphiti delete <id> --force` | Always --force (no TTY) |
| `graphiti_compact(scope)` | `graphiti compact [--global\|--project]` | timeout=120s (LLM-slow) |
| `graphiti_capture()` | `graphiti capture --async` via Popen | Non-blocking, DEVNULL, new session |
| `graphiti_config(key, value)` | `graphiti config get\|set <key> [value]` | timeout=10s |

## Non-Blocking Capture Implementation

graphiti_capture uses subprocess.Popen (not subprocess.run) because capture operations involve LLM summarization taking 5-30 seconds. Key implementation choices:

- `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL`: Background process must not inherit stdio transport's file descriptors (stdout corruption would break JSON-RPC)
- `start_new_session=True`: Detaches from MCP server process group preventing zombie processes on server exit
- FileNotFoundError caught separately: provides actionable "pip install" error message
- Returns immediately with "Conversation capture started in background."

## CWD / Scope Detection Approach

_run_graphiti() applies a 3-level CWD priority:
1. `GRAPHITI_PROJECT_ROOT` env var (explicit override — set by orchestration or test harness)
2. caller-supplied `cwd` argument
3. None — inherits MCP server process CWD (which is Claude Code's working directory)

This means Claude Code running in `/home/user/myproject` automatically scopes operations to that project without any configuration.

## Verification Output

```
$ ./venv/bin/python -c "from src.mcp_server.tools import graphiti_search, graphiti_list, graphiti_show, graphiti_summarize, graphiti_health; print('5 read tools OK')"
5 read tools OK

$ ./venv/bin/python -c "from src.mcp_server.tools import graphiti_add, graphiti_delete, graphiti_compact, graphiti_capture, graphiti_config; print('5 write tools OK')"
5 write tools OK

$ ./venv/bin/python -c "from src.mcp_server import tools; print(sorted([f for f in dir(tools) if f.startswith('graphiti_')]))"
['graphiti_add', 'graphiti_capture', 'graphiti_compact', 'graphiti_config', 'graphiti_delete', 'graphiti_health', 'graphiti_list', 'graphiti_search', 'graphiti_show', 'graphiti_summarize']

$ ./venv/bin/python -c "import subprocess; from src.mcp_server.tools import graphiti_capture; import inspect; src = inspect.getsource(graphiti_capture); assert 'Popen' in src; assert 'DEVNULL' in src; print('non-blocking OK')"
non-blocking OK
```

## Decisions Made
- **--force always passed to graphiti_delete**: MCP callers have no interactive TTY for confirmation prompts; always-force is the correct MCP behavior
- **graphiti_health informational**: Returns warning string on non-zero exit rather than raising, because health check failures are status information not execution errors
- **encode_response ImportError fallback**: Ensures tools.py works even if Plan 01 toon_utils.py hasn't been created yet (plan ordering tolerance)
- **_scope_flags() shared helper**: Extracted to a private helper to avoid duplicating the if/elif/else scope flag logic across all 6 scoped tools

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing mcp and python-toon dependencies before creating tools.py**
- **Found during:** Task 1 (before starting)
- **Issue:** Plan 01 dependencies (mcp[cli], python-toon) were declared in pyproject.toml but not yet installed in the venv; `python -c "from mcp.server.fastmcp import FastMCP"` failed with ModuleNotFoundError
- **Fix:** Ran `./venv/bin/pip install -e ".[dev]"` which installed mcp-1.26.0, python-toon-0.1.3 and transitive deps
- **Files modified:** None (venv only)
- **Verification:** `./venv/bin/python -c "from mcp.server.fastmcp import FastMCP; from toon import encode; print('imports OK')"`
- **Committed in:** Not committed (venv installation, no source changes)

---

**Total deviations:** 1 auto-fixed (1 blocking — venv dependency install)
**Impact on plan:** Necessary prerequisite; no scope creep. tools.py created as planned.

## Issues Encountered
- toon_utils.py already existed in src/mcp_server/ (from a prior partial execution of Plan 01) — used as-is, ImportError fallback in tools.py not needed at runtime but retained for safety

## Next Phase Readiness
- All 10 graphiti_* tool functions importable from src.mcp_server.tools
- Ready for Plan 03 (server.py: FastMCP app, @mcp.tool() registrations, graphiti://context resource)
- No blockers

---
*Phase: 08-mcp-server*
*Completed: 2026-02-21*

## Self-Check: PASSED

- FOUND: src/mcp_server/tools.py
- FOUND: commit 1e1c196 (feat(08-02): implement _run_graphiti helper and 5 read-oriented MCP tools)
