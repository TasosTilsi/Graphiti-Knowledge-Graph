# Requirements

**Last Updated:** 2026-02-02

This document defines the capabilities needed for the Graphiti Knowledge Graph system v1.

---

## R1: Storage & Graph Database

**Priority:** CRITICAL (foundational dependency)

### R1.1: Kuzu Database Integration
- Replace in-memory storage with Kuzu embedded graph database
- Persistent storage with graph queries and traversal
- Entity and relationship model with temporal support
- Efficient embedding storage and vector similarity search

**Acceptance:**
- ✓ Kuzu database initialized and accessible
- ✓ Entities and relationships stored persistently
- ✓ Graph queries return expected results
- ✓ Database survives restarts without data loss

### R1.2: Dual-Scope Storage
- Global preferences graph at `~/.graphiti/global/`
- Per-project graphs at `.graphiti/` (relative to project root)
- Automatic graph selection based on context (global vs project)
- Graph isolation (changes in one don't affect others)

**Acceptance:**
- ✓ Global graph persists user preferences across all projects
- ✓ Project graphs isolated per repository
- ✓ System automatically selects correct graph based on context
- ✓ Both graphs can be accessed simultaneously

**Research Flags:** None (Kuzu well-documented, stable)

---

## R2: CLI Interface

**Priority:** CRITICAL (single source of truth)

### R2.1: Core Operations
- `add <content>` - Add knowledge with optional metadata
- `search <query>` - Semantic search for relevant knowledge
- `list` - List all knowledge entries
- `delete <id>` - Delete specific entry
- `compact` - Remove expired/unused knowledge
- `summarize` - Generate summary of knowledge graph

**Acceptance:**
- ✓ All commands work from terminal
- ✓ Clear error messages on failure
- ✓ JSON output mode for programmatic use
- ✓ Help text for all commands

### R2.2: Configuration Management
- `config get <key>` - Get configuration value
- `config set <key> <value>` - Set configuration value
- `config list` - List all configuration
- Support for global and per-project configuration files

**Acceptance:**
- ✓ Configuration persisted to disk
- ✓ Per-project config overrides global config
- ✓ Validation on config values

### R2.3: Health & Diagnostics
- `health` - Check Ollama connectivity, database, quotas
- `stats` - Show graph statistics (node count, storage size)
- `version` - Display version information

**Acceptance:**
- ✓ Health command identifies connectivity issues
- ✓ Stats accurately reflect graph state
- ✓ Clear diagnostic messages

**Research Flags:** None (Typer CLI framework well-documented)

---

## R3: Security & Sanitization

**Priority:** CRITICAL (must precede git integration)

### R3.1: File-Level Exclusions
- Exclude files by pattern: `.env*`, `*secret*`, `*credential*`, `*.key`, `*.pem`, `*token*`
- Exclude directories: `node_modules/`, `.git/`, `venv/`, `__pycache__/`
- Configurable exclusion patterns per project
- Default safe exclusion list

**Acceptance:**
- ✓ Excluded files never captured
- ✓ Clear logging when files skipped
- ✓ Users can add custom exclusion patterns
- ✓ Tests verify common secret files excluded

### R3.2: Entity-Level Sanitization
- Detect and strip high-entropy strings (API keys, tokens)
- Pattern matching for common secret formats (AWS keys, GitHub tokens, JWTs)
- PII detection with confidence thresholds
- Developer name allowlisting (from git config)

**Acceptance:**
- ✓ Test API keys detected and stripped
- ✓ False positive rate < 5%
- ✓ Developer names from git config not flagged
- ✓ High-confidence PII matches sanitized

### R3.3: Pre-Commit Validation
- Synchronous, blocking secret detection before capture
- Fail loudly if secrets detected
- Audit log of sanitization events

**Acceptance:**
- ✓ Captures fail if secrets detected
- ✓ Clear error messages explaining what was found
- ✓ Audit log shows all sanitization events

**Research Flags:**
- Security Filtering Phase: Tune false positive rate (<5%)
- Test with real developer workflows for false positives

---

## R4: Automatic Capture

**Priority:** HIGH (differentiator)

### R4.1: Conversation-Based Capture
- Capture every 5-10 conversation turns
- Background async processing (never blocks)
- Extract decisions, preferences, architecture choices
- Relevance filtering (only meaningful context)

**Acceptance:**
- ✓ Conversations captured automatically
- ✓ No user-perceivable lag during capture
- ✓ Only relevant information stored (no noise)
- ✓ Captured data visible in graph

### R4.2: Git Post-Commit Hook
- Capture commit message + diff summary on each commit
- Always uses `--async` flag (non-blocking)
- Respects file exclusion patterns
- Captures the "why" behind code changes

**Acceptance:**
- ✓ Hook installed on setup
- ✓ Commits complete in <100ms (no blocking)
- ✓ Commit context captured in graph
- ✓ Excluded files not processed

### R4.3: Background Processing
- Local queue for capture jobs (asyncio.Queue)
- Worker thread processes queue asynchronously
- Backpressure handling (queue doesn't grow unbounded)
- Failure retry with exponential backoff

**Acceptance:**
- ✓ Capture operations never block main thread
- ✓ Queue remains bounded under load (<100 items)
- ✓ Failed captures retry automatically
- ✓ System remains responsive under high capture rate

**Research Flags:**
- Automatic Capture Phase: Performance benchmarks (<100ms file save latency)
- Load test 1000 captures/minute

---

## R5: LLM Integration

**Priority:** HIGH (required for embeddings and capture)

### R5.1: Cloud Ollama Primary
- Use cloud Ollama free tier for LLM calls
- Quota monitoring and tracking
- Graceful degradation when quota exhausted

**Acceptance:**
- ✓ Cloud Ollama used when available
- ✓ Quota tracked and logged
- ✓ Clear warnings when approaching limit

### R5.2: Local Ollama Fallback
- Fallback to local Ollama when cloud unavailable
- Use gemma2:9b for quality operations
- Use llama3.2:3b for fast operations
- Use nomic-embed-text for embeddings

**Acceptance:**
- ✓ Automatic fallback on cloud quota exhaustion
- ✓ Automatic fallback on network errors
- ✓ Clear indication of which LLM used
- ✓ System remains functional in fallback mode

### R5.3: Fallback Hierarchy
- Full context (cloud Ollama, rich embeddings)
- Reduced context (local Ollama, limited embeddings)
- Minimal context (text-only search, no embeddings)
- No context (degraded, basic operations only)

**Acceptance:**
- ✓ System never completely fails
- ✓ Users informed of current mode
- ✓ Each fallback level tested

**Research Flags:**
- Quota Management Phase: Test with artificially low quotas

---

## R6: Claude Code Integration

**Priority:** MEDIUM (differentiator, post-MVP)

### R6.1: MCP Server Tools
- MCP tools wrapping CLI operations
- Stdio transport for Claude Desktop
- HTTP transport for other clients
- Tool definitions following MCP 2024-11-05 spec

**Acceptance:**
- ✓ MCP tools callable from Claude Code
- ✓ Both transports work
- ✓ Errors propagated clearly

### R6.2: Context Injection Hooks
- Hook on Claude Code session start
- Inject relevant context from graph
- Semantic search based on current file + recent commits
- Limit to top-K relevant nodes (<8K tokens)

**Acceptance:**
- ✓ Context injected on session start
- ✓ Context relevant to current work
- ✓ Injection completes in <100ms (p95 latency)
- ✓ Token budget respected

### R6.3: Conversation Capture Hook
- Hook after every 5-10 turns
- Async capture (non-blocking)
- Extract decisions and preferences

**Acceptance:**
- ✓ Conversations captured automatically
- ✓ No user-perceivable lag
- ✓ Captured data queryable

**Research Flags:**
- MCP Server Phase: MCP protocol evolving (v2 coming Q1 2026)
- Performance Phase: Context injection latency (<100ms at p95)

---

## R7: Smart Retention

**Priority:** LOW (post-MVP, refinement)

### R7.1: Time-Based Expiration
- Knowledge expires after 90 days unused (configurable)
- "Unused" = no reads or updates
- Compact operation removes expired knowledge

**Acceptance:**
- ✓ Expired knowledge identified correctly
- ✓ Expiration period configurable per project
- ✓ Compact removes expired entries

### R7.2: Reinforcement-Based Retention
- Entities referenced multiple times persist longer
- Scoring based on read frequency and recency
- Configurable retention boost per reference

**Acceptance:**
- ✓ Frequently accessed knowledge persists beyond 90 days
- ✓ Retention scoring visible in stats
- ✓ Algorithm tunable

**Research Flags:**
- Smart Retention Phase: RL approaches for entity importance (niche, needs research)

---

## R8: Git Integration

**Priority:** MEDIUM (shareable knowledge)

### R8.1: Git-Safe Knowledge Graphs
- Project graphs committable to git
- No secrets in committed graphs (validation)
- Reasonable file sizes (<1MB per commit)
- Human-readable format (JSON or similar)

**Acceptance:**
- ✓ Project graph files safe for GitHub
- ✓ CI rejects PRs with secrets in graphs
- ✓ CI rejects PRs with >10MB graph changes
- ✓ Git diffs meaningful

### R8.2: Merge Conflict Prevention
- Use append-only event logs OR
- Use separate files per entity/edge OR
- Use CRDT-based storage
- Avoid monolithic graph files

**Acceptance:**
- ✓ Concurrent commits don't corrupt graph
- ✓ Merge conflicts resolvable (or don't occur)
- ✓ Test with 3+ developers committing simultaneously

**Research Flags:**
- Git Integration Phase: Storage architecture decision (Git LFS vs. S3 vs. DB vs. CRDT)
- Test concurrent commits for merge conflicts

---

## R9: Capture Modes

**Priority:** LOW (refinement)

### R9.1: Decisions-Only Mode (Default)
- Capture high-level decisions and reasoning
- Skip implementation details and code snippets
- Safer for git commits (less risk of leaking)

**Acceptance:**
- ✓ Captured knowledge describes "why," not "what"
- ✓ No code snippets in captured knowledge
- ✓ Mode is default

### R9.2: Decisions-and-Patterns Mode
- Capture decisions + architectural patterns
- Include code patterns (generalized, not literal)
- Requires stricter sanitization

**Acceptance:**
- ✓ Patterns captured without literal code
- ✓ Stricter sanitization applied
- ✓ Mode selectable per project

---

## R10: Performance

**Priority:** MEDIUM (must not degrade UX)

### R10.1: Latency Budgets
- Context injection: <100ms (p95)
- File save with capture: <100ms (p95)
- Search query: <200ms (p95)
- Health check: <50ms (p95)

**Acceptance:**
- ✓ All operations meet latency targets
- ✓ Measured under realistic load
- ✓ Performance tests in CI

### R10.2: Context Compression
- Limit context to top-K relevant nodes
- Summarize verbose nodes
- Keep prompts under 8K tokens for fast TTFT
- Cache common query patterns

**Acceptance:**
- ✓ Context never exceeds 8K tokens
- ✓ Cached queries respond faster
- ✓ Summaries preserve key information

**Research Flags:**
- Performance Phase: Optimize after automatic capture working
- Set p95 latency goals and measure

---

## R11: Context Refresh

**Priority:** LOW (long-conversation edge case)

### R11.1: Periodic Context Refresh
- Refresh context every 5-10 turns (for long conversations)
- Remove stale context from prompt
- Use sliding window (keep last N turns + relevant graph nodes)

**Acceptance:**
- ✓ Context refreshes automatically
- ✓ Long conversations (50+ turns) don't degrade
- ✓ Stale context removed

### R11.2: Conversation Forking
- Option to start new conversation with summary
- Preserves context continuity without degradation

**Acceptance:**
- ✓ New conversation includes summary of previous
- ✓ Fork operation seamless

**Research Flags:**
- Context Injection Phase: Test with 100+ turn conversations
- Monitor accuracy degradation at long context

---

## Out of Scope (v1)

These are explicitly NOT included in v1:

- **Real-time collaboration** - Async git-based sharing only
- **Web UI** - CLI/MCP interfaces sufficient
- **Multi-user authentication** - Personal tool, shared via git
- **Vector database alternatives** - Kuzu + embeddings sufficient
- **GraphQL API** - MCP protocol sufficient
- **Distributed deployment** - Local-only
- **Mobile apps** - Desktop/CLI only
- **Cloud-native architecture** - Local-first always

---

## Traceability

Mapping of requirements to phases in ROADMAP.md:

| Requirement | Phase | Status |
|-------------|-------|--------|
| R1.1: Kuzu Database Integration | Phase 1: Storage Foundation | Pending |
| R1.2: Dual-Scope Storage | Phase 1: Storage Foundation | Pending |
| R3.1: File-Level Exclusions | Phase 2: Security Filtering | Complete |
| R3.2: Entity-Level Sanitization | Phase 2: Security Filtering | Complete |
| R3.3: Pre-Commit Validation | Phase 2: Security Filtering | Complete |
| R5.1: Cloud Ollama Primary | Phase 8.1: Gap Closure — Verification Files | Complete |
| R5.2: Local Ollama Fallback | Phase 8.1: Gap Closure — Verification Files | Complete |
| R5.3: Fallback Hierarchy | Phase 8.1: Gap Closure — Verification Files | Complete |
| R2.1: Core Operations | Phase 4: CLI Interface | Pending |
| R2.2: Configuration Management | Phase 4: CLI Interface | Pending |
| R2.3: Health & Diagnostics | Phase 4: CLI Interface | Pending |
| R4.3: Background Processing | Phase 8.3: Gap Closure — Queue Dispatch | Pending |
| R4.1: Conversation-Based Capture | Phase 8.5: Gap Closure — Human Runtime Verification | Pending |
| R4.2: Git Post-Commit Hook | Phase 8.3: Gap Closure — Queue Dispatch | Pending |
| R8.1: Git-Safe Knowledge Graphs | Phase 7.1: Git Indexing Pivot | Complete |
| R8.2: Merge Conflict Prevention | Phase 7.1: Git Indexing Pivot | Complete |
| R6.1: MCP Server Tools | Phase 8.1: Gap Closure — Verification Files | Pending |
| R6.2: Context Injection Hooks | Phase 8.2: Gap Closure — MCP Server Bugs | Pending |
| R6.3: Conversation Capture Hook | Phase 8.2: Gap Closure — MCP Server Bugs | Pending |
| R7.1: Time-Based Expiration | Phase 9: Advanced Features | Pending |
| R7.2: Reinforcement-Based Retention | Phase 9: Advanced Features | Pending |
| R9.1: Decisions-Only Mode | Phase 9: Advanced Features | Pending |
| R9.2: Decisions-and-Patterns Mode | Phase 9: Advanced Features | Pending |
| R10.1: Latency Budgets | Phase 9: Advanced Features | Pending |
| R10.2: Context Compression | Phase 9: Advanced Features | Pending |
| R11.1: Periodic Context Refresh | Phase 9: Advanced Features | Pending |
| R11.2: Conversation Forking | Phase 9: Advanced Features | Pending |

**Coverage:** 27/27 requirements mapped (100%)

---

*Requirements defined: 2026-02-02*
*Status: Mapped to roadmap phases*
