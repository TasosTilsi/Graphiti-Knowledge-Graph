# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-02)

**Core value:** Context continuity without repetition - Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while project teams can share knowledge safely through git.
**Current focus:** Phase 2 - Security Filtering

## Current Position

Phase: 2 of 9 (Security Filtering)
Plan: 5 of 5 complete
Status: Phase complete ✓
Last activity: 2026-02-04 — Completed 02-05-PLAN.md (comprehensive security filtering tests)

Progress: [████████░░] 100% Phase 2 complete

## Performance Metrics

**Velocity:**
- Total plans completed: 8
- Average duration: 16 min
- Total execution time: 2h 3min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-storage-foundation | 3 | 75 min | 25 min |
| 02-security-filtering | 5 | 37 min | 7.4 min |

**Recent Trend:**
- Last 3 plans: 02-03 (15 min), 02-04 (3 min), 02-05 (15 min)
- Trend: Steady execution (15 → 3 → 15 min)

*Updated after each plan completion*

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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-04 (phase execution)
Stopped at: Completed Phase 2 (02-05-PLAN.md - comprehensive security filtering tests)
Resume file: None

**Phase 2 Complete:** Security filtering system fully operational with 46 passing tests. Ready for Phase 3 (CLI Foundation).
