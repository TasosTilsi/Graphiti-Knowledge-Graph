# Phase 3: LLM Integration - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish hybrid cloud/local Ollama integration with graceful fallback and quota management. Cloud Ollama is primary, local Ollama is fallback. System tracks quota, handles errors with retries, and queues failed requests for later processing.

</domain>

<decisions>
## Implementation Decisions

### Failover Behavior
- Failover triggers on ANY error from cloud (not just quota/rate-limit)
- Rate-limit errors: 10-minute cooldown before trying cloud again
- Other errors: Try cloud again on very next request
- Failover logging: Configurable, default ON (logs every failover event)
- Local Ollama auto-start: Configurable, default OFF (fail with clear instructions)
- If local model not pulled: Fail with instructions ("Run: ollama pull <model>")

### Provider Configuration
- Default cloud provider: Ollama official cloud service
- Cloud endpoint: Configurable (user can point to custom/self-hosted)
- Local model: Configurable, default to largest-param model available
- Fallback chain supported: List of local models tried in order until one works
- Extensive documentation required for all configurable options

### Error Handling
- Retry count: Configurable, default 2 retries (3 total attempts)
- Request timeout: Configurable, default 90 seconds
- Retry delay: Fixed delay (not exponential), configurable, default 10 seconds
- Connection errors and response errors: Same handling (retry → failover)
- No circuit breaker: Always try cloud on each request (simpler, self-healing)
- Total failure behavior: Raise exception AND queue for later
- Exception includes queue info: "LLM unavailable. Request queued for retry. ID: X"

### Quota Management
- Quota tracking: Claude's discretion (parse headers if available, estimate otherwise)
- Warning threshold: Log warning at 80% quota usage (configurable threshold)
- No soft limit: Use cloud until actual limit hit
- Quota visibility: Separate `graphiti quota` command (not in health check)

### Claude's Discretion
- Exact quota tracking implementation (headers vs local counting)
- Default local model selection logic (largest available)
- Queue persistence and retry scheduling for failed requests
- Specific log message formats

</decisions>

<specifics>
## Specific Ideas

- "Build the default to be Ollama official but give option to configure"
- "For all configurable stuff, provide extensive documentation"
- Rate-limit response handling should trigger the 10-minute cooldown specifically
- Queue-and-raise pattern: caller knows request was queued, can track by ID

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-llm-integration*
*Context gathered: 2026-02-04*
