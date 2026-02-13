# Phase 6: Automatic Capture - Context

**Gathered:** 2026-02-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable automatic knowledge capture from git commits and conversations without manual effort. This phase builds the capture triggers (git post-commit hook, Claude Code conversation hook), the LLM-powered summarization pipeline, and the hook installation/management system. The background queue (Phase 5) processes captured jobs. Security filtering (Phase 2) sanitizes content before LLM processing.

</domain>

<decisions>
## Implementation Decisions

### Git hook capture
- Hook captures **full diff + commit message** for every commit (including merge commits)
- **Deduplication for merges**: LLM identifies when merge content overlaps with already-stored knowledge from individual commits and skips redundant entities
- **Batch and summarize**: Don't create one entity per commit. Accumulate commits and summarize in batches of **10 commits** into a single session summary entity
- **Truncate large files**: Cap each file's diff at N lines per file (exact limit is Claude's discretion). Still captures all files but limits total payload
- **File-based signal hook**: The post-commit hook is a minimal shell script that appends the commit hash to `~/.graphiti/pending_commits` (or project-local equivalent). Near-instant on any machine — no Python startup, no queue connection, no network call in the hook itself
- **Background worker processes**: Worker picks up pending commit hashes, runs `git show` to fetch full data, batches 10 commits, sends to LLM for summarization, stores result
- **Non-blocking by design**: No specific millisecond target. The file-append approach is inherently 1-2ms on any machine

### Conversation capture
- **Both auto and manual modes**: Auto-capture at intervals (configurable, can be disabled) AND manual `graphiti capture` command
- **Auto-capture observation mechanism**: Claude's discretion — pick the best approach from Claude Code hooks or MCP tool hooks based on what's available
- **Extraction strategy**: Claude's discretion — determine optimal approach for extracting knowledge from conversation turns
- **Manual capture**: `graphiti capture` (no args) reads recent conversation context from the current Claude Code session and stores it. No arbitrary text input — that's what `graphiti add` is for

### Relevance filtering
- **What to store** (all four categories, full set by default):
  1. Decisions & rationale — why something was chosen over alternatives
  2. Architecture & patterns — system structure, component relationships, design patterns
  3. Bug fixes & root causes — what went wrong, why, how it was fixed
  4. Dependencies & config — libraries added/removed, config changes, environment setup
- **What to exclude**:
  - Raw code snippets — store what code does/why, not the implementation itself
  - Routine operations — skip "ran tests", "formatted code", mechanical actions
  - WIP/scratch content — skip fixup commits, temporary experiments, debugging traces
  - Additional exclusion rules at Claude's discretion based on research
- **Security gate**: Run Phase 2 security filters on raw content BEFORE sending to LLM. Defense in depth — secrets never reach the LLM
- **Configurable categories**: Full set by default, power users can narrow down which categories to capture via config

### Hook installation
- **Auto-install on first `graphiti add`**: When user first runs `graphiti add` in a project, automatically install the post-commit hook. Frictionless, no extra step
- **Existing hooks handling**: Claude's discretion — pick the safest non-destructive approach (append, chain, or hooks directory)
- **Both hook types**: Install both git hooks AND Claude Code conversation hooks in this phase. Full automatic capture from day one
- **Uninstall options**: Both a `graphiti hooks uninstall` CLI command to remove AND a `graphiti config set hooks.enabled false` toggle to disable without removing
- **Config toggle**: Hook checks config on every run — if disabled, exits immediately (no-op)

### Claude's Discretion
- Conversation capture observation mechanism (Claude Code hooks vs MCP hooks)
- Conversation extraction strategy (batch-and-summarize vs decision-extraction)
- Exact truncation limit for large file diffs
- Existing hook collision handling strategy
- Additional content exclusion rules beyond the explicit list

</decisions>

<specifics>
## Specific Ideas

- Git hook is a **shell script**, not Python — just `echo $COMMIT_HASH >> pending_file`. Worker does the heavy lifting later via `git show`
- Batch summarization produces **single session summary entities**, not multiple themed entities per batch
- Security filtering happens at the raw content stage, before any LLM interaction
- The `graphiti capture` command should work within Claude Code sessions to capture current session context

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-automatic-capture*
*Context gathered: 2026-02-13*
