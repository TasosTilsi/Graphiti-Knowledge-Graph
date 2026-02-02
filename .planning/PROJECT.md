# Graphiti Knowledge Graph

## What This Is

A local knowledge graph system that automatically captures and provides development context through CLI, Claude Code hooks, and MCP server interfaces. It maintains your personal preferences globally and project-specific knowledge locally, eliminating the need to repeat context across sessions while keeping all data safe for git commits.

## Core Value

**Context continuity without repetition** - Claude remembers your preferences, decisions, and project architecture across all sessions without you stating them again, while project teams can share knowledge safely through git.

## Requirements

### Validated

<!-- Shipped capabilities from existing codebase -->

- ✓ MCP server with stdio and HTTP transports — existing
- ✓ Basic memory storage with embeddings (nomic-embed-text) — existing
- ✓ Simple add/search knowledge operations — existing
- ✓ Ollama integration (LLM + embeddings) — existing
- ✓ CLI tools for knowledge management — existing
- ✓ Graceful degradation when dependencies unavailable — existing
- ✓ Multiple MCP client support (Claude Desktop, generic) — existing

### Active

<!-- Current scope - building toward these -->

- [ ] **KG-01**: Separate global preferences graph (~/.graphiti/global/) and per-project graphs (.graphiti/)
- [ ] **KG-02**: Replace in-memory storage with Kuzu graph database for better performance and persistence
- [ ] **KG-03**: Cloud Ollama integration with free tier quota management
- [ ] **KG-04**: Local Ollama fallback (gemma2:9b, llama3.2:3b) when cloud quota exhausted
- [ ] **KG-05**: CLI-first architecture - all operations via CLI, hooks and MCP wrap CLI
- [ ] **KG-06**: Automatic conversation-based capture (every 5-10 turns, background async)
- [ ] **KG-07**: Git post-commit hook for commit-based knowledge capture
- [ ] **KG-08**: Background async processing with local queue (non-blocking)
- [ ] **KG-09**: Security filtering - exclude secrets, PII, sensitive files from capture
- [ ] **KG-10**: Git-safe knowledge graphs (project graphs committable, no secrets)
- [ ] **KG-11**: Smart knowledge retention (reinforced knowledge persists, unused expires after 90 days)
- [ ] **KG-12**: Claude Code hooks for automatic context injection on session start
- [ ] **KG-13**: Semantic search for relevant context (based on current file, recent commits)
- [ ] **KG-14**: Enhanced MCP tools (delete, summarize, compact operations)
- [ ] **KG-15**: Configurable capture modes (decisions-only vs decisions-and-patterns)
- [ ] **KG-16**: Entity-level sanitization (detect and filter API keys, tokens, credentials)
- [ ] **KG-17**: File-level exclusions (.env*, *secret*, *credential*, *.key, etc.)

### Out of Scope

- Real-time collaboration (async git-based sharing only) — adds complexity, not core value
- Web UI (CLI/MCP interfaces sufficient) — CLI-first, UI not needed for v1
- Multi-user authentication (personal tool, shared via git) — team shares through git, no auth layer needed
- Vector database alternatives (Kuzu + embeddings sufficient) — stack decided, no need to evaluate others
- GraphQL API (MCP protocol sufficient) — MCP is the standard, no need for additional API
- Distributed deployment (local-only) — personal tool, runs on dev machine

## Context

**Existing Codebase:**
- Basic MCP server implementation exists with in-memory storage
- Currently uses graphiti_core for knowledge graph operations
- Ollama integration working with local models (mistral:7b, llama3.2:3b, nomic-embed-text)
- Simple CLI tools for add/search operations
- Supports both stdio (Claude Desktop) and HTTP transports

**Target Use Case:**
- Developer working across multiple projects
- Wants Claude Code to remember preferences without re-stating
- Wants project context to persist across sessions
- Wants to share project knowledge with team via git
- Needs automatic capture without manual effort
- Must be efficient (no blocking, no slowing down dev work)

**Knowledge Types:**
- **Global preferences**: Testing frameworks, coding style, tool choices, personal conventions
- **Project knowledge**: Architecture decisions, technology choices, patterns, the "why" behind decisions
- **Never captured**: Secrets, credentials, PII, raw code with literals, configuration files with sensitive data

## Constraints

- **Tech Stack**: Graphiti + Kuzu (replacing in-memory storage) — chosen for knowledge graph capabilities
- **LLM Provider**: Cloud Ollama free tier primary, local Ollama fallback — cost efficiency
- **Local Models**: gemma2:9b (quality), llama3.2:3b (speed), nomic-embed-text (embeddings) — CPU-optimized, no GPU
- **Machine**: Intel i7-13620H (16 threads), 32GB RAM, integrated GPU only — must run efficiently on CPU
- **Performance**: Non-blocking capture, async processing — never slow down development workflow
- **Security**: Git-safe by default, strict filtering — project knowledge must be safe for GitHub
- **Storage**: Separate graphs per project — avoid interference, keep files manageable
- **Interface Priority**: CLI first, then hooks and MCP — CLI is foundation, others wrap it
- **Language**: Python 3.12+ — existing codebase language

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| CLI-first architecture | CLI provides single source of truth, hooks and MCP wrap it to avoid duplication | — Pending |
| Kuzu instead of in-memory | Better persistence, performance, and graph query capabilities than dict storage | — Pending |
| Cloud Ollama with local fallback | Free tier for most operations, local models when quota exhausted maintains availability | — Pending |
| Separate global + per-project graphs | Global preferences apply everywhere, project knowledge isolated and git-shareable | — Pending |
| Decisions-only mode by default | Safer for git commits, captures high-level knowledge without code/data leakage | — Pending |
| Smart retention (90 days unused) | Keeps knowledge fresh, reinforced facts persist longer, configurable per project | — Pending |
| Background async capture | Never blocks dev work, queues locally and processes in background | — Pending |
| Strict security filtering | File exclusions + entity sanitization ensures git-safe knowledge graphs | — Pending |
| gemma2:9b for primary LLM | Best quality/performance on CPU, better than mistral:7b for structured tasks | ✓ Good |
| llama3.2:3b for fast fallback | Quick operations when speed matters more than quality | ✓ Good |
| nomic-embed-text for embeddings | Excellent embedding model, already installed and working | ✓ Good |

---
*Last updated: 2026-02-02 after initialization*
