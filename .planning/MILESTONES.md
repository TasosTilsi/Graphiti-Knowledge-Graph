# Milestones

## v1.0 MVP (Shipped: 2026-03-01)

**Phases completed:** 18 phases (Phases 1–8.9), 62 plans, 27 days (2026-02-02 → 2026-03-01)
**Codebase:** 44,453 lines Python | 247 commits

**Key accomplishments:**

1. Persistent Kuzu dual-scope knowledge graph: global preferences at `~/.graphiti/global/` and per-project isolation at `.graphiti/` — survives restarts, supports graph queries and temporal relationships
2. Defense-in-depth security filtering: file exclusions (.env*, *.key, *secret*), high-entropy string detection (AWS keys, GitHub tokens, JWTs), pre-commit validation hook, complete audit log
3. Hybrid cloud/local Ollama LLM: cloud-first with quota tracking and graceful fallback hierarchy — system never completely fails, always indicates active provider
4. CLI-first architecture with 16+ commands (`graphiti`/`gk`): add, search, list, show, delete, summarize, compact, config, health, hooks, index, queue, capture — with JSON output mode
5. Automatic knowledge capture: git post-commit hook + async SQLiteAckQueue + BackgroundWorker + conversation hooks for Claude Code — all non-blocking, under 100ms hook overhead
6. Local-first git history indexing: `graphiti index` builds Kuzu graph from commit logs/diffs on demand; `.graphiti/` fully gitignored — no merge conflicts, no secrets committed
7. MCP server with 11 tools for Claude Code: stdio transport, context injection on session start (stale-index detection, 8K token budget), TOON-encoded responses

**Git range:** d8c909c (project init) → a61485c (Phase 8.9 complete)

---

