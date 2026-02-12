---
phase: 04-cli-interface
plan: 08
subsystem: cli-graph-integration
tags: [gap-closure, graphiti, kuzu, real-data, cli-commands]

# Dependency graph
requires:
  - phase: 04-07
    provides: "GraphService with 8 operations, OllamaLLMClient/OllamaEmbedder adapters, async/sync bridge"
  - phase: 04-02
    provides: "CLI commands with stub functions returning mock data"
provides:
  - "Add command wired to GraphService.add() for real graph writes"
  - "Search command wired to GraphService.search() for real semantic/exact queries"
  - "List command wired to GraphService.list_entities() for real entity listing"
  - "LLM error handling with user-friendly messages in CLI"
affects: [04-09-gap-remaining-wiring, end-to-end-testing, cli-verification]

# Tech tracking
tech-stack:
  added: []
  patterns: [CLI-to-service wiring pattern, error handling for LLM unavailability, parameter threading from command to service]

key-files:
  created: []
  modified:
    - src/cli/commands/add.py
    - src/cli/commands/search.py
    - src/cli/commands/list_cmd.py

key-decisions:
  - "LLMUnavailableError handling: Catch in _add_entity and provide user-friendly message directing to 'graphiti health'"
  - "project_root parameter threading: Pass through from resolve_scope to _search_entities and _list_entities for correct scope resolution"
  - "Date/type/tag filters deferred: Document in search.py that these filters are future enhancements, not implemented yet"
  - "Tags format conversion: Convert list to string in list_cmd.py for display compatibility with table formatter"

patterns-established:
  - "CLI command wiring: Commands call private _function() which gets service via get_service() and wraps async calls in run_graph_operation()"
  - "Error propagation: Let LLMUnavailableError bubble up with enhanced user message, don't suppress"
  - "Parameter completeness: Thread all scope-related parameters (scope, project_root) from command through to service calls"

# Metrics
duration: 73.1min
completed: 2026-02-12
---

# Phase 04 Plan 08: CLI-to-Graph Wiring Summary

**Add, search, and list CLI commands now write/query real Kuzu graph via Graphiti instead of returning mock data**

## Performance

- **Duration:** 73.1 min (4390 seconds)
- **Started:** 2026-02-12T07:57:07Z
- **Completed:** 2026-02-12T09:10:21Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Add command calls GraphService.add() which invokes Graphiti.add_episode() to write real content to Kuzu graph with LLM extraction
- Search command calls GraphService.search() for semantic/exact queries against real stored entities/edges
- List command calls GraphService.list_entities() to retrieve actual entities from database (not mock data)
- All three commands now perform real graph operations with proper error handling

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire add command to GraphService** - `0262dc9` (feat)
2. **Task 2: Wire search and list commands to GraphService** - `f353754` (feat)

## Files Created/Modified
- `src/cli/commands/add.py` - Replaced _add_entity() stub with real GraphService.add() call, added LLMUnavailableError handling
- `src/cli/commands/search.py` - Replaced _search_entities() stub with GraphService.search() call, threaded project_root parameter
- `src/cli/commands/list_cmd.py` - Replaced _list_entities() stub with GraphService.list_entities() call, added scope/project_root/limit parameters

## Decisions Made

**LLMUnavailableError handling pattern:** Catch LLMUnavailableError in _add_entity() and provide user-friendly message directing users to 'graphiti health' command for diagnostics. This surfaces LLM configuration issues early with actionable guidance.

**project_root parameter threading:** Added project_root parameter to _search_entities() and _list_entities() functions to ensure correct scope resolution when calling GraphService. The resolve_scope() call in search_command and list_command already provides project_root as second return value, now we pass it through.

**Date/type/tag filters documented as future work:** search.py accepts since/before/type/tags parameters for CLI UX but documents that GraphService.search() doesn't yet support them. These filters will be added in future integration phases. Current semantic search returns all matching results.

**Tags format conversion in list_cmd:** Convert tags from list to string (", "-joined) in _list_entities() for compatibility with table formatter which expects string format. This matches the existing display logic.

## Deviations from Plan

None - plan executed exactly as written. All three commands wired to GraphService with proper parameter passing and error handling.

## Issues Encountered

None - imports succeeded, verification passed, all stub references removed cleanly.

## User Setup Required

None - no external service configuration required. Commands use existing GraphService which was configured in Plan 04-07.

## Next Phase Readiness

**Ready for Plan 04-09 (remaining gap closure):**
- Add, search, list commands now query real graph data
- Show, delete, summarize, compact, stats commands still use stubs (will be wired in 04-09)
- End-to-end testing can now verify real data flow from CLI → GraphService → Graphiti → Kuzu

**Blockers:** None. The primary gap (write, read, browse operations) is now closed. Remaining commands depend on understanding entity structure from actual usage.

## Self-Check

Verified all modified files exist:
- ✓ src/cli/commands/add.py
- ✓ src/cli/commands/search.py
- ✓ src/cli/commands/list_cmd.py

Verified commits exist:
- ✓ 0262dc9 (feat: wire add command)
- ✓ f353754 (feat: wire search and list commands)

Verified no mock/stub references remain:
- ✓ add.py: 0 occurrences
- ✓ search.py: 0 occurrences
- ✓ list_cmd.py: 0 occurrences

Verified GraphService integration:
- ✓ add.py: 5 references to get_service/run_graph_operation
- ✓ search.py: 6 references to get_service/run_graph_operation
- ✓ list_cmd.py: 5 references to get_service/run_graph_operation

Verified all commands import successfully:
- ✓ add_command, search_command, list_command all import without errors

## Self-Check: PASSED

---
*Phase: 04-cli-interface*
*Completed: 2026-02-12*
