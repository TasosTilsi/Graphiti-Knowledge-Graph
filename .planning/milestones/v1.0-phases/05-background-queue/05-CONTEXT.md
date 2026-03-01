# Phase 5: Background Queue - Context

**Gathered:** 2026-02-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement async processing queue to enable non-blocking Claude Code hooks and conversation capture. CLI commands can enqueue work that gets processed in the background by the MCP server. Queue persists across restarts via SQLite. This phase builds the processing infrastructure — actual capture logic (hooks, conversations) belongs in Phase 6.

</domain>

<decisions>
## Implementation Decisions

### Queue Architecture
- Primary worker runs as background thread inside MCP server process
- CLI fallback command (`graphiti process-queue` or similar) for manual processing when MCP isn't running
- Global FIFO with parallel batching: single queue ordered by timestamp
  - Sequential jobs act as barriers — process alone, wait until done
  - Consecutive parallel jobs batch together — run concurrently
  - Jobs carry a `parallel: bool` flag set by the caller at enqueue time
- Custom SQLite table (same DB pattern as Phase 3): id, created_at, parallel flag, job_type, payload, status, attempts
- Conditional eager startup: on MCP boot, check if backlog exists — start workers if yes, wait if no

### Job Submission API
- Dual submission mode: `--async` flag for explicit async + auto-detect hook context
  - Claude Code hooks: auto-detected, always queues (silent)
  - Interactive CLI: processes synchronously by default, `--async` to explicitly queue
- Minimal payload: store CLI command + arguments, worker replays the command
- Context-aware feedback: silent for auto-detected hooks, one-liner confirmation for explicit `--async`
- Queue inspection via `graphiti queue status` command for viewing pending/processing/failed jobs

### Failure Handling
- 3 retries before giving up
- Exponential backoff between retries (10s, 20s, 40s)
- Dead jobs move to dead letter table — preserved for inspection, can be manually retried
- Full isolation: each job fails independently, never blocks or affects other jobs

### Backpressure Handling
- Soft limit: always accept jobs, never lose knowledge, log warnings when queue exceeds threshold
- Queue size configurable (default 100), soft cap not hard rejection
- `graphiti queue status` shows warning at 80% capacity, error at 100%+ (same pattern as health check)
- No data loss guarantee: jobs always accepted regardless of queue size

### Claude's Discretion
- Thread pool size for parallel batch processing
- SQLite table schema details and indexing
- Auto-detection mechanism for hook context vs interactive CLI
- Dead letter table schema and manual retry UX
- Worker thread shutdown/cleanup on MCP server stop

</decisions>

<specifics>
## Specific Ideas

- Reuse the SQLite persistence pattern from Phase 3 (SQLiteAckQueue concept) but with custom schema for lane routing and timestamp ordering
- Queue worker replays CLI commands — CLI remains single source of truth (consistent with CLI-first architecture decision)
- `graphiti queue status` follows same UX pattern as `graphiti health` (ok/warning/error thresholds)
- MCP server is always running when Claude Code hooks fire, so in-process worker is guaranteed to be available for hook-generated jobs

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-background-queue*
*Context gathered: 2026-02-12*
