# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-02)

**Core value:** Context continuity without repetition - Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while project teams can share knowledge safely through git.
**Current focus:** Phase 5 In Progress — Background Queue Foundation

## Current Position

Phase: 5 of 9 (Background Queue)
Plan: 1 of 3 complete
Status: In Progress
Last activity: 2026-02-13 — Completed 05-01-PLAN.md (Queue Foundation - Data Models and Storage)
Next: 05-02-PLAN.md (Background Worker Thread)

Progress: [██████████████████████████████] 25 of 27 plans complete (92.6%)

## Performance Metrics

**Velocity:**
- Total plans completed: 25
- Average duration: 12.9 min
- Total execution time: 5h 25.6min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-storage-foundation | 3 | 75 min | 25 min |
| 02-security-filtering | 5 | 37 min | 7.4 min |
| 03-llm-integration | 5 | 83 min | 16.6 min |
| 04-cli-interface | 11 | 107 min | 9.7 min |
| 05-background-queue | 1 | 3.6 min | 3.6 min |

**Recent Trend:**
- Last 3 plans: 04-10 (1.8 min), 04-11 (1.9 min), 05-01 (3.6 min)
- Trend: Phase 05 started - Queue foundation with SQLite persistence and dead letter support

*Updated after each plan completion*

| Plan | Duration (s) | Tasks | Files |
|------|--------------|-------|-------|
| Phase 04 P01 | 161 | 2 tasks | 6 files |
| Phase 04 P02 | 355 | 2 tasks | 2 files |
| Phase 04 P03 | 180 | 2 tasks | 4 files |
| Phase 04 P04 | 141 | 2 tasks | 3 files |
| Phase 04 P05 | 227 | 2 tasks | 3 files |
| Phase 04 P06 | 420 | 2 tasks | 2 files |
| Phase 04 P07 | 219 | 2 tasks | 3 files |
| Phase 04 P08 | 4390 | 2 tasks | 3 files |
| Phase 04 P09 | 4353 | 2 tasks | 4 files |
| Phase 04 P10 | 106 | 2 tasks | 1 files |
| Phase 04 P11 | 112 | 2 tasks | 1 files |
| Phase 05 P01 | 214 | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- CLI-first architecture: CLI provides single source of truth, hooks and MCP wrap it
- Kuzu instead of in-memory: Better persistence, performance, and graph query capabilities
- Cloud Ollama with local fallback: Free tier for most operations, local models when quota exhausted
- Separate global + per-project graphs: Global preferences apply everywhere, project knowledge isolated
- Background async capture: Never blocks dev work, queues locally and processes in background
- Path configuration using Path.home(): Cross-platform compatibility for global database location
- GraphScope enum pattern: Type-safe routing between global and project scopes
- .git directory detection for project roots: Standard git convention, reliable across platforms
- Singleton pattern per scope: Prevents multiple Database objects to same Kuzu path
- asyncio.run() for async cleanup: Wraps KuzuDriver.close() for synchronous API
- Kuzu Connection API: Use kuzu.Connection(db) constructor, not db.connect() method
- Test isolation with monkeypatch: Prevents test pollution of user's real databases
- Aggressive entropy thresholds: BASE64=3.5, HEX=2.5 for maximum secret detection sensitivity
- Frozen dataclasses for security: Immutable security findings prevent accidental modification
- Computed properties pattern: was_modified computed from findings list rather than stored state
- Symlink resolution for security: Always Path.resolve() before pattern matching to prevent bypass attacks
- Fail-closed security posture: Unresolvable paths are excluded rather than allowed through
- Singleton audit logger: One SecurityAuditLogger per process to prevent multiple file handles
- Project-local audit logs: .graphiti/audit.log for per-project security tracking
- detect-secrets plugin config format: List of dicts with 'name' key and plugin-specific params
- Allowlist SHA256 hashes only: Never store plain text secrets, only hashes for secure lookup
- Required comments on allowlist: All allowlist entries require comment for audit trail
- transient_settings for thread-safety: Use detect-secrets transient_settings context manager
- Typed placeholders format: [REDACTED:type] format preserves detection type for debugging
- Storage never blocked: Sanitization always returns content, never raises exceptions for detected secrets
- Path.match() for glob patterns: Use Path.match() instead of string manipulation for proper ** glob semantics
- Project-scoped audit logger: Pass project_root to audit logger for correct log directory location
- Singleton reset in tests: Reset singleton instances in test setup for proper isolation
- Frozen dataclass for LLM config: Immutable configuration via dataclass(frozen=True)
- TOML configuration format: Python 3.11+ stdlib support, human-readable, type-safe parsing
- Environment variables override TOML: Security best practice for API keys, 12-factor app pattern
- Extensive configuration docs: WHY/WHEN/GOTCHA documentation for every configurable option
- Cloud-first failover pattern: Try cloud Ollama first, fall back to local on errors
- 429-only cooldown: Only rate-limit errors trigger cooldown; other errors retry cloud on next request
- Fixed delay retry: 10s fixed delay between retries (not exponential) for predictability
- Cooldown state persistence: Persist to JSON to survive restarts and prevent re-hitting rate limits
- Largest model selection: Select largest available model from fallback chain based on parameter count
- Header-based quota tracking: Parse x-ratelimit-* headers with local counting fallback
- SQLite-backed request queue: Persistent queue via persistqueue.SQLiteAckQueue with ack/nack pattern
- Bounded queue with pruning: Remove oldest items when max_size reached to prevent disk fill
- TTL-based expiry: Skip stale items older than configured TTL during processing
- Integrated quota tracking: OllamaClient tracks quota from headers or local count after cloud calls
- Queue-and-raise pattern: Failed requests queued with ID, exception includes tracking info
- Singleton LLM client: get_client() provides shared instance for quota/cooldown/queue state
- Convenience API: chat(), generate(), embed() functions at module level for clean imports
- [Phase 04]: DEFAULT_LIMIT = 15 for result pagination (user decision: 10-20 range)
- Mock data stubs for graph operations: Enables CLI testing before graph implementation with clear TODO markers for integration
- Rich Panel with Markdown for summaries: Professional formatted output respecting terminal capabilities
- confirm_action() for destructive ops: Single confirmation with --force bypass balances safety and UX
- list_cmd.py filename: Avoid shadowing Python's built-in list keyword
- Ambiguous name resolution pattern: Interactive numbered list prompts for user selection in show/delete commands
- Delete --force no short flag: Avoid conflict with --format (-f), makes destructive ops more explicit
- [Phase 04-02]: Auto-init .graphiti/ directory on first project-scope add operation for frictionless onboarding
- [Phase 04-02]: Stub functions return mock data for CLI flow testing before full graph integration
- [Phase 04-02]: Remove explicit Exit(SUCCESS) calls - Typer handles normal exit automatically
- [Phase 04-02]: Default search mode is semantic (--exact enables literal matching)
- [Phase 04-05]: Config uses dotted key paths (cloud.endpoint, retry.max_attempts) matching TOML structure for intuitive navigation
- [Phase 04-05]: Health checks use ok/warning/error status with 80%/95% quota thresholds for advance warning
- [Phase 04-05]: Sensitive values (api_key) masked as *** in display while remaining writable via --set for security
- [Phase 04-05]: Manual TOML writing for simple config structure avoids tomli_w dependency while remaining maintainable
- [Phase 04-06]: Separate test files for foundation vs commands improves maintainability and enables parallel test execution
- [Phase 04-06]: Mock all stub functions for fast, isolated CLI tests (<1s) that validate UX without requiring graph integration
- [Phase 04-06]: Human verification checkpoint ensures terminal UX meets professional standards beyond what automated tests can verify
- [Phase 04-06]: JSON extraction via bracket matching handles Rich pretty-printing while testing actual user-facing output
- [Phase 04-08]: LLMUnavailableError handling in CLI provides user-friendly messages directing to 'graphiti health' for diagnostics
- [Phase 04-08]: project_root parameter threading ensures correct scope resolution from CLI commands through to GraphService
- [Phase 04-08]: Date/type/tag filters in search documented as future enhancements while maintaining CLI UX
- [Phase 04-09]: Direct delegation pattern for CLI stub replacement preserves existing CLI interface while connecting to real graph operations
- [Phase 04-10]: Use EntityNode.get_by_group_ids() instead of raw Cypher for list_entities() - leverages graphiti_core's built-in API
- [Phase 04-10]: Case-insensitive CONTAINS matching for get_entity() enables flexible entity lookup ("python" matches "Python SDK")
- [Phase 04-10]: Node.delete_by_uuids() handles Kuzu-specific deletion including RelatesToNode_ cleanup automatically
- [Phase 04-10]: Best-effort stats pattern: get_stats() returns zeros on failure rather than raising exceptions for robustness
- [Phase 04-11]: summarize() limits to 200 entities with 100-entity prompt cap to avoid overwhelming LLM context
- [Phase 04-11]: LLM fallback pattern: summarize() returns entity listing on LLMUnavailableError rather than failing
- [Phase 04-11]: compact() uses exact case-insensitive name matching for deduplication (fuzzy/semantic dedup deferred to Phase 9)
- [Phase 04-11]: Deduplication keeps entity with longest summary (assumes most informative), deletes rest via Node.delete_by_uuids()
- [Phase 04-11]: Extracted _get_db_size() helper to avoid code duplication between compact() and get_stats()
- [Phase 05-01]: JobStatus enum for type-safe status tracking (PENDING, PROCESSING, FAILED, DEAD)
- [Phase 05-01]: QueuedJob dataclass non-frozen to allow status/attempts mutation during processing
- [Phase 05-01]: Dead letter table uses separate SQLite connection with WAL mode for thread safety
- [Phase 05-01]: Soft capacity limit always accepts jobs but logs warnings at 80% and 100%+ capacity
- [Phase 05-01]: is_hook_context() checks CLAUDE_* env vars, TTY status, and CI/CD markers for silent mode
- [Phase 05-01]: FIFO batching: get_batch() collects consecutive parallel jobs, stops at sequential barrier
- [Phase 05-01]: Connection-per-call pattern for dead letter operations ensures thread safety

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-13 (phase execution)
Stopped at: Completed 05-01-PLAN.md (Queue Foundation - Data Models and Storage)
Resume file: None

**Phase 5 IN PROGRESS:** Plan 1 of 3 complete in Phase 05-background-queue. Queue foundation established with SQLite-backed JobQueue, FIFO parallel batching logic, dead letter table, and hook context detection. Ready for Plan 02 (Background Worker Thread) and Plan 03 (CLI Commands).
