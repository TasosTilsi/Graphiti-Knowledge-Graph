# Project Research Summary

**Project:** Graphiti Knowledge Graph with CLI/Hooks/MCP Integration
**Domain:** Developer Tools - Knowledge Graph Systems
**Researched:** 2026-02-02
**Confidence:** HIGH

## Executive Summary

This is a multi-interface knowledge graph system designed for developers, with three key characteristics: CLI-first architecture, automatic context capture from git commits and conversations, and git-safe project knowledge graphs. Expert developers build such systems with a layered architecture where a core engine provides the single source of truth, wrapped by multiple interface layers (CLI, hooks, MCP server). The stack centers on Python 3.10+ with Kuzu embedded graph database, Graphiti Core for temporally-aware knowledge graphs, Ollama for local LLM processing, and Typer for the CLI interface.

The recommended approach prioritizes persistence migration (from in-memory to Kuzu) as the foundational change, followed by dual-scope storage (global vs per-project graphs) to enable git-safe sharing. Security filtering must be implemented before automatic capture features go live, using both file-level exclusions and entity-level sanitization to prevent secrets from entering knowledge graphs. Background async processing is critical for non-blocking git hooks—users must never wait for LLM processing during commits.

Key risks include: (1) secrets leaking into git-committed graphs if filtering is inadequate, (2) poor UX from blocking git operations, and (3) LLM quota exhaustion without graceful fallback. Mitigation strategies are clear: defense-in-depth filtering (file + entity level), async-first queue architecture with immediate returns, and hybrid cloud/local Ollama with automatic fallback. The architecture is well-understood, the stack is stable and documented, and the feature set balances automation (differentiator) with safety (requirement).

## Key Findings

### Recommended Stack

The stack research identified a cohesive set of mature, production-ready technologies with excellent compatibility. Python 3.10+ provides the baseline with modern async features and structural pattern matching. Kuzu 0.11.3 offers an embedded, serverless graph database with native vector search, full-text search, and Cypher query language—ideal for CPU-only environments. Graphiti Core 0.26.3 brings temporally-aware knowledge graphs with bi-temporal model and real-time incremental updates. The MCP SDK 1.26.0 (official Anthropic) provides stable protocol implementation for LLM integration. Ollama 0.6.1 client enables local and hybrid cloud/local LLM operations. Typer 0.21.1 delivers modern CLI development with type-hint-based design and auto-completion.

**Core technologies:**
- **Kuzu 0.11.3**: Embedded graph database — serverless architecture, excellent CPU performance, native vector search, no separate server process
- **Graphiti Core 0.26.3**: Knowledge graph framework — temporally-aware graphs, incremental updates, built for AI agents, Kuzu backend support
- **MCP SDK 1.26.0**: Protocol implementation — official Anthropic SDK, stable v1.x for production, stdio and HTTP transports
- **Ollama 0.6.1**: LLM client — async support, local and cloud hybrid capability, streaming responses, model management
- **Typer 0.21.1**: CLI framework — type-hint-based, auto-completion, Rich formatting included, excellent developer experience
- **aiojobs 1.4.0**: Async task scheduler — background processing without blocking, graceful shutdown support
- **pydantic-settings 2.12.0**: Configuration management — type-safe settings with validation, .env file support, twelve-factor compliant

**Critical constraint**: CPU-only hardware (Intel i7-13620H, 32GB RAM, no GPU) requires CPU-optimized models (mistral:7b-instruct, phi3:mini, nomic-embed-text) and rules out GPU-dependent libraries.

### Expected Features

Features divide into three clear categories: table stakes (core CRUD operations users expect), differentiators (automatic capture and git-safety that set the product apart), and anti-features (commonly requested but problematic features to avoid).

**Must have (table stakes):**
- Add/store knowledge with entity + relations model
- Search/retrieve with semantic capabilities
- List/browse with filtering by type/category
- Delete/forget for incorrect or stale knowledge
- Persistence that survives restarts (Kuzu migration is foundational)
- Configuration system for models, paths, rules
- Status/health check for diagnostics

**Should have (competitive differentiators):**
- Automatic capture from git commits and conversations (zero manual effort)
- Dual-scope storage (global preferences + per-project knowledge for git-safe team sharing)
- Git-safe by design (security filtering ensures no secrets leak)
- Claude Code hooks (seamless context injection on session start)
- Smart retention (90-day expiration with reinforcement learning to prevent stale data)
- Semantic context injection (auto-inject relevant knowledge based on current work)
- Background processing (never blocks dev work, async queue with local processing)
- Hybrid cloud/local LLM (cloud Ollama free tier with local fallback)
- Decisions-only capture mode (safer default avoiding code/data leakage)

**Defer (v2+):**
- Enhanced MCP tools beyond basic CRUD (wait for MCP protocol evolution)
- Multi-model support (GPT, Claude API, other providers—Ollama sufficient for v1)
- Team collaboration features (git-based sharing validates approach first)
- Advanced graph queries (simple search enough initially)
- Import/export (nice-to-have, not critical)
- Graph visualization UI (anti-feature until proven needed)

**Anti-features to avoid:**
- Real-time sync (distributed system complexity, use git-based async sharing instead)
- Web UI dashboard (maintenance burden, doesn't align with CLI-first philosophy)
- Full code storage (massive growth, git conflicts, leaks secrets—store decisions/patterns only)
- Unlimited history (unbounded growth, use smart retention with quality over quantity)
- Natural language CLI (unpredictable, use explicit commands for clarity and scriptability)

### Architecture Approach

Multi-interface knowledge graph systems follow a layered pattern with CLI-first architecture: a core engine provides the single source of truth, with multiple interface wrappers (CLI, hooks, MCP server, HTTP API) exposing functionality through different channels. The storage layer uses separate Kuzu embedded database instances for global (~/.graphiti/global/) and per-project (.graphiti/) graphs, providing isolation and git-safety. Security filtering operates at two levels: file-level exclusions (.env*, *secret*, *.key) and entity-level sanitization (pattern matching + entropy detection). Background async queue using aiojobs ensures non-blocking operations, critical for git hooks that must never delay commits. LLM processing uses cloud-first, local-fallback strategy with automatic quota tracking and graceful degradation.

**Major components:**
1. **CLI (Typer)** — Primary interface and single source of truth for operations, provides canonical human interface
2. **Core Engine** — Business logic for knowledge operations (add, search, delete, summarize), security filtering, graph selector (global vs project routing)
3. **Background Queue (aiojobs)** — Non-blocking async processing with job lifecycle management, enables instant hook returns
4. **LLM Processing (Ollama)** — Cloud Ollama primary with local fallback, entity extraction and knowledge graph generation
5. **Storage Layer (Kuzu)** — Embedded graph databases per scope (global + each project), ACID transactions, vector search support
6. **Git Hooks (pre-commit)** — Post-commit capture triggering CLI commands with --async flag
7. **MCP Server** — Model Context Protocol interface wrapping core operations (not CLI) for better error handling

**Key patterns:**
- CLI-first with interface wrappers (single implementation, consistent behavior)
- Graph selector for routing (global vs per-project based on context)
- Security filter pipeline (defense in depth, file + entity level)
- Embedded graph database per scope (complete isolation, git-committable)
- LLM client with graceful fallback (cost-efficient with reliability)

**Recommended build order:** Storage foundation (Kuzu adapter) → Core engine (operations, filtering, LLM) → CLI interface → Background queue → Git hooks → MCP server. This bottom-up approach ensures each layer has solid foundation before building dependent components.

### Critical Pitfalls

**Note:** PITFALLS.md was not found in the research files. The following pitfalls are synthesized from anti-patterns and risks mentioned in STACK.md, FEATURES.md, and ARCHITECTURE.md.

1. **Secrets leaking into git-committed graphs** — If security filtering is inadequate (file-level only, no entity sanitization), secrets will leak from test files, commits with pasted API keys, or hardcoded tokens. Prevention: Defense in depth with both file-level exclusions AND entity-level sanitization using pattern matching and entropy detection. Validate with pre-commit hook to catch secrets before commit.

2. **Blocking git operations with synchronous capture** — Git hooks that wait for LLM processing (2-10 seconds) create terrible UX. Users will disable hooks or abandon tool. Prevention: Always use --async flag in hooks, submit to background queue, return immediately. User never waits. Background worker processes asynchronously.

3. **LLM quota exhaustion without fallback** — Cloud Ollama free tier has limits. If quota exhausted with no fallback, capture stops working. Prevention: Hybrid cloud/local strategy with automatic fallback, quota tracking in Kuzu database, graceful degradation from cloud to local to error (never crash).

4. **In-memory storage causing data loss** — Current implementation uses in-memory storage. Data lost on restart. Prevention: Migrate to Kuzu persistent database as foundational change. This is highest priority dependency—many features require it.

5. **Coupling MCP transport to business logic** — Embedding stdio-specific assumptions throughout MCP server makes HTTP transport difficult to add later, violates separation of concerns. Prevention: Abstract transport layer, make core MCP server logic transport-agnostic, use transport adapters (stdio, HTTP).

## Implications for Roadmap

Based on research, suggested phase structure follows dependency chain from foundation (storage) to interfaces (hooks, MCP):

### Phase 1: Storage Foundation & Core Engine
**Rationale:** Kuzu migration is foundational—everything depends on persistent storage. Current in-memory implementation causes data loss. Core engine must exist before any interface can use it. Graph selector and security filtering are required before automatic capture can safely operate.

**Delivers:**
- Kuzu adapter with graph schema (entities, relations, embeddings)
- Separate embedded instances for global and per-project graphs
- Graph selector (routing to global vs project based on context)
- Security filter (file-level exclusions + entity-level sanitization)
- Core operations (add, search, delete, summarize)
- LLM client with cloud/local fallback

**Addresses:**
- Persistence (table stakes—must survive restarts)
- Dual-scope storage (differentiator—enables git-safe sharing)
- Git-safe by design (differentiator—prevents secrets in project graphs)

**Avoids:**
- In-memory storage data loss (critical pitfall #4)
- Secrets leaking into graphs (critical pitfall #1—filtering must be solid)

### Phase 2: CLI Interface & Configuration
**Rationale:** CLI is the primary interface and single source of truth. Hooks and MCP will wrap CLI operations. Must establish CLI commands before building wrappers. Configuration system needed for Ollama endpoints, quota limits, file exclusion patterns.

**Delivers:**
- Typer CLI application with subcommands (add, search, delete, list, summarize, status)
- Output formatting (JSON for machines, table/text for humans)
- Configuration management (global ~/.graphiti/config.toml, project .graphiti/config.toml)
- Health check and diagnostics (Ollama connection, storage status, quota usage)

**Uses:**
- Typer 0.21.1 for CLI framework
- pydantic-settings 2.12.0 for configuration
- Rich for terminal formatting (included with Typer)

**Implements:**
- CLI-first architecture pattern (single source of truth)
- Hierarchical configuration (global defaults, project overrides)

**Addresses:**
- All basic CRUD operations (table stakes)
- Configuration system (table stakes)
- Status/health check (table stakes)

### Phase 3: Background Processing & Git Hooks
**Rationale:** Background queue required before git hooks to ensure non-blocking behavior. Git hooks must never delay commits (critical UX requirement). Automatic capture from commits is core differentiator but depends on async queue.

**Delivers:**
- aiojobs-based async queue with job submission and background worker
- --async flag support in CLI commands
- post-commit git hook implementation
- Hook installation script
- Job definitions for capture operations

**Uses:**
- aiojobs 1.4.0 for async task scheduling
- pre-commit 4.5.1 for git hooks framework

**Implements:**
- Background async queue pattern (non-blocking operations)
- Git hook wrapper pattern (shell scripts calling CLI)

**Addresses:**
- Git post-commit hook (differentiator—automatic capture)
- Background processing (differentiator—never blocks dev work)

**Avoids:**
- Blocking git operations (critical pitfall #2—async-first architecture)
- LLM quota exhaustion (critical pitfall #3—fallback strategy in core)

### Phase 4: MCP Server Integration
**Rationale:** MCP server is wrapper around core operations, built after CLI is stable. Can call core library directly (not CLI) for better error handling. Stdio transport required for Claude Desktop, HTTP transport for generic clients.

**Delivers:**
- MCP server using official Python SDK
- Tool definitions (add_knowledge, search_knowledge, delete_knowledge, summarize_graph)
- Resource definitions (context retrieval for AI assistants)
- Transport implementations (stdio for Claude Desktop, HTTP for generic clients)
- Transport abstraction (core server logic is transport-agnostic)

**Uses:**
- MCP SDK 1.26.0 (official Anthropic)
- httpx for HTTP transport (already required by Ollama client)

**Implements:**
- MCP server pattern (wraps core operations, not CLI)
- Transport abstraction pattern (stdio and HTTP adapters)

**Addresses:**
- MCP protocol support (table stakes for Claude Code integration)

**Avoids:**
- Transport coupling to business logic (critical pitfall #5—abstraction layer)

### Phase 5: Advanced Features & Smart Retention
**Rationale:** After core functionality validated, add differentiating features. Claude Code hooks enable seamless context injection. Smart retention prevents stale data buildup. Conversation capture extends automatic capture beyond git.

**Delivers:**
- Claude Code session hooks (auto-inject context on session start)
- Semantic context injection (relevant knowledge based on current file/commit)
- Smart retention with 90-day expiration and reinforcement learning
- Access tracking for importance scoring
- Conversation capture (background every 5-10 turns)
- Compact/summarize operations (consolidate redundant knowledge)
- Configurable capture modes (decisions-only vs full)

**Addresses:**
- Claude Code hooks (differentiator)
- Semantic context injection (differentiator)
- Smart retention (differentiator)
- Conversation capture (differentiator)
- Decisions-only mode (differentiator)

### Phase Ordering Rationale

- **Storage first** because in-memory storage is limiting current implementation and everything depends on persistence
- **Core engine second** because it must exist before any interface can use it, and security filtering must be solid before automatic capture
- **CLI third** because it's the primary interface and single source of truth that hooks and MCP will wrap
- **Background queue before hooks** because hooks require non-blocking behavior—never delay commits
- **MCP last** because it's a wrapper that depends on stable core operations but is independent of hooks

**Dependency chain:** Storage → Core (uses storage) → CLI (uses core) → Queue (integrates with CLI) → Hooks (use CLI + queue) → MCP (uses core, parallel to hooks)

**Architecture alignment:** Bottom-up approach matches layered architecture (storage layer → processing layer → interface layer → integration layer)

**Pitfall avoidance:** Phase 1 addresses data loss, Phase 3 prevents blocking operations, security filtering in Phase 1 prevents secrets leakage

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 5 (Smart Retention):** Reinforcement learning for entity importance scoring is niche domain. Research patterns for knowledge graph pruning and RL-based entity selection. Sources in FEATURES.md mention RKGnet (2026) and RAKCR for RL approaches.
- **Phase 4 (MCP Server):** MCP protocol is evolving (v2 coming Q1 2026). May need research-phase to understand best practices for tool definitions and error handling patterns.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Storage Foundation):** Kuzu is well-documented with clear getting-started guides. Embedded database pattern is standard. Security filtering patterns available from detect-secrets and similar tools.
- **Phase 2 (CLI Interface):** Typer is extremely well-documented. CLI-first architecture is established pattern. Configuration management with pydantic-settings is standard.
- **Phase 3 (Background Processing):** asyncio queues are standard Python. Git hooks with pre-commit framework are well-documented. Pattern is straightforward.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages from official PyPI with stable versions. Kuzu 0.11.3, Graphiti Core 0.26.3, MCP SDK 1.26.0, Typer 0.21.1, Ollama 0.6.1 are production-ready. Version compatibility verified. Documentation quality is excellent. |
| Features | MEDIUM-HIGH | Feature landscape based on competitor analysis (MCP Knowledge Graph, kb CLI, Obsidian MCP) and 2026 sources for context management patterns. Table stakes clear, differentiators validated by user needs, anti-features identified from common mistakes. Some uncertainty on smart retention implementation complexity. |
| Architecture | HIGH | Multi-interface knowledge graph architecture is well-established pattern. CLI-first approach validated by Unix design principles and modern CLI tools (Gemini CLI, Confluent CLI). Layered architecture with separation of concerns is standard. Kuzu embedded architecture documented in official repo. |
| Pitfalls | MEDIUM | PITFALLS.md file was missing, so pitfalls synthesized from anti-patterns and risks mentioned in other research files. Confidence is medium because not systematically researched—these are inferred from architecture anti-patterns and feature anti-patterns. Should be validated during implementation. |

**Overall confidence:** HIGH for stack and architecture, MEDIUM-HIGH for features, MEDIUM for pitfalls (due to missing research file)

### Gaps to Address

**Missing PITFALLS.md file:** The parallel research agent for PITFALLS.md did not complete or file was lost. Pitfalls section above is synthesized from anti-patterns in ARCHITECTURE.md and risks in STACK.md/FEATURES.md. During Phase 1 planning, consider running focused pitfall research on:
- Common Kuzu embedded database mistakes
- Security filtering bypass techniques (what patterns miss secrets)
- Async queue failure modes and recovery strategies
- MCP server error handling best practices

**Smart retention implementation details:** FEATURES.md references reinforcement learning for entity importance scoring (RKGnet, RAKCR) but lacks implementation details. During Phase 5 planning, research:
- Practical RL approaches for knowledge graph pruning
- Simpler heuristics (access count + recency) as fallback if RL is too complex
- How to tune 90-day retention window based on usage patterns

**MCP protocol evolution:** MCP SDK 1.26.0 is stable v1.x, but v2 coming Q1 2026. During Phase 4 planning, check:
- Whether v2 is released and if migration is recommended
- New tool definition patterns or breaking changes
- Security best practices for MCP servers (OAuth 2.1 mentioned in sources)

**Quota management details:** Hybrid cloud/local Ollama strategy is clear conceptually but implementation details sparse. During Phase 1 (LLM client), research:
- Cloud Ollama actual free tier limits (if service exists—sources don't confirm public cloud Ollama availability)
- Quota tracking strategy (per-day? per-model?)
- Fallback trigger points (when to switch from cloud to local)

**CPU-only model performance:** Hardware constraint (Intel i7-13620H, no GPU) requires CPU-optimized models. Stack recommends mistral:7b-instruct, phi3:mini, nomic-embed-text. During Phase 1, validate:
- Actual performance on target hardware (latency, tokens/sec)
- Memory requirements (ensure 32GB RAM sufficient)
- Quality trade-offs vs GPU models (acceptable for knowledge graph extraction?)

## Sources

### Primary (HIGH confidence)
- **STACK.md** (this project) — Stack research with official package versions from PyPI, version compatibility verified
- **FEATURES.md** (this project) — Feature research with competitor analysis and 2026 sources for context management
- **ARCHITECTURE.md** (this project) — Architecture research with patterns from official MCP docs, CLI design principles, Kuzu architecture
- [Kuzu PyPI 0.11.3](https://pypi.org/project/kuzu/) — Official package page with version details
- [Graphiti Core PyPI 0.26.3](https://pypi.org/project/graphiti-core/) — Official package with Kuzu backend support
- [MCP Python SDK PyPI 1.26.0](https://pypi.org/project/mcp/) — Official Anthropic SDK
- [Typer PyPI 0.21.1](https://pypi.org/project/typer/) — Official CLI framework
- [Ollama Python PyPI 0.6.1](https://pypi.org/project/ollama/) — Official Python client
- [MCP Architecture Overview](https://modelcontextprotocol.io/docs/learn/architecture) — Official protocol architecture
- [Kuzu Documentation](https://kuzudb.github.io/docs/tutorials/) — Getting started and architecture

### Secondary (MEDIUM confidence)
- [Command Line Interface Guidelines](https://clig.dev/) — CLI design principles cited in ARCHITECTURE.md
- [Tailor Gemini CLI to your workflow with hooks](https://developers.googleblog.com/tailor-gemini-cli-to-your-workflow-with-hooks/) — 2026 CLI hooks patterns
- [GitHub: graphiti](https://github.com/getzep/graphiti) — Knowledge graph implementation details
- [MCP Knowledge Graph by shaneholloman](https://github.com/shaneholloman/mcp-knowledge-graph) — Anthropic's persistent memory implementation for competitor analysis
- [Yelp detect-secrets](https://github.com/Yelp/detect-secrets) — Enterprise secrets detection patterns for security filtering
- [Python asyncio Queues Documentation](https://docs.python.org/3/library/asyncio-queue.html) — Official asyncio queue patterns
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — Configuration best practices

### Tertiary (LOW confidence, needs validation)
- [Cloud Ollama references in STACK.md] — STACK.md mentions "cloud.ollama.ai" but this may be hypothetical—need to verify if public cloud Ollama service exists
- [RKGnet: Deep RL for Knowledge Graphs](https://www.nature.com/articles/s41598-025-31109-8) — 2026 paper on entity importance scoring, implementation details sparse
- [FastMCP as MCP SDK alternative] — Mentioned in STACK.md but unofficial, use official SDK for stability

---
*Research completed: 2026-02-02*
*Ready for roadmap: yes*
*Note: PITFALLS.md file was missing from research outputs; pitfalls synthesized from anti-patterns in ARCHITECTURE.md and risks in other research files*
