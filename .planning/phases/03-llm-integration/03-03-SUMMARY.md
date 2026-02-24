---
phase: 03-llm-integration
plan: 03
subsystem: llm-resilience
tags: [quota-tracking, request-queue, retry, persistence, structlog]

requires:
  - phase: 03-01
    provides: LLMConfig with queue and quota settings

provides:
  - QuotaTracker for cloud usage monitoring (header parsing + local fallback)
  - LLMRequestQueue for failed request persistence with TTL and bounded size
  - Queue-and-raise pattern enabling request tracking by ID

affects:
  - 03-04: Unified client will use QuotaTracker and LLMRequestQueue
  - 03-05: Async queue processing will use LLMRequestQueue

tech-stack:
  added: []  # Dependencies already added in 03-01
  patterns:
    - header-based-quota: Parse rate-limit headers for usage tracking
    - local-counting-fallback: Count requests when headers unavailable
    - sqlite-backed-queue: Persistent queue via persistqueue.SQLiteAckQueue
    - bounded-queue-pruning: Remove oldest items when at max capacity
    - ttl-based-expiry: Skip stale items older than configured TTL
    - ack-nack-pattern: SQLiteAckQueue acknowledgment for retry control

key-files:
  created:
    - src/llm/quota.py: QuotaTracker and QuotaInfo
    - src/llm/queue.py: LLMRequestQueue and QueuedRequest
  modified:
    - src/llm/__init__.py: Added quota and queue exports

key-decisions:
  - id: quota-header-parsing
    decision: Parse standard rate-limit headers (x-ratelimit-*)
    rationale: Cloud services use standard headers, provides accurate quota info
    alternative: Local counting only (less accurate, no reset timestamps)
    affects: [03-04]

  - id: quota-local-fallback
    decision: Fall back to local request counting when headers unavailable
    rationale: Better to have rough quota tracking than none
    alternative: Require headers (would fail for services without them)
    affects: [03-04]

  - id: queue-sqlite-backend
    decision: Use SQLiteAckQueue for persistent queue
    rationale: Thread-safe, crash-resistant, zero external dependencies
    alternative: Redis Queue (requires Redis server), file-based (no thread safety)
    affects: [03-04, 03-05]

  - id: queue-bounded-pruning
    decision: Remove oldest items when queue reaches max_size
    rationale: Prevent unbounded disk growth per RESEARCH.md pitfall 8
    alternative: Reject new items (would lose recent failures), unbounded (disk fill risk)
    affects: [03-04, 03-05]

  - id: queue-ttl-skip
    decision: Skip items older than TTL during processing (don't error)
    rationale: Stale requests may no longer be relevant, silent skip reduces noise
    alternative: Error on stale items (would fill logs), process anyway (waste resources)
    affects: [03-05]

patterns-established:
  - "QuotaTracker pattern: update_from_headers() -> check_threshold() -> log warning"
  - "Queue pattern: enqueue() returns ID -> process_one() with ack/nack -> get_queue_stats()"
  - "Structlog usage: All quota/queue events logged in structured JSON format"

metrics:
  duration: 2 min
  completed: 2026-02-05

requirements-completed: [R5.3]
---

# Phase 3 Plan 03: Quota Tracking and Request Queue Summary

**One-liner:** SQLite-backed request queue with bounded size and TTL, plus header-based quota tracking with 80% warning threshold and local counting fallback.

## What Was Built

Implemented resilience layer for LLM operations:

1. **QuotaTracker**: Monitors cloud usage via response headers (x-ratelimit-*) or local counting fallback
   - Parses limit, remaining, reset timestamp from headers
   - Calculates usage percentage and logs warning at configurable threshold (default 80%)
   - Falls back to request counting when headers unavailable
   - QuotaInfo dataclass for type-safe status retrieval

2. **LLMRequestQueue**: Persistent queue for failed LLM requests using SQLite
   - Stores operation type, parameters, timestamp, error message, and unique ID
   - Bounded queue (default 1000 items) removes oldest when full
   - TTL support (default 24h) skips stale items during processing
   - process_one() with ack/nack for retry control, process_all() for batch processing
   - Thread-safe via SQLiteAckQueue, crash-resistant via auto-commit

3. **Module exports**: Added QuotaTracker, QuotaInfo, LLMRequestQueue, QueuedRequest to src.llm

## Architecture

**Quota Tracking Flow:**
```
Cloud Response Headers
    ↓
QuotaTracker.update_from_headers()
    ↓
Parse x-ratelimit-limit, x-ratelimit-remaining, x-ratelimit-reset
    ↓
Calculate usage_percent = 1 - (remaining / limit)
    ↓
check_threshold() → log warning if >= 80%
    ↓
Store in QuotaInfo (source="headers")

Fallback: increment_local_count() if headers unavailable
```

**Request Queue Flow:**
```
LLM Operation Fails (cloud + local both fail)
    ↓
enqueue(operation, params, error) → generate UUID
    ↓
Check queue.qsize() >= max_size?
    ├─ Yes: Remove oldest items to make room
    └─ No: Proceed
    ↓
SQLiteAckQueue.put(QueuedRequest)
    ↓
Return request_id for tracking
    ↓
Log: "Request queued for retry. ID: {request_id}"

Later Processing:
    ↓
process_one(processor_fn)
    ↓
Get oldest item, check timestamp
    ├─ Stale (age > TTL): ack() and skip
    └─ Fresh: Try processor_fn(operation, params)
        ├─ Success: ack() to remove
        └─ Failure: nack() to return to queue
```

## Key Features

**QuotaTracker:**
- Case-insensitive header matching (x-ratelimit-* and X-RateLimit-*)
- Configurable warning threshold (0.8 = 80% by default)
- get_status() returns last QuotaInfo or local count fallback
- reset() clears state when quota period resets
- Structured logging for all quota events

**LLMRequestQueue:**
- SQLite persistence to ~/.graphiti/llm_queue (configurable)
- Unique request IDs (UUID4) for tracking
- Bounded size prevents disk fill (removes oldest when full)
- TTL-based expiry skips stale items (default 24h)
- get_queue_stats() for monitoring: {pending, max_size, ttl_hours}
- clear_stale() removes all items older than TTL
- process_all() for batch retry (returns success/failure counts)

## Commits

| Task | Commit  | Message                                      |
| ---- | ------- | -------------------------------------------- |
| 1    | b253871 | feat(03-03): implement QuotaTracker for cloud usage monitoring |
| 2    | ecf13bf | feat(03-03): implement LLMRequestQueue for failed request persistence |
| 3    | 8de72fd | feat(03-03): export quota and queue modules from src.llm |

## Files Created/Modified

**Created:**
- `src/llm/quota.py` (179 lines): QuotaTracker class with header parsing and threshold checking
- `src/llm/queue.py` (269 lines): LLMRequestQueue with SQLite persistence and TTL support

**Modified:**
- `src/llm/__init__.py`: Added QuotaTracker, QuotaInfo, LLMRequestQueue, QueuedRequest to exports

## Decisions Made

1. **Header parsing strategy**: Parse standard x-ratelimit-* headers with case-insensitive matching
   - Rationale: Cloud services use standard headers, provides accurate quota tracking
   - Fallback: Local counting when headers unavailable (better than no tracking)

2. **Queue bounded pruning**: Remove oldest items when queue reaches max_size
   - Rationale: Prevents unbounded disk growth (RESEARCH.md pitfall 8)
   - Alternative: Reject new items (loses recent failures) or unbounded (disk fill risk)

3. **TTL silent skip**: Skip stale items during processing without error
   - Rationale: Stale requests may no longer be relevant, reduces log noise
   - Alternative: Error on stale (fills logs) or process anyway (wastes resources)

4. **SQLite backend**: Use persistqueue.SQLiteAckQueue for persistence
   - Rationale: Thread-safe, crash-resistant, zero external dependencies (no Redis needed)
   - Alternative: Redis Queue (requires server) or file-based (not thread-safe)

## Deviations from Plan

None - plan executed exactly as written.

## Verification

All verification checks passed:

- ✓ QuotaTracker parses standard rate-limit headers (x-ratelimit-limit, x-ratelimit-remaining)
- ✓ QuotaTracker logs warning when threshold exceeded (85% usage triggered 80% threshold)
- ✓ QuotaTracker falls back to local counting when headers unavailable
- ✓ LLMRequestQueue persists to SQLite file (~/.graphiti/llm_queue)
- ✓ Queue bounded by max_size configuration (1000 items default)
- ✓ Stale items (older than TTL) skipped during processing
- ✓ enqueue() returns unique request ID (UUID4)
- ✓ process_one() handles success/failure correctly (ack on success, nack on failure)
- ✓ All classes exported from src.llm module

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-05T06:58:20Z
- **Completed:** 2026-02-05T07:01:13Z
- **Tasks:** 3/3 completed
- **Files created:** 2
- **Files modified:** 1
- **Lines of code:** 448 (179 quota + 269 queue)

## Next Phase Readiness

**Blockers:** None

**Concerns:** None

**Ready for:**

- **03-04 (Unified Client)**: QuotaTracker and LLMRequestQueue available for integration
  - Client can call tracker.update_from_headers() after cloud responses
  - Client can call queue.enqueue() when both cloud and local fail
  - Exception can include request_id: "LLM unavailable. Request queued for retry. ID: {id}"

- **03-05 (Async Queue Processing)**: LLMRequestQueue ready for background processing
  - process_all() can be called in background thread/task
  - get_queue_stats() can report pending count to CLI
  - clear_stale() can be called periodically for cleanup

**Configuration available:**
- quota_warning_threshold: 0.8 (80% default)
- queue_max_size: 1000 items
- queue_item_ttl_hours: 24 hours

**Integration pattern established:**
```python
from src.llm import QuotaTracker, LLMRequestQueue, load_config

config = load_config()
tracker = QuotaTracker(config.quota_warning_threshold)
queue = LLMRequestQueue(config)

# After cloud response
info = tracker.update_from_headers(response.headers)

# When both cloud and local fail
request_id = queue.enqueue("chat", params, str(error))
raise LLMUnavailableError(f"LLM unavailable. Request queued for retry. ID: {request_id}")
```

---
*Phase: 03-llm-integration*
*Completed: 2026-02-05*
