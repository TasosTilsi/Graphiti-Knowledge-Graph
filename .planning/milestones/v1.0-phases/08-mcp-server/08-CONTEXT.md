# Phase 8: MCP Server - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver both SKILL.md (immediate) and MCP Server (full integration) in a single phase. SKILL.md teaches Claude Code how to use the graphiti CLI autonomously. MCP Server wraps all CLI operations as callable tools, exposes a context resource for session-start injection, and supports stdio (default) and HTTP transports.

Creating posts interactions, advanced retention, and context refresh are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Phase deliverables
- Phase 8 ships two things: SKILL.md first, then MCP Server alongside it
- Not splitting into separate phases — both land in Phase 8

### Tool interface
- All CLI commands exposed as MCP tools (full parity with CLI): add, search, list, show, delete, summarize, compact, capture, health, config
- Tool naming: `graphiti_` prefix (e.g., `graphiti_add`, `graphiti_search`) — avoids collision with other MCP servers
- Implementation: MCP tools call the graphiti CLI via subprocess — preserves CLI-first architecture, single source of truth

### Response format (TOON)
- All MCP tool responses are encoded in TOON (Token-Oriented Object Notation) — not plain text, not JSON
- TOON gives ~40% token reduction vs JSON for uniform arrays of objects (entity lists, search results, etc.)
- SKILL.md instructs Claude to present TOON responses as human-readable prose to the user — no TOON ever shown to the end user
- No extra transformation cost: Claude reads TOON naturally and incorporates into its response; the SKILL.md instruction is a one-time system prompt cost (~10-15 tokens), not per-call
- Context injection (`graphiti://context` resource) also encoded as TOON

### SKILL.md behaviors (automatic)
- Inject context at session start (pull relevant knowledge when a session begins)
- Capture after key moments (run `graphiti add` after decisions, architecture discussions, bug resolutions)
- Surface knowledge on relevant topics (when user mentions a file/topic, proactively check if graphiti has context)
- Respond when explicitly asked
- SKILL.md instructs Claude to: use `--limit` flags for self-managed token budget, and always present tool results as natural human-readable prose (never expose TOON or raw CLI output to user)

### Context injection
- Signals at session start: current working directory / git project, recent git commits, recently modified files
- Content priority: decisions + architecture first (most durable, valuable context)
- Injection point: system prompt / MCP resource (`graphiti://context`) — invisible to user, appears before conversation
- Empty graph behavior: silent — inject nothing, no prompt to capture
- **Source of truth**: local Kuzu DB built by Phase 7.1 on-demand indexer — NOT journal replay. If index is stale (new commits since last index), trigger re-index before injecting.

### Token budget
- Default: 8K tokens (8192)
- User-configurable via: `mcp.context_tokens` config key (consistent with existing dotted key path convention)
- Trimming strategy: oldest entries first — most recent knowledge preserved
- SKILL.md: instructs Claude to self-limit results using `--limit` flags

### Transport & config
- Default transport: stdio (Claude Code spawns and manages the process)
- Also supported: HTTP / SSE (for running server independently or multi-client)
- Project context: auto-detect from current working directory at server startup (same behavior as CLI)
- Configuration method: `graphiti mcp install` command writes correct JSON to `~/.claude/claude.json` automatically, plus documentation explaining what it does
- MCP resources: expose `graphiti://context` resource for session-start injection (in addition to tools)

### Claude's Discretion
- Exact subprocess invocation details for MCP → CLI calls
- HTTP transport implementation details (port, endpoint structure)
- Internal token counting method for budget enforcement
- SKILL.md exact wording and formatting
- TOON library choice (use existing toon-format library or implement minimal encoder)

</decisions>

<specifics>
## Specific Ideas

- The `graphiti mcp install` command should write to `~/.claude/claude.json` — zero manual config for users
- SKILL.md should cover all four behaviors: session start, post-decision capture, topic surfacing, and explicit requests
- TOON format reference: https://github.com/toon-format/toon — designed specifically for LLM consumption
- End users must always see human-readable prose — TOON is a Claude-internal wire format, never surfaced to users

</specifics>

<deferred>
## Deferred Ideas

### Phase 9 cleanup: TOON retrofit for existing LLM prompt boundaries
Apply TOON encoding to structured data passed to the LLM in earlier phases — same token savings, better extraction quality:

- **Phase 4** (`summarize` command) — entity list `{name, summary, type}` currently sent as plain text to LLM; encode as TOON
- **Phase 6** (capture pipeline) — commit batch `{hash, message, files, diff}` sent for relevance filtering and summarization; encode as TOON
- **Phase 7.1** (indexer two-pass extraction) — commit stats and diffs sent to LLM per commit; largest savings since indexer makes many LLM calls per run; encode as TOON

Note: Phases 3 (LLM client), 5 (queue), and 7 (superseded) don't directly benefit — they're plumbing layers without structured-data-to-LLM boundaries.

</deferred>

---

*Phase: 08-mcp-server*
*Context gathered: 2026-02-20*
