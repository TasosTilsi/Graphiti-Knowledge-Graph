---
phase: 08-mcp-server
plan: 01
subsystem: mcp
tags: [mcp, fastmcp, toon, python-toon, encoding, token-budget]

# Dependency graph
requires:
  - phase: 07.1-git-indexing-pivot
    provides: indexer and CLI foundation that MCP server will wrap
provides:
  - mcp[cli]>=1.26.0,<2.0.0 dependency declared and installed in venv
  - python-toon>=0.1.3 dependency declared and installed in venv
  - src/mcp_server/ package scaffolded with __init__.py
  - encode_response() utility with 3-item TOON threshold
  - trim_to_token_budget() utility with 4-char/token approximation
affects: [08-02, 08-03, 08-04, 08-05]

# Tech tracking
tech-stack:
  added:
    - mcp[cli]==1.26.0 (Official Anthropic MCP Python SDK with FastMCP framework)
    - python-toon==0.1.3 (TOON encoding — ~40% token reduction for uniform arrays)
  patterns:
    - TOON threshold pattern: encode_response uses TOON for 3+ item lists, JSON for scalars/small lists
    - Token budget approximation: 4 chars/token (no tiktoken dependency, sufficient for budget trimming)
    - Header preservation pattern: trim_to_token_budget separates TOON header from data rows, updates [N,] count

key-files:
  created:
    - src/mcp_server/__init__.py
    - src/mcp_server/toon_utils.py
  modified:
    - pyproject.toml

key-decisions:
  - "mcp[cli]>=1.26.0,<2.0.0 upper bound pins to stable 1.x branch before MCP v2 (planned Q1 2026)"
  - "TOON 3-item threshold: header overhead exceeds savings for <3 items (Pitfall 6 from research)"
  - "4 chars/token approximation is sufficient for token budget trimming — tiktoken avoided as dependency"
  - "trim_to_token_budget() updates [N,] row count in header after trimming via regex substitution"
  - "No Rich/structlog imports in toon_utils.py — stdio transport uses stdout for JSON-RPC, any print() corrupts protocol"

patterns-established:
  - "Stdio safety: Never write to stdout in MCP server modules — use stderr or omit logging"
  - "TOON encoding: only apply to arrays with 3+ items to ensure token savings"
  - "Token budget trimming: preserve TOON header, remove oldest data rows, update header count"

requirements-completed: [R6.2, R6.3]

# Metrics
duration: 2min
completed: 2026-02-21
---

# Phase 8 Plan 01: MCP Server Foundation Summary

**mcp[cli] 1.26.0 and python-toon 0.1.3 installed; src/mcp_server/ scaffolded with TOON encode_response() (3-item threshold) and trim_to_token_budget() (4-char/token approximation, header-preserving row trimming)**

## Performance

- **Duration:** ~2 min (107 seconds)
- **Started:** 2026-02-21T16:44:32Z
- **Completed:** 2026-02-21T16:46:19Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `mcp[cli]>=1.26.0,<2.0.0` and `python-toon>=0.1.3` to pyproject.toml and verified both importable from venv
- Created `src/mcp_server/__init__.py` package init with module docstring describing the planned server architecture
- Created `src/mcp_server/toon_utils.py` with `encode_response()` and `trim_to_token_budget()` — the shared encoding primitives used by tools.py and context.py in later plans

## Task Commits

Each task was committed atomically:

1. **Task 1: Add mcp and python-toon to pyproject.toml dependencies** - `6ac1505` (chore)
2. **Task 2: Create src/mcp_server/ package with TOON utility module** - `4cd7bd6` (feat)

## Files Created/Modified

- `pyproject.toml` — Added mcp[cli]>=1.26.0,<2.0.0 and python-toon>=0.1.3 to dependencies list
- `src/mcp_server/__init__.py` — Package init with module docstring (server.py, tools.py, context.py, install.py, toon_utils.py)
- `src/mcp_server/toon_utils.py` — TOON encoding utilities: encode_response() with 3-item threshold, trim_to_token_budget() with header preservation and row count update

## Decisions Made

- **TOON 3-item threshold**: encode_response() uses TOON for arrays with 3+ items and JSON for anything smaller. TOON header overhead exceeds token savings for <3 items (Pitfall 6 from research).
- **4 chars/token approximation**: Used for trim_to_token_budget() instead of tiktoken. Character-count approximation is sufficient for budget enforcement; tiktoken is OpenAI-specific with ~12% error for Claude models.
- **Header count update after trim**: trim_to_token_budget() uses regex to update the `[N,]` row count in the TOON header after trimming rows. This keeps the header accurate for downstream consumers.
- **mcp[cli] 1.x upper bound**: `<2.0.0` pins to stable 1.x branch since MCP v2 is planned for Q1 2026 and may break the FastMCP API.
- **No stdout writes in toon_utils.py**: Stdio transport uses stdout for JSON-RPC. Any print() in imported modules corrupts the protocol. toon_utils.py has no logging at all (pure encoding functions).

## Deviations from Plan

None - plan executed exactly as written.

The one deviation candidate was the `pip install` command failing for system pip (externally-managed environment). Resolved by using the project's `.venv/bin/pip` instead. This is an infrastructure configuration detail, not a plan deviation.

## Issues Encountered

- System `pip` refused to install (PEP 668 externally-managed environment). Used `.venv/bin/pip` instead — the project's virtual environment is at `.venv/`. No code changes needed.

## Verification Commands Run

```
# Task 1 verification
python -c "from mcp.server.fastmcp import FastMCP; from toon import encode; print('imports OK')"
# Output: imports OK

grep "mcp\[cli\]" pyproject.toml  # Output: "mcp[cli]>=1.26.0,<2.0.0",
grep "python-toon" pyproject.toml  # Output: "python-toon>=0.1.3",

# Task 2 verification
python -c "from src.mcp_server.toon_utils import encode_response, trim_to_token_budget; data = [...3 items...]; result = encode_response(data); assert result.startswith('[')"
# Output: TOON OK

python -c "from src.mcp_server.toon_utils import encode_response; result = encode_response({'id': '1', 'name': 'single'}); json.loads(result)"
# Output: single dict OK

python -c "from src.mcp_server.toon_utils import trim_to_token_budget; long_text = ...; trimmed = trim_to_token_budget(long_text, 1); assert len(trimmed) <= 10"
# Output: trim OK

# Overall verification
python -c "from src.mcp_server import toon_utils; print(toon_utils.__all__)"
# Output: ['encode_response', 'trim_to_token_budget']

pip show mcp python-toon  # Both listed: mcp 1.26.0, python-toon 0.1.3
```

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 8 Plan 02 (server.py + tools.py) can now import from `src.mcp_server.toon_utils`
- Phase 8 Plan 03 (context.py + SKILL.md) can use `encode_response()` and `trim_to_token_budget()`
- Phase 8 Plan 04 (install.py + CLI wiring) depends on server.py from Plan 02
- All plans unblocked: mcp SDK importable, TOON encoder available, package scaffolded

## Self-Check: PASSED

All created files verified on disk:
- FOUND: `src/mcp_server/__init__.py`
- FOUND: `src/mcp_server/toon_utils.py`
- FOUND: `.planning/phases/08-mcp-server/08-01-SUMMARY.md`

All task commits verified in git log:
- FOUND: `6ac1505` — chore(08-01): add mcp and python-toon to pyproject.toml dependencies
- FOUND: `4cd7bd6` — feat(08-01): create src/mcp_server/ package with TOON utility module

---
*Phase: 08-mcp-server*
*Completed: 2026-02-21*
