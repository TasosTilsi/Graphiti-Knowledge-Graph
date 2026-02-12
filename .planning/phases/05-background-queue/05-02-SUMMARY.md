---
phase: 05-background-queue
plan: 02
subsystem: queue
tags: [threading, background-worker, parallel-processing, retry-logic, cli-replay]

# Dependency graph
requires:
  - phase: 05-01
    provides: JobQueue with SQLite persistence and FIFO batching
provides:
  - BackgroundWorker thread with Event-based lifecycle control
  - Parallel batch processing via ThreadPoolExecutor (4 workers)
  - Exponential backoff retry (10s, 20s, 40s delays)
  - Public API: enqueue, get_status, start_worker, stop_worker
  - Singleton pattern for shared queue and worker state
affects: [05-03-cli-commands, 06-git-hooks, 07-conversation-capture, 08-mcp-server]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Event-based worker lifecycle with non-daemon threads for graceful shutdown
    - ThreadPoolExecutor for concurrent parallel job execution
    - CLI-first architecture: worker replays CLI commands via subprocess
    - Singleton pattern for queue and worker (matches Phase 3 LLM client)
    - Context-aware feedback: silent for hooks, verbose for interactive CLI

key-files:
  created:
    - src/queue/worker.py
  modified:
    - src/queue/__init__.py

key-decisions:
  - "ThreadPoolExecutor with 4 max_workers optimal for I/O-bound CLI replay"
  - "Non-daemon threads prevent job loss on process exit"
  - "Event.wait(timeout) for responsive shutdown without busy-waiting"
  - "Conditional worker startup: threshold=1 (start on any pending job)"
  - "Health levels at 80%/100% thresholds match established health check pattern"
  - "_kwargs_to_flags helper converts dict to CLI flags (Boolean True=flag only, False=skip)"

patterns-established:
  - "Singleton management: get_queue() and get_worker() with lazy initialization"
  - "Context-aware feedback: silent param=None auto-detects hook context"
  - "Health status calculation: ok < 80% < warning < 100% < error"
  - "Manual processing fallback: process_queue() for CLI when MCP isn't running"

# Metrics
duration: 167s
completed: 2026-02-13
---

# Phase 5 Plan 2: Background Worker Thread Summary

**Background worker thread with parallel batch processing, exponential backoff retry, and public API for CLI and MCP integration**

## Performance

- **Duration:** 2.8 min (167s)
- **Started:** 2026-02-12T23:06:38Z
- **Completed:** 2026-02-13T01:09:25Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- BackgroundWorker class runs as background thread with Event-based lifecycle (start/stop/is_running)
- Parallel batch processing via ThreadPoolExecutor (4 workers for I/O-bound CLI commands)
- Sequential job barriers: non-parallel jobs processed alone, block parallel batches
- Exponential backoff retry: 10s, 20s, 40s delays between attempts (3 max retries)
- Dead letter handling: exhausted jobs moved to dead_letter_jobs table
- CLI-first architecture: worker replays CLI commands via subprocess
- Public API with singleton pattern: enqueue, get_status, process_queue, start/stop_worker
- Context-aware feedback: auto-detects hooks (silent) vs interactive CLI (verbose)
- Health level calculation: ok/warning/error at 80%/100% capacity thresholds

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement BackgroundWorker with parallel batching and retry** - `caba8ca` (feat)
   - BackgroundWorker class with threading.Event lifecycle control
   - ThreadPoolExecutor for parallel batch processing (max 4 workers)
   - Sequential jobs act as barriers (processed alone)
   - Exponential backoff retry: 10s, 20s, 40s between attempts
   - Dead letter handling after 3 failed attempts
   - CLI-first architecture: worker replays commands via subprocess
   - Graceful shutdown: completes current job before stopping

2. **Task 2: Create public queue API with singleton management** - `bcac1ae` (feat)
   - Module-level singletons: _queue and _worker for shared state
   - get_queue() and get_worker() lazy singleton pattern (matches Phase 3)
   - enqueue() with context-aware feedback (silent for hooks, verbose for CLI)
   - get_status() returns health level (ok/warning/error at 80%/100% thresholds)
   - process_queue() for CLI fallback manual processing
   - start_worker() conditional startup on backlog detection (threshold=1)
   - stop_worker() for graceful shutdown
   - reset() for test isolation

## Files Created/Modified

- `src/queue/worker.py` (created) - BackgroundWorker class: threading.Event lifecycle, ThreadPoolExecutor parallel batching, exponential backoff retry, CLI command replay via subprocess
- `src/queue/__init__.py` (modified) - Public API: enqueue, get_status, process_queue, start_worker, stop_worker, get_queue, get_worker, reset; singleton management; context-aware feedback

## Decisions Made

- **ThreadPoolExecutor with 4 workers:** Research shows 4 workers optimal for I/O-bound CLI replay. Not CPU-bound, so don't need cpu_count() workers. Configurable via max_workers parameter.
- **Non-daemon threads:** Prevents job loss on exit. Daemon threads killed abruptly, losing in-progress jobs. Non-daemon ensures graceful shutdown.
- **Event.wait(timeout) for sleep:** Responsive shutdown during backoff delays. Wake on stop signal or after timeout, not blocking sleep().
- **Conditional worker startup (threshold=1):** Start worker on any pending job. Worker overhead minimal, better to process proactively than accumulate backlog.
- **Health thresholds 80%/100%:** Matches established `graphiti health` pattern from Phase 4. Provides advance warning before hitting capacity.
- **CLI-first architecture:** Worker replays commands via subprocess. CLI remains single source of truth. Simplifies logic, maintains consistency.

## Deviations from Plan

None - plan executed exactly as written. No auto-fixes needed, no blocking issues encountered.

## Issues Encountered

None - implementation was straightforward with clear specifications from research phase.

## User Setup Required

None - no external service configuration required. Background worker integrated into existing queue infrastructure.

## Next Phase Readiness

**Ready for Plan 03 (CLI Commands):**
- Public API complete: enqueue(), get_status(), process_queue()
- Worker lifecycle management: start_worker(), stop_worker()
- Health monitoring ready for `graphiti queue status` command
- Manual processing ready for `graphiti process-queue` command
- Dead letter inspection ready for `graphiti queue dead-letter` command

**Ready for Phase 06 (Git Hooks):**
- Hook context detection integrated into enqueue()
- Silent mode automatic for Claude Code hooks
- Worker ready to process hook-queued jobs in background

**Ready for Phase 08 (MCP Server):**
- start_worker() ready to call on MCP boot
- Conditional startup prevents unnecessary worker when queue empty
- stop_worker() ready for graceful MCP shutdown

**Verification complete:**
- All success criteria met
- Worker starts, processes jobs, and stops cleanly
- Parallel batching works via ThreadPoolExecutor
- Exponential backoff verified with correct delays (10s, 20s, 40s)
- Public API functions work correctly
- Singleton pattern enables shared state
- Health level calculation correct at thresholds

---
*Phase: 05-background-queue*
*Completed: 2026-02-13*

## Self-Check: PASSED

All created files verified:
- ✓ src/queue/worker.py exists
- ✓ src/queue/__init__.py modified

All commits verified:
- ✓ caba8ca (Task 1: BackgroundWorker implementation)
- ✓ bcac1ae (Task 2: Public API and singletons)
