---
phase: 06-automatic-capture
plan: 01
subsystem: capture-pipeline
tags: [capture, git-integration, llm-summarization, security-filtering, batch-processing]
dependency_graph:
  requires:
    - phase-02-security (sanitize_content for pre-LLM filtering)
    - phase-03-llm (chat for summarization)
    - phase-04-graph (GraphService for storage)
  provides:
    - git commit capture with atomic pending file I/O
    - batch accumulator for 10-item grouping
    - relevance filtering (4 categories)
    - LLM-powered batch summarization with security gate
  affects:
    - phase-06-02 (git hooks will use capture pipeline)
    - phase-06-03 (conversation capture will use summarizer)
tech_stack:
  added:
    - subprocess for git command execution
    - structlog for capture logging
  patterns:
    - atomic rename for race-free file I/O
    - per-file diff truncation (500 lines max)
    - security-first pipeline (filter BEFORE LLM)
    - graceful LLM fallback (concatenation on unavailable)
key_files:
  created:
    - src/capture/__init__.py (module exports)
    - src/capture/git_capture.py (git commit extraction)
    - src/capture/batching.py (batch accumulator)
    - src/capture/relevance.py (content filtering)
    - src/capture/summarizer.py (LLM summarization)
  modified: []
decisions:
  - decision: "Atomic rename pattern for pending_commits file"
    rationale: "Prevents race condition where new commits appended during processing are lost. Rename to .processing, read/delete temp file, new appends go to original file."
    alternatives: ["flock-based locking", "read-truncate with mutex"]
  - decision: "Per-file diff truncation at 500 lines via awk"
    rationale: "Balances context preservation with payload size. Truncate from end (keep start) since file metadata and initial context most important. awk tracks per-file line count."
    alternatives: ["total line limit", "truncate from middle", "no truncation"]
  - decision: "Security filter BEFORE LLM (sanitize_content)"
    rationale: "Defense in depth from Phase 2. Secrets never reach LLM even if later stages fail. Locked user decision."
    alternatives: ["trust git to not contain secrets", "filter after LLM"]
  - decision: "Graceful LLM fallback to concatenation"
    rationale: "Better to store raw content than lose capture on LLM unavailable. Matches Phase 4 summarize pattern. User can re-process later."
    alternatives: ["fail and queue for retry", "skip capture entirely"]
  - decision: "Fixed regex patterns for fixup!/squash! (deviation)"
    rationale: "\\bfixup!\\b didn't match because ! is not word boundary. Removed trailing \\b to match correctly."
    alternatives: ["use \\bfixup", "match full commit format"]
metrics:
  duration_seconds: 202
  task_count: 2
  file_count: 5
  commit_count: 2
  lines_added: 800
  completed_at: "2026-02-13T19:06:12Z"
---

# Phase 6 Plan 1: Capture Pipeline Core Summary

**Capture pipeline foundation with git extraction, batching, filtering, and LLM summarization**

## What Was Built

Built the core capture pipeline that transforms raw git diffs into clean, relevant knowledge graph entities via LLM summarization. The pipeline consists of 5 modules:

1. **git_capture.py**: Atomic pending file I/O and git diff extraction
   - `read_and_clear_pending_commits()`: Atomic rename pattern prevents race conditions
   - `fetch_commit_diff()`: Runs git show + diff-tree with per-file truncation (500 lines)
   - `append_pending_commit()`: Testing/manual queueing helper
   - Handles merge commits with `-m` flag

2. **batching.py**: Generic batch accumulator for grouping items
   - Default batch size: 10 (user decision from Phase 6 context)
   - Returns full batch when size reached
   - Supports partial flush for shutdown scenarios

3. **relevance.py**: Content filtering for knowledge capture
   - 4 categories: decisions, architecture, bugs, dependencies
   - Keyword-based matching with exclude patterns
   - Filters WIP/routine/scratch content (fixup, squash, typo, formatting)

4. **summarizer.py**: LLM-powered batch summarization
   - BATCH_SUMMARIZATION_PROMPT with extraction/exclusion instructions
   - Merge deduplication: "skip redundant information if merge overlaps with individual commits"
   - Security gate: `sanitize_content()` runs BEFORE LLM (locked Phase 2 decision)
   - Graceful fallback: Returns concatenation on LLMUnavailableError
   - `summarize_and_store()`: High-level bridge to graph storage

5. **__init__.py**: Module exports for clean public API

## Architecture Decisions

### Atomic Rename Pattern for Pending File

**Problem**: Race condition between read and truncate - new commits appended during processing could be lost.

**Solution**: Atomic rename to `.processing` suffix, read/delete temp file. New appends go to original filename during processing.

**Code pattern**:
```python
temp_file = pending_file.with_suffix('.processing')
pending_file.rename(temp_file)  # Atomic on POSIX
commits = temp_file.read_text()
temp_file.unlink()
```

**Why this works**: POSIX guarantees atomic rename. New appends via `echo >> file` create new file with original name while we process temp file.

### Per-File Diff Truncation at 500 Lines

**Problem**: Large commits can exceed LLM context limits. Need truncation that preserves context.

**Solution**: awk-based per-file truncation tracking line count per `diff --git` section. Print truncation marker when exceeded.

**Why 500 lines**: Balances context (enough to understand changes) with payload size (stays within LLM limits). User decision from research: Claude's discretion in 200-1000 range.

**Why truncate from end**: File metadata (name, mode changes) and initial context (hunks near start) are most informative. End of large diffs often repetitive.

### Security Gate BEFORE LLM

**Problem**: Git diffs might contain secrets (API keys, credentials). Must never reach LLM.

**Solution**: Call `sanitize_content()` on joined content BEFORE formatting prompt. Locked Phase 2 decision.

**Defense in depth**: Even if post-LLM filtering existed, this prevents leakage at source.

**Code**:
```python
sanitization_result = sanitize_content(joined_content)
safe_content = sanitization_result.sanitized_content
# Only safe_content goes into prompt
```

### Graceful LLM Fallback

**Problem**: LLM might be unavailable (quota exhausted, network issues). Capture shouldn't fail.

**Solution**: On `LLMUnavailableError`, return basic concatenation with separators. Content still captured, just not summarized.

**Why concatenation not skip**: Better to store raw content than lose capture. User can re-process later when LLM available. Matches Phase 4 `summarize` command pattern.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed regex patterns for fixup!/squash! exclusion**
- **Found during:** Task 2 verification
- **Issue:** Pattern `\bfixup!\b` didn't match "fixup! typo" because `!` is not a word boundary character. The `\b` after `!` prevented matching.
- **Fix:** Changed patterns from `\bfixup!\b` and `\bsquash!\b` to `\bfixup!` and `\bsquash!` (removed trailing `\b`)
- **Files modified:** `src/capture/relevance.py` (EXCLUDE_PATTERNS)
- **Commit:** 9abd14e
- **Test result:** Before fix: `filter_relevant_commit("fixup! typo")` returned `True`. After fix: returns `False` (correct).

## Implementation Highlights

### Git Command Robustness

Used `subprocess.run()` with proper error handling:
- `capture_output=True, text=True` for clean output
- `timeout=30` to prevent hanging on large repos
- Let `CalledProcessError` propagate for debugging (don't catch silently)
- Check merge commits with `git rev-parse {sha}^@` to count parents

### Merge Commit Support

For merge commits (multiple parents), use `git diff-tree -m` to show diff against each parent separately. This provides full context for LLM deduplication.

Detection:
```python
parents = subprocess.run(['git', 'rev-parse', f'{sha}^@'])
is_merge = len(parents.stdout.strip().split('\n')) > 1
```

### Relevance Categories

All 4 categories enabled by default (user decision: full set):
1. **Decisions**: "decided", "chose", "alternative", "option", "rejected", "tradeoff"
2. **Architecture**: "design", "structure", "pattern", "component", "interface", "layer"
3. **Bugs**: "fix", "bug", "error", "issue", "crash", "regression", "root cause"
4. **Dependencies**: "add", "install", "upgrade", "remove", "dependency", "library"

Exclude patterns filter out:
- WIP content: "wip", "fixup!", "squash!"
- Routine ops: "formatted", "ran tests", "update readme", "lint"
- Scratch content: "typo", "temporary experiment", "debugging trace"

### LLM Prompt Structure

BATCH_SUMMARIZATION_PROMPT includes:
- **EXTRACT ONLY**: 4 relevance categories with clear definitions
- **EXCLUDE**: Raw code, routine operations, WIP/scratch
- **SPECIAL NOTE**: Merge deduplication instruction for overlapping content
- **OUTPUT**: Single cohesive session summary (not per-commit)

This guides LLM to extract knowledge (what/why) not implementation (how).

## Testing & Verification

All verification checks passed:
- ✅ git_capture module loads and fetches commit diffs
- ✅ BatchAccumulator accumulates and returns batches at size 10
- ✅ Relevance filter matches category keywords and excludes WIP patterns
- ✅ Summarizer module loads with prompt template
- ✅ All exports available from `src.capture` package

Manual verification:
```python
# Batch accumulator
b = BatchAccumulator(3)
assert b.add(1) is None
assert b.add(2) is None
assert b.add(3) == [1,2,3]  # Full batch returned

# Relevance filter
assert filter_relevant_commit("feat: decided to use Redis")  # Decisions
assert filter_relevant_commit("fix: crash on null pointer")  # Bugs
assert not filter_relevant_commit("fixup! typo")  # Excluded
```

## Integration Points

**Phase 2 Security** (`src.security`):
- `sanitize_content()` called before LLM in `summarize_batch()`
- Returns `SanitizationResult` with `was_modified` flag
- Secrets redacted with typed placeholders: `[REDACTED:aws_key]`

**Phase 3 LLM** (`src.llm`):
- `chat()` for batch summarization
- `LLMUnavailableError` caught for graceful fallback
- Automatic queue-and-retry handled by LLM layer

**Phase 4 Graph** (`src.graph`):
- `get_service()` for GraphService instance
- `run_graph_operation()` wraps async graph operations
- `summarize_and_store()` bridges capture -> storage

## Files Created

| File | Purpose | Lines | Key Functions |
|------|---------|-------|---------------|
| src/capture/__init__.py | Module exports | 51 | Package interface |
| src/capture/git_capture.py | Git extraction | 244 | read_and_clear_pending_commits, fetch_commit_diff |
| src/capture/batching.py | Batch accumulator | 97 | BatchAccumulator class |
| src/capture/relevance.py | Content filtering | 166 | filter_relevant_commit, get_active_categories |
| src/capture/summarizer.py | LLM summarization | 242 | summarize_batch, summarize_and_store |

**Total**: 5 files, ~800 lines of code

## Success Criteria Met

- ✅ src/capture/ package exists with 5 files (init, git_capture, batching, relevance, summarizer)
- ✅ Atomic pending file read-and-clear uses rename pattern (not read+truncate)
- ✅ Per-file diff truncation at 500 lines (Claude's discretion from user decision)
- ✅ Batch accumulator defaults to size 10 (locked user decision)
- ✅ All 4 relevance categories implemented with keyword lists
- ✅ Exclude patterns cover WIP, fixup, routine, scratch content
- ✅ Summarizer calls sanitize_content() BEFORE LLM (locked security gate decision)
- ✅ Summarizer prompt includes merge deduplication instruction
- ✅ LLM fallback returns basic content on LLMUnavailableError

## Next Steps

**Phase 6 Plan 2** (Git Hooks): Install post-commit hook that calls capture pipeline
**Phase 6 Plan 3** (Conversation Capture): Hook Claude Code Stop event for conversation capture
**Phase 6 Plan 4** (Worker Integration): Background worker processes pending commits via queue

The capture pipeline is ready for hook integration. Git hooks and conversation observers will write to `pending_commits`, and background workers will call these modules to process batches.

## Self-Check: PASSED

All created files exist:
```bash
✅ FOUND: src/capture/__init__.py
✅ FOUND: src/capture/git_capture.py
✅ FOUND: src/capture/batching.py
✅ FOUND: src/capture/relevance.py
✅ FOUND: src/capture/summarizer.py
```

All commits exist:
```bash
✅ FOUND: 5db901e (Task 1: git_capture, batching, init)
✅ FOUND: 9abd14e (Task 2: relevance, summarizer, init update)
```

All verification tests passed:
```bash
✅ git_capture OK
✅ batching OK
✅ relevance OK (after regex fix)
✅ summarizer OK
✅ All exports OK
```
