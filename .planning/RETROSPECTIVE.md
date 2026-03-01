# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v1.0 — MVP

**Shipped:** 2026-03-01
**Phases:** 18 (Phases 1–8.9, including 10 decimal gap-closure insertions) | **Plans:** 62 | **Timeline:** 27 days

### What Was Built

- Persistent Kuzu graph database with dual-scope isolation (global preferences + per-project knowledge)
- Defense-in-depth security: file exclusions, high-entropy detection, entity sanitization, pre-commit blocking hook
- Hybrid cloud/local Ollama LLM with quota tracking and graceful fallback — never completely fails
- Full CLI with 16+ commands; CLI-first architecture where MCP and hooks wrap CLI subprocesses
- Async background queue (SQLiteAckQueue + BackgroundWorker) for non-blocking git and conversation capture
- Automatic capture from git commits (post-commit hook) and Claude Code conversations (every 5-10 turns)
- Local-first git history indexer replacing journal-based approach — `.graphiti/` fully gitignored
- MCP server with 11 tools, context injection with stale-index detection, TOON encoding for large responses

### What Worked

- **CLI-first architecture**: Having the CLI as single source of truth made MCP and hook wiring straightforward. Subprocess-based MCP tools meant no code duplication between CLI and MCP layer.
- **GSD phase structure**: Planning-then-executing at plan granularity kept changes atomic and easy to reason about. Decimal phase insertions (7.1, 8.1–8.9) worked well for urgent gap closure without renumbering.
- **Audit-driven gap closure**: Running milestone audit before marking complete caught real integration bugs (graphiti_index missing, hooks.enabled CLI syntax, _is_claude_hook_installed depth). Worth the extra cycle.
- **Security filtering as a phase**: Building security in Phase 2 (before LLM and capture phases) meant it was always available as a gate. sanitize_content() runs before LLM in all capture paths.
- **Milestone audit + gap phases pattern**: The chain audit → plan-gap-phases → execute → re-audit is effective for catching integration issues invisible at phase level.

### What Was Inefficient

- **Phase 7 → 7.1 pivot**: Significant rework — journal writer, replay engine, checkpoint tracking, LFS helpers all built in Phase 7 and removed in 7.1. The local-first decision should have been made before Phase 7. Architectural pivots cost ~2 phases.
- **Phase 4 gap closure (04-07 through 04-11)**: CLI was built with mock stubs in original plans. Wiring to real graph operations required 5 extra plans (nearly doubled Phase 4). Implement real operations in original plans next time.
- **10 gap-closure decimal phases**: Phases 8.1–8.9 were necessary but indicate that verification was incomplete during main phases. Writing VERIFICATION.md during each phase (not as retroactive gap closure) would have prevented several of these.
- **State update lag**: ROADMAP.md progress table, REQUIREMENTS.md status notes, and STATE.md fell behind actual completion multiple times. Updating these in the plan execution itself (not as a separate step) avoids the drift.

### Patterns Established

- **Decimal phase insertion**: `X.Y` phases for urgent insertions between planned phases. Clearly marked `[INSERTED]` in roadmap. Maintains numeric ordering without renumbering downstream phases.
- **CLI subprocess for MCP tools**: All MCP tools call `graphiti <command>` as subprocess using `_GRAPHITI_CLI = Path(sys.executable).parent / 'graphiti'`. Never rely on PATH inheritance.
- **TOON encoding threshold**: Apply TOON for 3+ item lists, plain JSON for scalars. 3-item threshold where TOON header overhead pays off.
- **Security gate before LLM**: `sanitize_content()` always runs before LLM in capture paths. Belt-and-suspenders with pre-commit hook.
- **SQLiteAckQueue with multithreading=True**: Required when background worker runs `ollama_chat` in `run_in_executor` threads.
- **GRAPHITI_HOOK_START/END markers**: Idempotent hook section management — detect, update, or remove without touching other tools' content.
- **sys.executable path resolution**: Avoids PATH issues in Claude Code subprocess contexts consistently.
- **`lstrip('.')` not `strip('.')`**: For normalizing dot-prefixed field names from LLM — only strip leading dots, never trailing.

### Key Lessons

1. **Define architecture before building**: The Phase 7 → 7.1 pivot (journal → local-first) cost ~2 phases. Architecture decisions about storage model should be made before starting, not mid-milestone.
2. **Implement real operations in original plans**: Building CLI with mock stubs and wiring real operations later (Phase 4 gap closure) nearly doubled Phase 4 plan count. Integrate real operations from the start.
3. **Write VERIFICATION.md during execution**: Writing 3 VERIFICATION.md files retroactively in Phase 8.8 was overhead that could have been eliminated by including VERIFICATION.md creation in each phase's final plan.
4. **Audit before declaring done**: The milestone audit caught real bugs (graphiti_index missing, hooks.enabled syntax) that would have silently broken user flows. Always audit before marking complete.
5. **Keep docs in sync during execution**: ROADMAP.md progress table and REQUIREMENTS.md status notes drifted. Update state docs as part of plan execution, not separately.
6. **Security filtering is infrastructure, not feature**: Build it early (Phase 2 here) so all subsequent phases can use it as a dependency. Retrofitting security is harder.

### Cost Observations

- Model mix: ~80% sonnet, ~15% opus (planning/architecture), ~5% haiku (quick tasks)
- Sessions: ~15-20 sessions over 27 days
- Notable: Parallel wave execution within phases significantly reduced wall-clock time. GSD balanced model profile (sonnet default) worked well for this codebase scale.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 MVP | 18 | 62 | First milestone; established baseline patterns |

### Cumulative Quality

| Milestone | Tests | Gap-Closure Phases | Architecture Pivots |
|-----------|-------|--------------------|---------------------|
| v1.0 | 56+ | 10 (8.1–8.9, 7.1) | 1 (journal → local-first) |

### Top Lessons (Verified Across Milestones)

1. Architecture decisions before building avoids expensive mid-milestone pivots
2. Implement real integrations in original plans — mock stubs defer debt, not eliminate it
3. Write VERIFICATION.md during phase execution, not as retroactive gap closure
