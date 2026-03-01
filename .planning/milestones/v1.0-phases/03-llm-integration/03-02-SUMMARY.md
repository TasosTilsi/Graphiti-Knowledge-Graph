---
phase: 03-llm-integration
plan: 02
status: complete
subsystem: llm-client
tags: [ollama, failover, retry, tenacity, cloud-local]

requires:
  - phases: [03-01]
    reason: LLMConfig and configuration foundation

provides:
  - OllamaClient with cloud-first/local-fallback pattern
  - Tenacity-based retry with fixed delay
  - Rate-limit cooldown (429 only, 10 minutes)
  - Non-429 errors: cloud tried on next request (no persistent cooldown)
  - Cooldown state persistence across restarts
  - LLMUnavailableError with CONTEXT.md-compliant message format

affects:
  - 03-03: Local model verification depends on client patterns
  - 03-04: Unified client will use OllamaClient as foundation
  - 03-05: Queue integration will populate request_id in LLMUnavailableError

tech-stack:
  added: []
  patterns:
    - cloud-first-failover: Try cloud first, fall back to local on error
    - tenacity-retry: Decorator-based retry with fixed delay
    - cooldown-persistence: State persisted to JSON for restart resilience
    - largest-model-selection: Regex-based parameter extraction for model selection

key-files:
  created:
    - src/llm/client.py: OllamaClient with failover and retry logic
  modified:
    - src/llm/__init__.py: Added OllamaClient and LLMUnavailableError exports

decisions:
  - id: llm-client-429-only-cooldown
    decision: Only rate-limit (429) errors trigger 10-minute cooldown
    rationale: Non-429 errors may be transient, trying cloud on next request enables self-healing
    alternative: All errors set cooldown (would prevent recovery from transient issues)
    affects: [03-04, 03-05]

  - id: llm-client-fixed-delay-retry
    decision: Fixed delay retry, not exponential backoff
    rationale: Per CONTEXT.md - simpler configuration, predictable behavior
    alternative: Exponential backoff (more complex config, harder to reason about)
    affects: All retry behavior

  - id: llm-client-cooldown-persistence
    decision: Persist cooldown state to llm_state.json
    rationale: Prevents immediately re-hitting rate limit after application restart
    alternative: Memory-only (would lose cooldown on restart)
    affects: Rate-limit handling reliability

  - id: llm-client-largest-model-selection
    decision: Select largest available model from fallback chain
    rationale: Better quality when multiple models available
    alternative: First available (would ignore model size)
    affects: Local fallback quality

metrics:
  duration: 2 minutes
  completed: 2026-02-05

requirements-completed: [R5.1, R5.2, R5.3]
---

# Phase 3 Plan 02: Cloud Client Implementation Summary

**One-liner:** Cloud-first OllamaClient with tenacity retry, 429-only cooldown, state persistence, and local fallback using largest available model.

## What Was Built

Implemented the core LLM client with cloud/local failover:

1. **OllamaClient class**: 466-line implementation with cloud-first pattern
2. **Cloud client setup**: httpx timeout configuration (5s connect, 90s read, 10s write)
3. **Local client setup**: Shorter timeouts (2s connect, 60s read)
4. **Retry logic**: tenacity decorator with fixed delay (3 attempts, 10s between)
5. **Rate-limit handling**: 429 → 10-minute cooldown persisted to disk
6. **Non-rate-limit errors**: No cooldown set, cloud tried on next request
7. **Local fallback**: Model verification, largest-model selection, clear error messages
8. **LLMUnavailableError**: Message format per CONTEXT.md with optional request_id
9. **Module exports**: Added OllamaClient and LLMUnavailableError to src.llm

## Architecture

**Request Flow:**

```
Request arrives
    ↓
Is cloud available? (has API key AND not in rate-limit cooldown)
    ↓ YES                                    ↓ NO
Try cloud with retry                   Try local with model fallback
    ↓                                        ↓
Success → return                       Success → return
    ↓                                        ↓
ResponseError                          All models failed
    ↓                                        ↓
Is 429?                                Raise LLMUnavailableError
    ↓ YES        ↓ NO
Set 10-min    Log error
cooldown      (no cooldown)
    ↓              ↓
Fall through to local
```

**Key Design Decisions:**

- **429-only cooldown**: Non-429 errors do NOT set persistent cooldown. Cloud is tried again on the very next request. This enables self-healing for transient issues.
- **Fixed delay**: 10s between retry attempts (not exponential), per CONTEXT.md decision
- **State persistence**: `cloud_cooldown_until` saved to `~/.graphiti/llm_state.json` to survive restarts
- **Largest model selection**: When local fallback chain has multiple models, select largest by parameter count (e.g., "9b" > "3b")
- **Granular timeouts**: Different timeout configs for cloud vs local (fast failure on connection, long read for generation)

## Implementation Highlights

**Rate-Limit Handling (CONTEXT.md compliance):**

```python
def _handle_cloud_error(self, error: ResponseError):
    if error.status_code == 429:
        # Rate limit: Set 10-minute cooldown
        self.cloud_cooldown_until = time.time() + self.config.rate_limit_cooldown_seconds
        self._save_cooldown_state()
    else:
        # CONTEXT.md decision: Non-rate-limit errors do NOT set cooldown.
        # Cloud will be tried again on the very next request.
        # Only 429 errors trigger the 10-minute cooldown period.
        logger.warning("Cloud error (non-rate-limit)", ...)
```

**Retry with Tenacity:**

```python
@retry(
    stop=stop_after_attempt(self.config.retry_max_attempts),
    wait=wait_fixed(self.config.retry_delay_seconds),
    retry=retry_if_exception_type((ConnectionError, ResponseError)),
    before_sleep=lambda retry_state: logger.info("Retrying cloud request", ...)
)
def _do_retry():
    # Call cloud client method
```

**Largest Model Selection:**

```python
def extract_params(model_name: str) -> int:
    """Extract parameter count from model name.

    Examples:
        "gemma2:9b" -> 9_000_000_000
        "llama3.2:3B" -> 3_000_000_000
    """
    match = re.search(r"(\d+)b", model_name.lower())
    return int(match.group(1)) * 1_000_000_000 if match else 0

return max(candidates, key=extract_params)
```

**LLMUnavailableError Message Format:**

```python
class LLMUnavailableError(Exception):
    def __init__(self, message: str | None = None, request_id: str | None = None):
        self.request_id = request_id
        if message is None:
            if request_id:
                message = f"LLM unavailable. Request queued for retry. ID: {request_id}"
            else:
                message = "LLM unavailable. Request will be queued for retry."
        super().__init__(message)
```

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Blockers:** None

**Concerns:** None

**Ready for:**
- **03-03 (Local Client Verification)**: Can test local model checking, largest-model selection
- **03-04 (Unified Client)**: OllamaClient provides failover foundation
- **03-05 (Async Queue)**: LLMUnavailableError ready for request_id population

**Deferred Implementation:**
- `local_auto_start` config field exists but auto-start not implemented (deferred per plan)
- TODO comment added: "local_auto_start implementation deferred. Config field exists for future use."
- Current behavior: fail with clear instructions ("Start with: ollama serve") regardless of setting

## Verification

All verification checks passed:

- ✓ OllamaClient initializes with LLMConfig
- ✓ _is_cloud_available() returns False when no API key configured
- ✓ _is_cloud_available() returns False when in cooldown period (via cooldown state loading)
- ✓ _is_cloud_available() returns True after non-429 cloud error (no cooldown set)
- ✓ Retry decorator configured with fixed delay (not exponential)
- ✓ Rate-limit (429) sets 10-minute cooldown
- ✓ Non-429 errors do NOT set any cooldown (explicit comment + no modification of cloud_cooldown_until)
- ✓ Cooldown state persists to llm_state.json (via _save_cooldown_state())
- ✓ Local fallback tries models in configured order (via _try_local())
- ✓ Missing model raises clear error with "ollama pull" instruction
- ✓ local_auto_start config acknowledged but implementation deferred with TODO
- ✓ LLMUnavailableError generates correct message format per CONTEXT.md
- ✓ LLMUnavailableError supports optional request_id parameter
- ✓ All classes exported from src.llm module

## Commits

| Task | Commit  | Message                                              |
| ---- | ------- | ---------------------------------------------------- |
| 1    | e42ce29 | feat(03-02): implement OllamaClient with cloud/local failover |
| 2    | 6841093 | feat(03-02): export OllamaClient and LLMUnavailableError |

## Knowledge for Future Sessions

**Cooldown behavior (CRITICAL):**

- Rate-limit (429) errors → 10-minute cooldown, persisted to disk
- All other errors (500, 502, connection issues) → NO cooldown
- This asymmetry is intentional per CONTEXT.md: enables self-healing for transient issues
- Code includes explicit comment documenting this decision for future maintainers

**Failover pattern established:**

- Always try cloud first if API key present and not in rate-limit cooldown
- Retry with fixed delay before failing over to local
- Log all failover events if config.failover_logging enabled
- Track current provider for observability

**Local model selection:**

- Filter to only pulled models
- Select largest by parameter count extracted from name
- Regex pattern: `(\d+)b` case-insensitive
- Falls back to 0 params if extraction fails (deprioritizes model)

**Error message standards:**

- Local Ollama not running: "Local Ollama not running. Start with: ollama serve"
- Model not pulled: "Model {model} not available. Run: ollama pull {model}"
- Total failure: "LLM unavailable. Request will be queued for retry." (+ ID after queue integration)

**State persistence pattern:**

- Use `get_state_path()` from config module → `~/.graphiti/llm_state.json`
- Handle missing/corrupt files gracefully (log warning, don't crash)
- Create parent directory if needed (mkdir parents=True, exist_ok=True)
- This pattern reusable for other state tracking needs
