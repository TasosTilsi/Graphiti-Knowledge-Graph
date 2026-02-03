# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-02)

**Core value:** Context continuity without repetition - Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while project teams can share knowledge safely through git.
**Current focus:** Phase 2 - Security Filtering

## Current Position

Phase: 2 of 9 (Security Filtering)
Plan: 2 of 5 complete
Status: In progress
Last activity: 2026-02-03 — Completed 02-02-PLAN.md (file exclusion and audit logging)

Progress: [████░░░░░░] 50%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 16 min
- Total execution time: 1.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-storage-foundation | 3 | 75 min | 25 min |
| 02-security-filtering | 2 | 4 min | 2 min |

**Recent Trend:**
- Last 3 plans: 01-03 (18 min), 02-01 (2 min), 02-02 (2 min)
- Trend: Consistently fast (18 → 2 → 2 min)

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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-03 (phase execution)
Stopped at: Completed 02-02-PLAN.md (file exclusion and audit logging)
Resume file: None
