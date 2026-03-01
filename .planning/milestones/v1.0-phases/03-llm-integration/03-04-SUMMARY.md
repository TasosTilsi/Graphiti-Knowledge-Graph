---
phase: 03-llm-integration
plan: 04
status: complete
subsystem: llm-unified-api
tags: [integration, public-api, quota-tracking, request-queue, singleton]

requires:
  - phases: [03-02, 03-03]
    reason: OllamaClient with failover, QuotaTracker and LLMRequestQueue modules

provides:
  - OllamaClient with full quota tracking and request queueing
  - High-level public API with get_client() singleton
  - Convenience functions: chat(), generate(), embed(), get_status()
  - Queue-and-raise pattern with request ID tracking
  - Complete LLM integration system ready for production use

affects:
  - 03-05: Async queue processing will use process_queue() method
  - CLI commands: Can use get_status() for quota/queue visibility
  - All downstream graph operations: Can use simple chat()/embed() API

tech-stack:
  added: []  # All dependencies already in place
  patterns:
    - singleton-client: Single shared OllamaClient instance per process
    - queue-and-raise: Failed requests queued, exception includes tracking ID
    - convenience-api: High-level functions wrapping client methods
    - integrated-monitoring: Quota and queue status accessible via get_status()

key-files:
  created: []
  modified:
    - src/llm/client.py: Integrated quota tracker and request queue
    - src/llm/__init__.py: Added singleton and convenience API

decisions:
  - id: llm-header-based-quota-tracking
    decision: Track quota from cloud response headers when available
    rationale: Most accurate quota info comes from provider headers
    alternative: Local counting only (less accurate, no reset info)
    affects: [quota-visibility, warning-accuracy]

  - id: llm-queue-all-failures
    decision: Queue all requests when both cloud and local fail
    rationale: Ensures no requests lost, enables retry after recovery
    alternative: Fail immediately without queue (loses requests)
    affects: [03-05, resilience]

  - id: llm-singleton-client
    decision: Singleton pattern for OllamaClient via get_client()
    rationale: Shares quota state, cooldown state, and queue across all callers
    alternative: New client per call (loses state, wastes resources)
    affects: [all-llm-consumers]

  - id: llm-convenience-api
    decision: Provide chat(), generate(), embed() at module level
    rationale: Simpler imports, cleaner code for common operations
    alternative: Always require get_client().method() (more verbose)
    affects: [developer-experience, code-clarity]

patterns-established:
  - "Integrated client pattern: OllamaClient orchestrates failover + quota + queue"
  - "Public API pattern: Module-level functions for common operations"
  - "Singleton pattern: reset_client() enables testing without global state issues"
  - "Status aggregation: get_status() provides unified view of provider, quota, queue"

metrics:
  duration: 31 min
  completed: 2026-02-05

requirements-completed: [R5.1, R5.2, R5.3]
---

# Phase 3 Plan 04: Unified Client Integration Summary

**One-liner:** OllamaClient now tracks quota from headers, queues failed requests with IDs, and exposes clean public API with get_client() singleton and chat()/generate()/embed() convenience functions.

## What Was Built

Completed integration of all LLM components into cohesive system:

1. **OllamaClient Integration**:
   - Added `_quota_tracker` initialization with warning threshold
   - Added `_request_queue` initialization with config settings
   - Updated `_retry_cloud()` to track quota after successful cloud calls
   - Modified chat(), generate(), embed() to queue failures when both cloud and local fail
   - Added `get_quota_status()`, `get_queue_stats()`, `process_queue()` accessor methods

2. **Quota Tracking**:
   - Check if response has headers attribute (ollama library may not expose)
   - Call `update_from_headers()` when headers available
   - Fall back to `increment_local_count()` when headers not exposed
   - Automatic warning logging at 80% threshold

3. **Request Queueing**:
   - Catch `LLMUnavailableError` in all operation methods
   - Queue operation, params, and error message
   - Raise new exception with request ID: "LLM unavailable. Request queued for retry. ID: {uuid}"
   - Enables caller tracking and async retry

4. **Public API**:
   - `get_client()`: Singleton pattern, lazy initialization
   - `reset_client()`: Testing support for singleton reset
   - `chat(messages, model=None, **kwargs)`: Direct chat API
   - `generate(prompt, model=None, **kwargs)`: Direct generation API
   - `embed(input, model=None)`: Direct embeddings API
   - `get_status()`: Returns provider, quota info, queue stats

5. **Module Documentation**:
   - Comprehensive docstring with quick start guide
   - Configuration instructions
   - Error handling explanation
   - Updated `__all__` exports

## Architecture

**Complete Request Flow:**

```
User calls chat() / generate() / embed()
    ↓
get_client() returns singleton OllamaClient
    ↓
Try cloud (if available and not in cooldown)
    ↓
Success → update_from_headers() or increment_local_count()
    ↓         ↓
    ✓         Error (429) → Set cooldown, fall through
              Error (other) → No cooldown, fall through
    ↓
Try local with model fallback
    ↓
    ✓ Success → Return result
    ↓
    ✗ Both failed → enqueue(operation, params, error)
    ↓
Raise LLMUnavailableError with request_id
```

**Status Aggregation:**

```
get_status() returns:
{
    "current_provider": "cloud" | "local" | "none",
    "quota": QuotaInfo(limit, remaining, usage_percent, source),
    "queue": {pending: N, max_size: 1000, ttl_hours: 24}
}
```

## Implementation Highlights

**Quota Tracking Integration:**

```python
result = _do_retry()
self._current_provider = "cloud"

# Track quota usage after successful cloud call
if hasattr(result, 'headers') and result.headers:
    self._quota_tracker.update_from_headers(result.headers)
else:
    # Fallback: increment local count
    self._quota_tracker.increment_local_count()

return result
```

**Queue-and-Raise Pattern:**

```python
try:
    # Try cloud and local...
    return self._try_local("chat", model, messages=messages, **kwargs)

except LLMUnavailableError as e:
    # Both cloud and local failed - queue the request
    params = {"model": model, "messages": messages, **kwargs}
    request_id = self._request_queue.enqueue("chat", params, str(e))

    # Raise with queue ID
    raise LLMUnavailableError(
        f"LLM unavailable. Request queued for retry. ID: {request_id}",
        request_id=request_id
    ) from e
```

**Singleton Pattern:**

```python
_client: OllamaClient | None = None
_config: LLMConfig | None = None

def get_client(config: LLMConfig | None = None) -> OllamaClient:
    global _client, _config
    if _client is None:
        _config = config or load_config()
        _client = OllamaClient(_config)
    return _client
```

**Convenience API:**

```python
def chat(messages: list[dict], model: str | None = None, **kwargs) -> dict:
    return get_client().chat(model=model, messages=messages, **kwargs)
```

## Verification

All verification checks passed:

- ✓ OllamaClient._quota_tracker exists and tracks usage
- ✓ OllamaClient._request_queue exists and queues failures
- ✓ Quota tracking attempts header parsing, falls back to local count
- ✓ LLMUnavailableError includes request_id when raised after queue
- ✓ get_client() returns singleton (same instance on repeated calls)
- ✓ reset_client() clears singleton (new instance after reset)
- ✓ chat(), generate(), embed() convenience functions work
- ✓ get_status() returns provider, quota, queue info
- ✓ All exports in __all__ list
- ✓ Module docstring provides quick start guide

## Commits

| Task | Commit  | Message                                                     |
| ---- | ------- | ----------------------------------------------------------- |
| 1    | e26c0fe | feat(03-04): integrate quota tracking and request queue    |
| 2    | f7d09d5 | feat(03-04): create high-level public API for LLM module   |

## Files Modified

**src/llm/client.py** (137 insertions, 38 deletions):
- Added QuotaTracker and LLMRequestQueue imports
- Initialize `_quota_tracker` and `_request_queue` in `__init__`
- Track quota in `_retry_cloud()` after successful cloud calls
- Wrap chat(), generate(), embed() with queue-on-failure logic
- Add `get_quota_status()`, `get_queue_stats()`, `process_queue()` methods

**src/llm/__init__.py** (126 insertions, 4 deletions):
- Add comprehensive module docstring with quick start
- Implement `get_client()` singleton pattern
- Implement `reset_client()` for testing
- Add convenience functions: chat(), generate(), embed(), get_status()
- Update `__all__` exports with all public API functions

## Decisions Made

1. **Header-based quota tracking**: Parse response headers for quota info when available, fall back to local counting
   - Rationale: Headers provide accurate limit/remaining/reset info
   - Fallback ensures tracking works even if headers not exposed by ollama library

2. **Queue all failures**: When both cloud and local fail, always queue request
   - Rationale: No requests lost, enables async retry after recovery
   - Alternative: Fail immediately (loses requests permanently)

3. **Singleton client**: Single OllamaClient instance shared across all callers
   - Rationale: Shares quota state, cooldown state, queue across entire process
   - Testing: reset_client() enables clean isolation between tests

4. **Convenience API**: Module-level functions for common operations
   - Rationale: Simpler imports (`from src.llm import chat`), cleaner calling code
   - Alternative: Always require `get_client().chat()` (more verbose, exposes internals)

## Deviations from Plan

None - plan executed exactly as written.

## Performance

- **Duration:** 31 minutes
- **Started:** 2026-02-05T17:04:25Z
- **Completed:** 2026-02-05T17:36:08Z
- **Tasks:** 2/2 completed
- **Files created:** 0
- **Files modified:** 2 (client.py, __init__.py)
- **Lines of code:** 263 added (137 + 126), 42 removed

## Next Phase Readiness

**Blockers:** None

**Concerns:** None

**Ready for:**

- **03-05 (Async Queue Processing)**: Can call `process_queue()` for batch retry
  - Returns (success_count, failure_count) tuple
  - Logs processing results via structlog
  - Suitable for background thread or CLI command

- **CLI Development**: Complete public API available
  - `graphiti quota`: Call `get_status()['quota']`
  - `graphiti queue`: Call `get_status()['queue']`
  - Simple imports: `from src.llm import chat, embed, get_status`

- **Graph Operations**: Can use LLM functions directly
  - `chat([{"role": "user", "content": "..."}])` for reasoning
  - `embed("text to embed")` for vector generation
  - Automatic failover, quota tracking, queueing handled transparently

**Integration pattern established:**

```python
from src.llm import chat, embed, get_status

# Use LLM for reasoning
response = chat([{"role": "user", "content": "Extract entities from: ..."}])

# Use LLM for embeddings
vectors = embed(["text 1", "text 2", "text 3"])

# Monitor system
status = get_status()
if status['quota']['usage_percent'] and status['quota']['usage_percent'] > 0.8:
    print("Warning: Approaching quota limit")
if status['queue']['pending'] > 0:
    print(f"Queue has {status['queue']['pending']} pending requests")
```

## Knowledge for Future Sessions

**Complete LLM system now available:**

- Cloud-first failover with local fallback
- Automatic retry with fixed delay
- Rate-limit cooldown (429 only, persisted)
- Quota tracking from headers or local counting
- Request queue for failed operations (SQLite-backed)
- Public API with singleton pattern
- Comprehensive error handling and logging

**Usage patterns:**

1. **Simple usage**: `from src.llm import chat, embed`
2. **Monitoring**: `from src.llm import get_status`
3. **Advanced**: `from src.llm import get_client` (access full OllamaClient API)
4. **Testing**: `from src.llm import reset_client` (clear singleton between tests)

**Error handling:**

- Normal errors: Automatic retry and failover
- Total failure: `LLMUnavailableError` with request_id, request queued
- Rate limit: 10-minute cooldown, automatic local fallback
- Caller receives clear error messages with tracking IDs

**State management:**

- Cooldown state: Persisted to `~/.graphiti/llm_state.json`
- Queue state: Persisted to `~/.graphiti/llm_queue/` (SQLite)
- Quota state: In-memory (ephemeral, resets on restart)

**Next steps:**

- Plan 03-05: Background queue processing (async retry of failed requests)
- Future: CLI commands leveraging get_status() and process_queue()

---

*Phase: 03-llm-integration*
*Completed: 2026-02-05*
