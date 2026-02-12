---
phase: 05-background-queue
plan: 03
subsystem: cli
tags: [cli, queue-management, typer-commands, rich-output, dead-letter-recovery]

# Dependency graph
requires:
  - phase: 05-02
    provides: Background worker with public API (enqueue, get_status, process_queue)
provides:
  - Queue CLI command group accessible via 'graphiti queue'
  - status subcommand with health indicators and JSON format
  - process subcommand for manual queue processing fallback
  - retry subcommand for dead letter job recovery
affects: [06-git-hooks, 08-mcp-server]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Typer command group registration via app.add_typer()
    - Rich Table output for queue status with color-coded health
    - JSON format support for programmatic use
    - Health threshold pattern (ok/warning/error at 80%/100%)
    - Consistent output patterns matching health command

key-files:
  created:
    - src/cli/commands/queue_cmd.py
  modified:
    - src/cli/__init__.py

key-decisions:
  - "Health thresholds match graphiti health: ok < 80% < warning < 100% < error"
  - "JSON format support enables programmatic queue monitoring"
  - "process command blocks until queue empty (synchronous CLI fallback)"
  - "retry 'all' enables bulk dead letter recovery"
  - "Rich table output follows established health.py patterns"

patterns-established:
  - "CLI queue inspection: graphiti queue status shows pending/dead-letter/worker/health"
  - "Manual processing fallback: graphiti queue process for CLI use when MCP not running"
  - "Dead letter recovery: graphiti queue retry <id> or retry all"
  - "Color-coded health indicators: [green]ok[/green], [yellow]warning[/yellow], [red]error[/red]"

# Metrics
duration: 141s
completed: 2026-02-12T23:14:22Z
---

# Phase 5 Plan 3: CLI Commands Summary

**Queue management CLI with status inspection, manual processing fallback, and dead letter recovery**

## Performance

- **Duration:** 2.4 min (141s)
- **Started:** 2026-02-12T23:12:01Z
- **Completed:** 2026-02-12T23:14:22Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Queue command group registered as Typer sub-app via app.add_typer()
- status subcommand displays Rich table with health indicator (ok/warning/error)
- Health thresholds at 80%/100% match established graphiti health pattern
- JSON format support for programmatic monitoring
- process subcommand provides CLI fallback for manual queue processing
- retry subcommand enables dead letter recovery (specific job or 'all')
- Color-coded output with icons: ✓ (ok), ⚠ (warning), ✗ (error)
- All 10 commands accessible: add, search, list, show, delete, summarize, compact, config, health, queue
- Existing commands unaffected by queue integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create queue CLI command group** - `e212410` (feat)
   - queue_app Typer sub-app with status, process, retry subcommands
   - status: displays Rich table with pending/capacity/dead_letter/worker status
   - Health indicator with ok/warning/error levels at 80%/100% thresholds
   - JSON format support via --format json flag
   - process: manual CLI fallback blocks until queue empty
   - retry: dead letter recovery for specific job ID or 'all' jobs
   - Follows health.py output patterns (Rich tables, color coding)

2. **Task 2: Register queue command group** - `5366ee1` (feat)
   - Import queue_app from queue_cmd module
   - Register via app.add_typer(queue_app, name="queue")
   - Update command count comment: 10 commands registered
   - Full command tree verified: graphiti queue status/process/retry
   - All existing commands remain functional

## Files Created/Modified

- `src/cli/commands/queue_cmd.py` (created) - Queue command group: status (health monitoring), process (manual fallback), retry (dead letter recovery); Rich table output, JSON format, color-coded health indicators
- `src/cli/__init__.py` (modified) - Import queue_app, register via add_typer(), update command count to 10

## Decisions Made

- **Health thresholds at 80%/100%:** Matches established `graphiti health` pattern from Phase 4. Provides advance warning before capacity reached.
- **JSON format support:** Enables programmatic monitoring via `--format json` for scripting and automation use cases.
- **Blocking process command:** Synchronous CLI fallback blocks until queue empty. Simple pattern for manual processing when MCP not running.
- **Retry 'all' support:** Enables bulk dead letter recovery via `graphiti queue retry all` for operational convenience.
- **Rich table output:** Follows established health.py patterns for consistent UX across diagnostic commands.

## Deviations from Plan

None - plan executed exactly as written. No auto-fixes needed, no blocking issues encountered.

## Issues Encountered

None - implementation was straightforward. Queue public API from 05-02 integrated cleanly with CLI patterns from Phase 4.

## User Setup Required

None - queue commands available immediately via `graphiti queue` after installation. No external configuration required.

## Next Phase Readiness

**Ready for Phase 06 (Git Hooks):**
- Queue status inspection available for debugging hook-queued jobs
- Manual processing fallback ready for development/testing without MCP
- Dead letter recovery enables fixing failed hook captures

**Ready for Phase 08 (MCP Server):**
- Queue status API ready for MCP server health endpoints
- JSON format enables programmatic monitoring
- Manual process command provides fallback when MCP unavailable

**Verification complete:**
- `graphiti queue status` displays Rich table with health indicator
- `graphiti queue status --format json` outputs valid JSON
- `graphiti queue process` attempts to process pending jobs
- `graphiti queue retry <id>` shows "not found" error for nonexistent jobs
- All existing CLI commands still functional (health, config, add, etc.)
- Command registered in main app without breaking existing functionality

---
*Phase: 05-background-queue*
*Completed: 2026-02-12T23:14:22Z*

## Self-Check: PASSED

All created files verified:
- ✓ src/cli/commands/queue_cmd.py exists
- ✓ src/cli/__init__.py modified

All commits verified:
- ✓ e212410 (Task 1: Queue CLI command group)
- ✓ 5366ee1 (Task 2: Queue command registration)
