# Roadmap: Graphiti Knowledge Graph

## Overview

Transform a basic MCP knowledge graph server into a production-ready, CLI-first system with automatic context capture, local-first knowledge graphs, and seamless Claude Code integration. Starting from storage foundation (Kuzu migration) through security filtering, LLM integration, and CLI interface, building toward automatic capture via git hooks and conversations, then pivoting to on-demand git indexing (replacing journal-based git storage), adding MCP server integration, advanced features, and a frontend visualization UI.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Storage Foundation** - Kuzu database with dual-scope graphs
- [x] **Phase 2: Security Filtering** - File and entity-level sanitization
- [x] **Phase 3: LLM Integration** - Cloud Ollama with local fallback
- [x] **Phase 4: CLI Interface** - Core operations and configuration
- [x] **Phase 5: Background Queue** - Async processing for non-blocking operations
- [x] **Phase 6: Automatic Capture** - Git hooks and conversation capture
- [x] **Phase 7: Git Integration** - Git-safe knowledge graphs (journal-based — superseded by 7.1)
- [x] **Phase 7.1: Git Indexing Pivot** [INSERTED] - Replace journal with local-first on-demand git history indexing
- [x] **Phase 8: MCP Server** - Context injection and Claude Code integration (completed 2026-02-23)
- [x] **Phase 8.1: Gap Closure — Verification Files** [INSERTED] - Write VERIFICATION.md for Phases 03 and 08 to satisfy 3-source cross-reference protocol (completed 2026-02-24)
- [ ] **Phase 8.2: Gap Closure — MCP Server Bugs** [INSERTED] - Fix --async flag bug in capture, context.py bare path, and _auto_install_hooks key mismatch
- [ ] **Phase 8.3: Gap Closure — Queue Dispatch** [INSERTED] - Fix BackgroundWorker._replay_command() dispatch for capture_git_commits jobs (restores Flow 3)
- [x] **Phase 8.4: Gap Closure — Documentation Traceability** [INSERTED] - Update REQUIREMENTS.md checkboxes and add requirements-completed frontmatter to SUMMARY.md files (depends on 8.1, 8.2, 8.3)
- [x] **Phase 8.5: Gap Closure — Human Runtime Verification** [INSERTED] - Step-by-step verification checklists for Phases 02 (security) and 06 (automatic capture) (completed 2026-02-24)
- [x] **Phase 8.6: Gap Closure — Runtime Bug Fixes** [INSERTED] - Fix LLM output `.name` field parsing failure and `process_queue()` race condition (discovered during Phase 06 human verification run 2026-02-26) (completed 2026-02-27)
- [x] **Phase 8.7: Gap Closure — Hook Security Gaps** [INSERTED] - Fix two gaps found during Phase 07/7.1 human verification: (1) `scan_staged_secrets()` silently skips newly staged files due to inverted `deleted_file` check; (2) `graphiti hooks install` does not deploy pre-commit hook despite template and installer function existing (completed 2026-02-27)
- [x] **Phase 8.8: Gap Closure — Verification Documentation** [INSERTED] - Write missing VERIFICATION.md for Phases 8.2, 8.3, and 8.5; update Phase 06 VERIFICATION.md from human_needed to passed; close R4.1 checkbox in REQUIREMENTS.md (completed 2026-03-01)
- [x] **Phase 8.9: Gap Closure — Integration Wiring Fixes** [INSERTED] - Fix three integration bugs found by milestone audit: (1) add missing graphiti_index MCP tool; (2) fix hooks.enabled CLI flag syntax in manager.py; (3) fix _is_claude_hook_installed() dict traversal depth (completed 2026-03-01)
- [ ] **Phase 9: Advanced Features** - Smart retention, performance, and context refresh
- [ ] **Phase 10: Frontend UI** - Localhost graph visualization and monitoring dashboard

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
**Plans**: 3 plans in 3 waves

Plans:
- [x] 05-01-PLAN.md — Queue data models, SQLite storage with dead letter, and hook context detection
- [x] 05-02-PLAN.md — Background worker with parallel batching, retry, and public API
- [x] 05-03-PLAN.md — CLI queue commands (status, process, retry) and app registration

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
**Plans**: 4 plans in 2 waves

Plans:
- [x] 06-01-PLAN.md — Capture pipeline core: git capture, batching, relevance filtering, LLM summarization
- [x] 06-02-PLAN.md — Hook installation system: templates, installer, manager
- [x] 06-03-PLAN.md — Conversation capture and git worker processing pipeline
- [x] 06-04-PLAN.md — CLI commands (capture, hooks) and auto-install wiring

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
**Plans**: 5 plans in 3 waves

Plans:
- [ ] 07-01-PLAN.md -- Journal entry Pydantic model and timestamped file writer
- [ ] 07-02-PLAN.md -- Git configuration files (.gitignore, .gitattributes) and LFS helpers
- [ ] 07-03-PLAN.md -- Checkpoint tracking and incremental journal replay engine
- [ ] 07-04-PLAN.md -- Pre-commit validation hooks (staging, schema, secrets, size)
- [ ] 07-05-PLAN.md -- Auto-heal, compact, hook templates, and auto-setup

### Phase 7.1: Git Indexing Pivot [INSERTED]
**Goal**: Replace journal-based git storage with local-first on-demand git history indexing. Remove journal writer, replay engine, checkpoint tracking, LFS helpers, and journal-specific hooks. Add git history parser that builds knowledge from commit log and diffs on demand. `.graphiti/` becomes fully gitignored — no knowledge committed to git, ever.
**Depends on**: Phase 7 (git hooks framework to reuse), Phase 4 (CLI, Kuzu storage)
**Requirements**: R8.1, R8.2 (revised: local-first replaces git-sharing approach)
**Success Criteria** (what must be TRUE):
  1. `graphiti index` (or automatic trigger) builds Kuzu graph from git history without any committed journal files
  2. Index is rebuilt automatically when new commits arrive (stale detection via git HEAD comparison)
  3. `.graphiti/` is fully gitignored — no journal, no DB, no LFS tracking
  4. Background indexing triggered by post-commit/post-merge hooks is non-blocking (<100ms hook overhead)
  5. Journal writer, replay engine, checkpoint tracking, and LFS helpers are removed from codebase
  6. Pre-commit secrets scanning and size checks are preserved (still valuable for repo hygiene)
**Plans**: 4 plans in 2 waves

Plans:
- [x] 7.1-01-PLAN.md — Remove journal, LFS, checkpoint, replay, autoheal, compact modules; trim surviving gitops files and compact CLI command
- [x] 7.1-02-PLAN.md — Build src/indexer/ package: state management, quality gate, GitIndexer class, two-pass extraction pipeline
- [x] 7.1-03-PLAN.md — Update and create hook templates (post-merge, post-checkout, post-rewrite, pre-commit); extend installer with new hook types and upgrade path
- [x] 7.1-04-PLAN.md — Create graphiti index CLI command; register in app; wire new hook installers into graphiti hooks install

### Phase 8: MCP Server
**Goal**: Provide MCP server interface for Claude Code integration with context injection and conversation capture
**Depends on**: Phase 7.1 (local Kuzu DB built by indexer), Phase 4 (wraps core operations), Phase 6 (conversation capture)
**Requirements**: R6.1, R6.2, R6.3
**Success Criteria** (what must be TRUE):
  1. MCP tools are callable from Claude Code with both stdio and HTTP transports
  2. Relevant context is injected on session start based on current file and commits (<100ms p95)
  3. Context injection respects token budget (under 8K tokens)
  4. Conversations are captured automatically via MCP hooks without blocking
  5. Tool errors propagate clearly to Claude Code with actionable messages
**Plans**: 4 plans in 3 waves

Plans:
- [ ] 08-01-PLAN.md — Package foundation: mcp + python-toon deps, src/mcp_server/ scaffold, TOON utility module
- [ ] 08-02-PLAN.md — MCP tools layer: 10 subprocess-based graphiti_* tool handler functions
- [ ] 08-03-PLAN.md — Server wiring: context resource, FastMCP server, mcp install command, CLI registration
- [ ] 08-04-PLAN.md — Integration smoke tests + human verification checkpoint

### Phase 8.1: Gap Closure — Verification Files [INSERTED]
**Goal**: Write VERIFICATION.md files for Phase 03 (LLM Integration) and Phase 08 (MCP Server) to satisfy the 3-source cross-reference protocol required by milestone audit. Evidence already exists — this phase synthesizes it into the required format.
**Depends on**: Phase 8 (evidence source — 08-04-SUMMARY.md)
**Gap Closure**: Closes procedural gaps for R5.1, R5.2, R5.3 (Phase 03) and R6.1, R6.2, R6.3 (Phase 08)
**Requirements**: R5.1, R5.2, R5.3, R6.1, R6.2, R6.3
**Success Criteria** (what must be TRUE):
  1. `.planning/phases/03-llm-integration/VERIFICATION.md` exists and cites UAT.md as evidence source
  2. `.planning/phases/08-mcp-server/VERIFICATION.md` exists and cites 08-04-SUMMARY.md as evidence source
  3. Both files list the requirements they cover
  4. Known issues (R6.3 --async bug, R6.2 path bug) noted as "tracked in Phase 8.2"
  5. 3-source cross-reference is now satisfiable for both phases
**Plans**: TBD

Plans:
- [ ] 8.1-01-PLAN.md — Write VERIFICATION.md for Phase 03 (LLM Integration)
- [ ] 8.1-02-PLAN.md — Write VERIFICATION.md for Phase 08 (MCP Server)

### Phase 8.2: Gap Closure — MCP Server Bugs [INSERTED]
**Goal**: Fix three bugs in the MCP server layer that cause silent functional failures — capture calls a non-existent CLI flag, context injection always fails without venv on PATH, and success logging is dead code due to wrong key names.
**Depends on**: Phase 8 (fixes bugs introduced in Phase 8 code)
**Gap Closure**: Closes R6.3 (functional bug), R6.2 (flow gap), R4.2 (observability)
**Requirements**: R6.2, R6.3, R4.2
**Success Criteria** (what must be TRUE):
  1. `graphiti_capture()` in `src/mcp_server/tools.py` no longer calls `--async`; uses `--quiet` or equivalent
  2. `src/mcp_server/context.py` resolves graphiti binary via `_GRAPHITI_CLI` path logic, not bare `"graphiti"` string
  3. `_auto_install_hooks()` in `src/cli/commands/add.py` checks `git_hook`/`claude_hook` keys correctly
  4. Flow 4 (MCP context injection) completes end-to-end without PATH dependency
  5. MCP conversation capture completes without silent subprocess failure
**Plans**: 2 plans in 2 waves

Plans:
- [ ] 8.2-01-PLAN.md — Fix graphiti_capture --async flag and context.py bare path
- [ ] 8.2-02-PLAN.md — Fix _auto_install_hooks key names and add integration verification

### Phase 8.3: Gap Closure — Queue Dispatch [INSERTED]
**Goal**: Fix BackgroundWorker._replay_command() to correctly dispatch capture_git_commits jobs. Currently all queue-mediated git commit captures land in the dead letter queue because the worker reads payload.get('command', '') which returns empty string for this job type.
**Depends on**: Phase 5 (Background Queue), Phase 6 (Automatic Capture)
**Gap Closure**: Closes R4.3, R4.2 — restores Flow 3 (git commit → hook → queue → worker → LLM → Kuzu)
**Requirements**: R4.2, R4.3
**Success Criteria** (what must be TRUE):
  1. `_replay_command()` in `src/queue/worker.py` detects `job_type="capture_git_commits"` and dispatches correctly
  2. Git capture jobs process successfully instead of landing in dead letter queue
  3. Direct `process_pending_commits()` path remains functional (not broken by changes)
  4. Flow 3 end-to-end: post-commit hook → enqueue → worker → process_pending_commits() → knowledge captured
  5. Dead letter queue is empty after processing a test git commit
**Plans**: TBD

Plans:
- [ ] 8.3-01-PLAN.md — Fix _replay_command dispatch and add job-type routing for capture_git_commits
- [ ] 8.3-02-PLAN.md — Integration test for Flow 3 end-to-end

### Phase 8.4: Gap Closure — Documentation Traceability [INSERTED]
**Goal**: Update REQUIREMENTS.md traceability table to reflect actual completion state, and add requirements-completed frontmatter to phases 01–07 SUMMARY.md files. Pure documentation — no code changes.
**Depends on**: Phase 8.1 (verification files must exist), Phase 8.2 (bugs fixed), Phase 8.3 (queue fixed) — so docs reflect accurate final state
**Gap Closure**: Updates global traceability for all 19 v1.0 requirements
**Requirements**: All
**Success Criteria** (what must be TRUE):
  1. REQUIREMENTS.md traceability table checkboxes match actual completion state
  2. Phases 01–07 SUMMARY.md files each have `requirements-completed:` frontmatter listing their requirement IDs
  3. Coverage count at top of REQUIREMENTS.md reflects updated state
  4. All `[x]` checkboxes correspond to requirements with confirmed VERIFICATION.md evidence
**Plans**: TBD

Plans:
- [x] 8.4-01-PLAN.md — Update REQUIREMENTS.md and add requirements-completed frontmatter to all SUMMARY.md files

### Phase 8.5: Gap Closure — Human Runtime Verification [INSERTED]
**Goal**: Create guided human verification checklists for Phase 02 (Security Filtering) and Phase 06 (Automatic Capture). These phases have `human_needed` status because static analysis can't substitute for live runtime testing. This phase produces runnable verification scripts and step-by-step guides.
**Depends on**: Nothing (independent)
**Gap Closure**: Provides path to close R3.1, R3.2, R3.3 (security) and R4.1, R4.2 (automatic capture) from human_needed → verified
**Requirements**: R3.1, R3.2, R3.3, R4.1, R4.2
**Success Criteria** (what must be TRUE):
  1. Phase 02 verification guide: commands to test AWS key detection, .env exclusion, audit log writing in a live environment
  2. Phase 06 verification guide: commands to test git hook timing (<100ms), conversation lag, excluded file E2E, captured knowledge queryability
  3. Both guides are runnable by a human without reading source code
  4. Guides include expected output for each check so the human knows pass/fail
  5. Both VERIFICATION.md files updated to `status: passed` after human completes checklist
**Plans**: TBD

Plans:
- [x] 8.5-01-PLAN.md — Human verification guide for Phase 02 (Security Filtering)
- [x] 8.5-02-PLAN.md — Human verification guide for Phase 06 (Automatic Capture)

### Phase 8.6: Gap Closure — Runtime Bug Fixes [INSERTED]
**Goal**: Fix two bugs discovered during Phase 06 human runtime verification (2026-02-26): (1) LLM returns `".name"` (dot-prefixed) instead of `"name"` field key when processing dot-prefixed filenames, causing Pydantic validation failure and 0 entities stored; (2) `process_queue()` race condition — `qsize()` drops to 0 when jobs are "in-flight" (unacked), causing the main loop to stop the worker before processing completes.
**Depends on**: Phase 8.5 (discovered during verification run)
**Gap Closure**: Unblocks Phase 06 human verification Tests 3 and 4 (end-to-end pipeline)
**Requirements**: R4.1, R4.2
**Success Criteria** (what must be TRUE):
  1. `process_pending_commits()` successfully stores entities even when commit touches dot-prefixed files (e.g., `.env.test_verification`)
  2. `graphiti queue process` completes all queued jobs without stopping the worker prematurely
  3. Both fixes verified by re-running the affected pipeline step

Plans:
- [ ] 8.6-01-PLAN.md — Fix LLM output `.name` field normalization in `src/graph/adapters.py`
- [ ] 8.6-02-PLAN.md — Fix `process_queue()` race condition in `src/queue/__init__.py`

### Phase 8.7: Gap Closure — Hook Security Gaps [INSERTED]
**Goal**: Fix two security/wiring gaps discovered during Phase 07/7.1 human verification runs (2026-02-27): (1) `scan_staged_secrets()` inverts the GitPython `deleted_file` semantics — files staged for the first time (new files in index, not in HEAD) appear as `deleted_file=True` and are silently skipped, meaning a developer can commit a brand-new `config.py` containing an AWS key with no warning; (2) `graphiti hooks install` deploys only 4 of 5 planned hooks — `install_precommit_hook()` exists in `src/hooks/installer.py` but is never called from the CLI install command, leaving the secrets/size pre-commit check unwired.
**Depends on**: Phase 8.6 (follows gap closure series)
**Gap Closure**: Closes R8.1 gaps — new-file secrets bypass and missing pre-commit deployment
**Requirements**: R8.1
**Success Criteria** (what must be TRUE):
  1. `scan_staged_secrets()` detects secrets in newly staged files (not previously in HEAD)
  2. `graphiti hooks install` deploys all 5 hooks: post-commit, pre-commit, post-merge, post-checkout, post-rewrite
  3. `graphiti hooks uninstall` removes the pre-commit hook
  4. `graphiti hooks status` reports pre-commit installation state
  5. `verify_phase_07.py` tests new-file secret detection and passes
  6. `verify_phase_71.py` tests 5-hook deployment and passes

Plans:
- [x] 8.7-01-PLAN.md — Fix `scan_staged_secrets()` inverted deleted_file check in `src/gitops/hooks.py`
- [x] 8.7-02-PLAN.md — Wire `install_precommit_hook()` into CLI install/uninstall/status commands
- [x] 8.7-03-PLAN.md — Update verification scripts to test fixed behaviour

### Phase 8.8: Gap Closure — Verification Documentation [INSERTED]
**Goal**: Write missing VERIFICATION.md files for Phases 8.2, 8.3, and 8.5 (unverified gap-closure phases from milestone audit); update Phase 06 VERIFICATION.md from `human_needed` to `passed`; close R4.1 REQUIREMENTS.md checkbox.
**Depends on**: Phase 8.5 (human verification guide already produced; this phase records completion)
**Gap Closure**: Closes R4.1 (partial → complete); satisfies 3-source cross-reference for Phases 8.2, 8.3, 8.5
**Requirements**: R4.1
**Success Criteria** (what must be TRUE):
  1. `.planning/phases/08.2-gap-closure-mcp-server-bugs-inserted/VERIFICATION.md` exists and documents bug fixes for --async flag, context.py bare path, _auto_install_hooks keys
  2. `.planning/phases/08.3-gap-closure-queue-dispatch-inserted/VERIFICATION.md` exists and documents BackgroundWorker._replay_command() dispatch fix
  3. `.planning/phases/08.5-gap-closure-human-runtime-verification-inserted/VERIFICATION.md` exists and records human verification guide completion
  4. `.planning/phases/06-automatic-capture/VERIFICATION.md` status updated from `human_needed` to `passed`
  5. REQUIREMENTS.md R4.1 checkbox changed from `[ ]` to `[x]` and traceability table shows Complete

Plans:
- [x] 8.8-01-PLAN.md — Write VERIFICATION.md for Phases 8.2, 8.3, and 8.5
- [x] 8.8-02-PLAN.md — Update Phase 06 VERIFICATION.md and close R4.1 in REQUIREMENTS.md

### Phase 8.9: Gap Closure — Integration Wiring Fixes [INSERTED]
**Goal**: Fix three integration bugs identified by the milestone audit: (1) `graphiti_index` MCP tool is missing — add tool handler and register in server.py; (2) `hooks.enabled` config uses wrong CLI flag syntax in manager.py causing hooks.enabled to always default to True; (3) `_is_claude_hook_installed()` checks wrong dict depth, always reporting hook as not-installed.
**Depends on**: Phase 8.8 (documentation complete before code fixes)
**Gap Closure**: Closes R6.1 (HIGH: graphiti_index missing), R3.3 (MEDIUM: hooks.enabled broken), R4.1/R6.2/R6.3 display (LOW: _is_claude_hook_installed cosmetic)
**Requirements**: R6.1, R3.3, R4.1
**Success Criteria** (what must be TRUE):
  1. `graphiti_index` tool handler exists in `src/mcp_server/tools.py` and is registered in `server.py` — MCP users can trigger git history indexing
  2. `src/hooks/manager.py` calls `graphiti config get hooks.enabled` / `graphiti config set hooks.enabled <value>` (subcommand syntax, not `--get`/`--set` flags)
  3. `_is_claude_hook_installed()` in `src/hooks/manager.py` traverses `entry["hooks"][0]["command"]` instead of `entry.get("command")`
  4. `graphiti hooks status` correctly reports Claude hook installation state
  5. `graphiti config set hooks.enabled false` persists and is read back correctly

Plans:
- [ ] 8.9-01-PLAN.md — Add graphiti_index MCP tool to tools.py and register in server.py
- [ ] 8.9-02-PLAN.md — Fix hooks.enabled CLI syntax and _is_claude_hook_installed() traversal in manager.py

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

### Phase 10: Frontend UI
**Goal**: Localhost web interface for exploring and monitoring the knowledge graph — interactive graph visualization showing entities and connections, plus a monitoring dashboard for capture stats and graph health
**Depends on**: Phase 9 (all core functionality and advanced features in place)
**Requirements**: TBD
**Success Criteria** (what must be TRUE):
  1. `graphiti ui` starts a localhost web server and opens the browser
  2. Interactive graph visualization renders entities as nodes and relationships as edges, clickable for detail
  3. Dashboard view shows capture stats, recent activity, entity counts, and graph health
  4. Navigation between graph exploration and dashboard is seamless
  5. UI works fully offline — no external CDN or API dependencies
**Plans**: TBD

Plans:
- [ ] 10-01: TBD during planning

### Phase 11: Multi-Provider LLM Support
**Goal**: Replace the Ollama-only client with a provider-agnostic LLM layer that supports OpenAI, Anthropic, Groq, Mistral, and any OpenAI-compatible endpoint — configured via a new `[provider]` section in `llm.toml`, with no code changes required to switch providers.
**Depends on**: Phase 10 (all core functionality and UI in place)
**Requirements**: TBD
**Success Criteria** (what must be TRUE):
  1. `[provider] type = "openai"` in `llm.toml` routes all LLM calls through the OpenAI SDK with configurable `base_url` and `api_key`
  2. `[provider] type = "ollama"` (default) preserves all existing behaviour — no regression for current users
  3. Any OpenAI-compatible service (Groq, Mistral, Together AI, LM Studio, etc.) works by setting `type = "openai"` and the appropriate `base_url`
  4. Embeddings provider is independently configurable — can mix Ollama embeddings with OpenAI chat, or vice versa
  5. Failover logic (cloud → local) works for OpenAI-type providers the same as for Ollama
  6. `graphiti config` shows the active provider type and endpoint
  7. The concrete example injection and bare list normalisation in the adapter continue to work regardless of provider
**Plans**: TBD

Plans:
- [ ] 11-01: TBD during planning

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 7.1 -> 8 -> 8.1/8.2/8.3/8.5 (parallel) -> 8.4 -> 8.6 -> 8.7 -> 8.8 -> 8.9 -> 9 -> 10 -> 11

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Storage Foundation | 3/3 | Complete | 2026-02-03 |
| 2. Security Filtering | 5/5 | Complete | 2026-02-04 |
| 3. LLM Integration | 5/5 | Complete | 2026-02-08 |
| 4. CLI Interface | 11/11 | Complete | 2026-02-12 |
| 5. Background Queue | 3/3 | Complete | 2026-02-13 |
| 6. Automatic Capture | 4/4 | Complete | 2026-02-13 |
| 7. Git Integration | 5/5 | Complete   | 2026-02-20 |
| 7.1. Git Indexing Pivot | 4/4 | Complete | 2026-02-20 |
| 8. MCP Server | 4/4 | Complete   | 2026-02-27 |
| 8.1. Gap Closure — Verification Files | 2/2 | Complete    | 2026-02-24 |
| 8.2. Gap Closure — MCP Server Bugs | 2/2 | Complete | 2026-02-24 |
| 8.3. Gap Closure — Queue Dispatch | 2/2 | Complete | 2026-02-24 |
| 8.4. Gap Closure — Documentation Traceability | 1/1 | Complete    | 2026-02-24 |
| 8.5. Gap Closure — Human Runtime Verification | 2/2 | Complete | 2026-02-24 |
| 8.6. Gap Closure — Runtime Bug Fixes | 2/2 | Complete | 2026-02-27 |
| 8.7. Gap Closure — Hook Security Gaps | 3/3 | Complete | 2026-02-27 |
| 8.8. Gap Closure — Verification Documentation | 2/2 | Complete | 2026-03-01 |
| 8.9. Gap Closure — Integration Wiring Fixes | 0/2 | Not started | - |
| 9. Advanced Features | 0/TBD | Not started | - |
| 10. Frontend UI | 0/TBD | Not started | - |
| 11. Multi-Provider LLM Support | 0/TBD | Not started | - |
