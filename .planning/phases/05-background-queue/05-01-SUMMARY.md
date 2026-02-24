---
phase: 05-background-queue
plan: 01
subsystem: queue
tags: [persistqueue, sqlite, background-jobs, async, dead-letter-queue]

# Dependency graph
requires:
  - phase: 03-llm-integration
    provides: LLMRequestQueue pattern for SQLite-backed queuing with ack/nack
provides:
  - Queue data models (QueuedJob, JobStatus, DeadLetterJob, QueueStats)
  - SQLite-backed JobQueue with FIFO ordering and parallel/sequential batching
  - Dead letter table for failed job tracking and manual retry
  - Hook context detection for silent vs verbose operation modes
affects: [05-02-worker-thread, 05-03-cli-commands, 06-git-hooks, 07-conversation-capture]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - SQLite persistence with separate main queue and dead letter tables
    - FIFO batching with parallel job grouping and sequential barriers
    - Soft capacity limits with warning logs (never reject jobs)
    - Hook context detection via environment variables and TTY status

key-files:
  created:
    - src/queue/__init__.py
    - src/queue/models.py
    - src/queue/storage.py
    - src/queue/detector.py
  modified: []

key-decisions:
  - "Use JobStatus enum for type-safe status tracking (PENDING, PROCESSING, FAILED, DEAD)"
  - "QueuedJob dataclass uses non-frozen to allow status/attempts mutation during processing"
  - "Dead letter table uses separate SQLite connection with WAL mode for thread safety"
  - "Soft capacity limit always accepts jobs but logs warnings at 80% and 100%+ capacity"
  - "is_hook_context() checks CLAUDE_* env vars, TTY status, and CI/CD markers"
  - "Support str or Path for db_path to match existing LLMRequestQueue pattern"

patterns-established:
  - "FIFO batching: get_batch() collects consecutive parallel jobs, stops at sequential barrier"
  - "Dead letter workflow: move_to_dead_letter() → get_dead_letter_jobs() → retry_dead_letter()"
  - "Separate SQLite connections: main queue uses persistqueue, dead letter uses direct sqlite3"
  - "Connection-per-call pattern for dead letter operations ensures thread safety"

# Metrics
duration: 214s
completed: 2026-02-13

requirements-completed: [R4.3]
---

# Phase 5 Plan 1: Queue Foundation Summary

**SQLite-backed persistent job queue with FIFO parallel batching, dead letter table for failed jobs, and hook context detection for silent operation**

## Performance

- **Duration:** 3.6 min (214s)
- **Started:** 2026-02-12T22:59:54Z
- **Completed:** 2026-02-13T01:03:28Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Queue data models with JobStatus enum, QueuedJob/DeadLetterJob dataclasses, auto-computed QueueStats
- SQLite-backed JobQueue with parallel job batching and sequential job barriers (FIFO ordering preserved)
- Dead letter table with separate connection, WAL mode, and manual retry capability
- Hook context detector for silent mode in Claude Code hooks and CI/CD environments
- Soft capacity limit: always accepts jobs, logs warnings at 80%/100% thresholds

## Task Commits

Each task was committed atomically:

1. **Task 1: Create queue data models and context detector** - `520d3db` (feat)
   - JobStatus enum with PENDING, PROCESSING, FAILED, DEAD values
   - QueuedJob dataclass with UUID, job_type, payload, parallel flag
   - DeadLetterJob dataclass for failed job tracking with failure metadata
   - QueueStats dataclass with auto-computed capacity_pct
   - is_hook_context() detector for Claude Code/CI/CD environments

2. **Task 2: Create SQLite-backed JobQueue with dead letter support** - `e8fc8c8` (feat)
   - JobQueue class with persistqueue.SQLiteAckQueue for main queue
   - FIFO batching logic: parallel jobs batch, sequential jobs barrier
   - Dead letter table with separate SQLite connection for failed jobs
   - Soft capacity limit with warnings at 80% and 100%
   - WAL mode enabled on dead letter DB for better concurrency

## Files Created/Modified

- `src/queue/__init__.py` - Package initialization with model exports (QueuedJob, JobStatus, QueueStats, DeadLetterJob, is_hook_context)
- `src/queue/models.py` - Data models: JobStatus enum, QueuedJob/DeadLetterJob/QueueStats dataclasses with field defaults and serialization support
- `src/queue/detector.py` - Hook context detection: checks CLAUDE_* env vars, TTY status, CI/CD markers for silent vs verbose mode
- `src/queue/storage.py` - JobQueue class: SQLite persistence, FIFO batching, dead letter table, ack/nack, retry logic

## Decisions Made

- **JobStatus enum:** Type-safe status tracking prevents string typos and enables pattern matching
- **Non-frozen dataclasses:** QueuedJob status and attempts must be mutable during processing; frozen would break worker updates
- **Separate dead letter connection:** Using sqlite3 directly (not persistqueue) for dead letter table allows custom schema and avoids queue semantics for archive data
- **WAL mode for dead letter:** Enables better read concurrency for dead letter queries without blocking writes
- **Soft capacity limit:** Never reject jobs (no data loss guarantee per requirements), but log warnings at thresholds for monitoring
- **str or Path support:** Matches existing LLMRequestQueue pattern, enables test flexibility with temporary directories

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added type handling for db_path parameter**
- **Found during:** Task 2 verification testing
- **Issue:** Test passed string path to JobQueue(), but __init__ only handled Path objects, causing AttributeError: 'str' object has no attribute 'mkdir'
- **Fix:** Added type checking in __init__ to convert str to Path, updated type annotation to Union[str, Path]
- **Files modified:** src/queue/storage.py
- **Verification:** Test passed with both string and Path inputs
- **Committed in:** e8fc8c8 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking issue)
**Impact on plan:** Essential fix for test compatibility and API flexibility. Matches existing LLMRequestQueue pattern which also accepts str paths. No scope creep.

## Issues Encountered

None - plan executed smoothly after type handling fix.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Plan 02 (Background Worker Thread):**
- Queue storage and models complete and fully tested
- FIFO batching logic verified with parallel/sequential job handling
- Dead letter table operational with retry capability
- Hook context detection ready for integration

**Ready for Plan 03 (CLI Commands):**
- get_stats() provides metrics for queue status command
- get_dead_letter_jobs() provides data for dead letter inspection
- retry_dead_letter() enables manual retry command

**Verification complete:**
- All success criteria met
- Package imports work correctly
- Parallel/sequential batching logic correct
- Dead letter operations functional
- Queue persistence verified across restarts
- Soft limit behavior confirmed

---
*Phase: 05-background-queue*
*Completed: 2026-02-13*

## Self-Check: PASSED

All created files verified:
- ✓ src/queue/__init__.py
- ✓ src/queue/models.py
- ✓ src/queue/detector.py
- ✓ src/queue/storage.py

All commits verified:
- ✓ 520d3db (Task 1: queue models and detector)
- ✓ e8fc8c8 (Task 2: SQLite JobQueue with dead letter)
