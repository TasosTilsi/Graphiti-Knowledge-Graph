# Roadmap: Graphiti Knowledge Graph

## Overview

Transform a basic MCP knowledge graph server into a production-ready, CLI-first system with automatic context capture, git-safe project knowledge graphs, and seamless Claude Code integration. Starting from storage foundation (Kuzu migration) through security filtering, LLM integration, and CLI interface, building toward automatic capture via git hooks and conversations, then adding MCP server integration and advanced features like smart retention and performance optimization.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Storage Foundation** - Kuzu database with dual-scope graphs
- [x] **Phase 2: Security Filtering** - File and entity-level sanitization
- [x] **Phase 3: LLM Integration** - Cloud Ollama with local fallback
- [ ] **Phase 4: CLI Interface** - Core operations and configuration
- [ ] **Phase 5: Background Queue** - Async processing for non-blocking operations
- [ ] **Phase 6: Automatic Capture** - Git hooks and conversation capture
- [ ] **Phase 7: Git Integration** - Git-safe knowledge graphs
- [ ] **Phase 8: MCP Server** - Context injection and Claude Code integration
- [ ] **Phase 9: Advanced Features** - Smart retention, performance, and context refresh

## Phase Details

### Phase 1: Storage Foundation
**Goal**: Replace in-memory storage with persistent Kuzu database supporting global and per-project knowledge graphs
**Depends on**: Nothing (first phase)
**Requirements**: R1.1, R1.2
**Success Criteria** (what must be TRUE):
  1. Kuzu database initializes successfully for both global and project scopes
  2. Entities and relationships persist across application restarts without data loss
  3. Graph queries return accurate results with temporal support
  4. System automatically selects correct graph (global vs project) based on context
  5. Both graphs can be accessed and queried simultaneously
**Plans**: 3 plans in 3 waves

Plans:
- [x] 01-01-PLAN.md — Project foundation with dependencies, GraphScope enum, path configuration
- [x] 01-02-PLAN.md — GraphSelector for scope routing, GraphManager for dual-scope database management
- [x] 01-03-PLAN.md — Persistence and isolation tests, verification checkpoint

### Phase 2: Security Filtering
**Goal**: Implement defense-in-depth security filtering to prevent secrets and PII from entering knowledge graphs
**Depends on**: Phase 1 (storage must exist to filter what goes into it)
**Requirements**: R3.1, R3.2, R3.3
**Success Criteria** (what must be TRUE):
  1. Files matching exclusion patterns (.env*, *secret*, *.key) are never processed
  2. High-entropy strings (API keys, tokens) are detected and stripped from entities
  3. Common secret formats (AWS keys, GitHub tokens, JWTs) are identified and blocked
  4. Capture operations fail loudly if secrets are detected with clear error messages
  5. Audit log records all sanitization events for review
**Plans**: 5 plans in 4 waves

Plans:
- [x] 02-01-PLAN.md — Security models and configuration foundation
- [x] 02-02-PLAN.md — File exclusions and audit logging
- [x] 02-03-PLAN.md — Secret detection and allowlist management
- [x] 02-04-PLAN.md — Content sanitizer with typed placeholders
- [x] 02-05-PLAN.md — Integration tests and verification checkpoint

### Phase 3: LLM Integration
**Goal**: Establish hybrid cloud/local Ollama integration with graceful fallback and quota management
**Depends on**: Phase 1 (needs storage for quota tracking)
**Requirements**: R5.1, R5.2, R5.3
**Success Criteria** (what must be TRUE):
  1. Cloud Ollama is used for LLM operations when quota available
  2. System tracks quota usage and logs warnings when approaching limits
  3. Automatic fallback to local Ollama occurs when cloud quota exhausted or network fails
  4. System clearly indicates which LLM provider (cloud vs local) is currently active
  5. All functionality remains operational in local-only fallback mode
**Plans**: 5 plans in 4 waves

Plans:
- [x] 03-01-PLAN.md — Configuration foundation with TOML, env overrides, dependencies
- [x] 03-02-PLAN.md — OllamaClient with cloud-first failover and tenacity retry
- [x] 03-03-PLAN.md — QuotaTracker and LLMRequestQueue for state management
- [x] 03-04-PLAN.md — Full integration with public API convenience functions
- [x] 03-05-PLAN.md — Comprehensive test suite and verification checkpoint

### Phase 4: CLI Interface
**Goal**: Build comprehensive CLI as single source of truth for all knowledge graph operations
**Depends on**: Phase 3 (CLI operations use LLM for embeddings and processing)
**Requirements**: R2.1, R2.2, R2.3
**Success Criteria** (what must be TRUE):
  1. All core operations (add, search, delete, list, summarize, compact) work from terminal
  2. Configuration can be viewed and modified via CLI commands
  3. Health check identifies connectivity and quota issues with clear diagnostics
  4. JSON output mode enables programmatic use of all commands
  5. Help text and error messages guide users effectively
**Plans**: 11 plans (6 original + 5 gap closure) in 3 waves

Plans:
- [x] 04-01-PLAN.md — CLI foundation: Typer app, Rich output, input handling, utilities, entry points
- [x] 04-02-PLAN.md — Add and search commands
- [x] 04-03-PLAN.md — List, show, and delete commands
- [x] 04-04-PLAN.md — Summarize and compact commands
- [x] 04-05-PLAN.md — Config and health commands
- [x] 04-06-PLAN.md — CLI test suite and verification checkpoint
- [x] 04-07-PLAN.md — [GAP CLOSURE] Adapter layer and GraphService for graphiti_core integration
- [x] 04-08-PLAN.md — [GAP CLOSURE] Wire add, search, list commands to real graph operations
- [x] 04-09-PLAN.md — [GAP CLOSURE] Wire show, delete, summarize, compact commands to real graph operations
- [ ] 04-10-PLAN.md — [GAP CLOSURE] Implement list_entities, get_entity, delete_entities, get_stats with real Kuzu queries
- [ ] 04-11-PLAN.md — [GAP CLOSURE] Implement summarize and compact with LLM summarization and entity deduplication

### Phase 5: Background Queue
**Goal**: Implement async processing queue to enable non-blocking git hooks and conversation capture
**Depends on**: Phase 4 (queue processes jobs that call CLI commands)
**Requirements**: R4.3
**Success Criteria** (what must be TRUE):
  1. Capture operations submitted to queue never block the main thread
  2. Queue remains bounded under load (max 100 items) with backpressure handling
  3. Failed captures retry automatically with exponential backoff
  4. System remains responsive during high capture rates (1000+ captures/minute)
  5. Worker thread processes queued jobs successfully in background
**Plans**: TBD

Plans:
- [ ] 05-01: TBD during planning

### Phase 6: Automatic Capture
**Goal**: Enable automatic knowledge capture from git commits and conversations without manual effort
**Depends on**: Phase 5 (requires async queue), Phase 2 (requires security filtering)
**Requirements**: R4.1, R4.2
**Success Criteria** (what must be TRUE):
  1. Git post-commit hook captures commit context without blocking commits (<100ms)
  2. Conversations are captured automatically every 5-10 turns with no perceivable lag
  3. Only relevant information (decisions, architecture) is stored, not noise
  4. Excluded files are never processed during automatic capture
  5. Captured knowledge is queryable and appears in search results
**Plans**: TBD

Plans:
- [ ] 06-01: TBD during planning

### Phase 7: Git Integration
**Goal**: Make project knowledge graphs safe for git commits with validation and merge conflict prevention
**Depends on**: Phase 2 (security filtering must be solid), Phase 6 (capturing to graphs)
**Requirements**: R8.1, R8.2
**Success Criteria** (what must be TRUE):
  1. Project graph files (.graphiti/) are safe to commit to GitHub with no secrets
  2. Graph file sizes remain reasonable (<1MB per commit) for git performance
  3. Concurrent commits from multiple developers don't corrupt graphs
  4. Git diffs of graph changes are meaningful and reviewable
  5. Storage architecture prevents or minimizes merge conflicts
**Plans**: TBD

Plans:
- [ ] 07-01: TBD during planning

### Phase 8: MCP Server
**Goal**: Provide MCP server interface for Claude Code integration with context injection and conversation capture
**Depends on**: Phase 4 (wraps core operations), Phase 6 (conversation capture)
**Requirements**: R6.1, R6.2, R6.3
**Success Criteria** (what must be TRUE):
  1. MCP tools are callable from Claude Code with both stdio and HTTP transports
  2. Relevant context is injected on session start based on current file and commits (<100ms p95)
  3. Context injection respects token budget (under 8K tokens)
  4. Conversations are captured automatically via MCP hooks without blocking
  5. Tool errors propagate clearly to Claude Code with actionable messages
**Plans**: TBD

Plans:
- [ ] 08-01: TBD during planning

### Phase 9: Advanced Features
**Goal**: Add smart retention, performance optimization, capture modes, and context refresh for production readiness
**Depends on**: Phase 8 (all core functionality in place)
**Requirements**: R7.1, R7.2, R9.1, R9.2, R10.1, R10.2, R11.1, R11.2
**Success Criteria** (what must be TRUE):
  1. Unused knowledge expires after configurable period (default 90 days)
  2. Frequently accessed knowledge persists beyond expiration via reinforcement scoring
  3. Decisions-only capture mode (default) excludes code snippets and implementation details
  4. All operations meet latency budgets (context <100ms, search <200ms, health <50ms at p95)
  5. Long conversations (50+ turns) maintain quality via context refresh and forking
**Plans**: TBD

Plans:
- [ ] 09-01: TBD during planning

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Storage Foundation | 3/3 | Complete | 2026-02-03 |
| 2. Security Filtering | 5/5 | Complete | 2026-02-04 |
| 3. LLM Integration | 5/5 | Complete | 2026-02-08 |
| 4. CLI Interface | 9/11 | Gap closure | - |
| 5. Background Queue | 0/TBD | Not started | - |
| 6. Automatic Capture | 0/TBD | Not started | - |
| 7. Git Integration | 0/TBD | Not started | - |
| 8. MCP Server | 0/TBD | Not started | - |
| 9. Advanced Features | 0/TBD | Not started | - |
