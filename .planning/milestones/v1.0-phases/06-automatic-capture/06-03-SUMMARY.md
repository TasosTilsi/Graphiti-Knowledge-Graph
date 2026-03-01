---
phase: 06-automatic-capture
plan: 03
subsystem: capture-processing
tags: [capture, conversation, git-worker, batch-processing, transcript-tracking]
dependency_graph:
  requires:
    - phase-06-01 (capture pipeline core: summarize_and_store)
    - phase-05 (queue infrastructure: enqueue)
    - phase-02 (security filtering: sanitize_content)
  provides:
    - conversation capture from Claude Code JSONL transcripts
    - git worker end-to-end processing pipeline
    - per-session turn tracking for incremental capture
    - batch processing with relevance pre-filtering
  affects:
    - phase-06-04 (hook integration will call these modules)
tech_stack:
  added:
    - json for JSONL transcript parsing
    - os for environment variable detection
  patterns:
    - atomic metadata writes (write-to-temp, rename)
    - incremental capture via turn tracking
    - pre-filtering before batching (skip early)
    - graceful transcript detection from environment
key_files:
  created:
    - src/capture/conversation.py (Claude Code transcript capture)
    - src/capture/git_worker.py (git commit processing pipeline)
  modified:
    - src/capture/__init__.py (added new exports)
decisions:
  - decision: "Metadata file at ~/.graphiti/capture_metadata.json"
    rationale: "Global location for per-session turn tracking. JSON format for human-readability and debugging. Atomic writes prevent corruption during concurrent updates."
    alternatives: ["per-project metadata", "SQLite storage", "no tracking (re-process all)"]
  - decision: "Separate auto and manual capture modes"
    rationale: "Auto mode (from hooks) is incremental with metadata tracking. Manual mode (from CLI) processes full transcript. Different use cases require different behaviors."
    alternatives: ["always incremental", "always full", "flag-based control"]
  - decision: "Pre-filter relevance before batching"
    rationale: "Skip irrelevant commits early to avoid unnecessary LLM calls. More efficient than filtering after batching. Reduces cost and latency."
    alternatives: ["filter after batching", "no filtering", "filter after LLM"]
  - decision: "Extract commit message from git show output"
    rationale: "Need commit message for relevance filtering. git show includes full metadata. Parse to extract subject line (first non-blank after Date:)."
    alternatives: ["separate git log call", "use git diff-tree --format", "no message extraction"]
  - decision: "Graceful transcript auto-detection"
    rationale: "Check CLAUDE_TRANSCRIPT_PATH env var, then common location (~/.claude/transcript.jsonl). Helpful error message if not found. Reduces friction for manual capture."
    alternatives: ["always require explicit path", "fail silently", "hardcode single location"]
metrics:
  duration_seconds: 172
  task_count: 2
  file_count: 3
  commit_count: 2
  lines_added: 762
  completed_at: "2026-02-13T21:13:41Z"
requirements-completed: [R4.1, R4.2]
---

# Phase 6 Plan 3: Capture Processing Modules Summary

**Conversation capture from Claude Code transcripts and git worker processing pipeline**

## What Was Built

Built the end-to-end processing modules that complete the capture system:

1. **conversation.py**: Claude Code transcript capture
   - `read_transcript()`: Parse JSONL transcript files with error handling
   - `extract_conversation_text()`: Extract content from turns with separators
   - `capture_conversation()`: Main capture function with auto/manual modes
   - `capture_manual()`: CLI entry point with auto-detection
   - Per-session metadata tracking at `~/.graphiti/capture_metadata.json`
   - Atomic metadata writes (write-to-temp, rename)
   - Auto mode: Incremental capture from last_captured_turn
   - Manual mode: Full transcript processing (ignores metadata)

2. **git_worker.py**: End-to-end git commit processing pipeline
   - `process_pending_commits()`: Main processing function
     - Read pending commits atomically
     - Fetch diffs with 500-line truncation
     - Pre-filter for relevance (skip irrelevant early)
     - Batch into groups of 10
     - Summarize and store via LLM
   - `enqueue_git_processing()`: Queue via Phase 5 infrastructure
   - `_extract_commit_message()`: Parse commit subject from git show output
   - Sequential job processing (parallel=False) to avoid race conditions

3. **Updated __init__.py**: Added new exports
   - Conversation: `capture_conversation`, `capture_manual`, `read_transcript`, `extract_conversation_text`
   - Git worker: `process_pending_commits`, `enqueue_git_processing`, `DEFAULT_BATCH_SIZE`, `DEFAULT_MAX_LINES_PER_FILE`

## Architecture Decisions

### Per-Session Turn Tracking

**Problem**: Conversation capture from hooks should be incremental (avoid re-processing same turns).

**Solution**: Metadata file at `~/.graphiti/capture_metadata.json` stores last_captured_turn per session_id.

**Format**:
```json
{
  "session_abc123": 42,
  "session_xyz789": 15
}
```

**Auto mode**: Read from last_captured_turn, update after successful capture.
**Manual mode**: Ignore metadata, process full transcript (for one-off captures).

### Atomic Metadata Writes

**Pattern**: Same as pending commits file from Plan 01.
```python
temp_file = METADATA_FILE.with_suffix('.tmp')
temp_file.write_text(json.dumps(metadata, indent=2))
temp_file.rename(METADATA_FILE)
```

**Why**: Prevents corruption if process crashes mid-write. Rename is atomic on POSIX.

### Pre-Filter Relevance Before Batching

**Problem**: Irrelevant commits waste LLM calls and cost money.

**Solution**: Extract commit message from git show output, run `filter_relevant_commit()` before batching.

**Flow**:
1. Fetch diff → Extract message → Check relevance
2. If relevant: Add to batch
3. If irrelevant: Skip early (log + count)

**Why skip early**: Reduces LLM calls, faster processing, lower cost. More efficient than filtering after batching.

### Transcript Auto-Detection

**Problem**: Manual capture should "just work" without requiring transcript path.

**Solution**: Try multiple detection methods:
1. Check `CLAUDE_TRANSCRIPT_PATH` environment variable
2. Try common location: `~/.claude/transcript.jsonl`
3. If not found: Raise ValueError with helpful message

**User experience**: `await capture_manual()` works if transcript in standard location.

### Sequential Git Processing

**Problem**: Multiple git workers processing simultaneously could race on pending file.

**Solution**: Enqueue with `parallel=False`. Phase 5 queue ensures sequential processing (only one git worker at a time).

**Trade-off**: Slower processing vs correctness. Acceptable since git commits are asynchronous anyway.

## Implementation Highlights

### Conversation Capture

**JSONL parsing with error handling**:
```python
for line_num, line in enumerate(f, start=1):
    try:
        turn = json.loads(line)
        # Extract index from multiple possible fields
        turn_index = turn.get('index', turn.get('turn', line_num - 1))
        if turn_index <= since_turn:
            continue
        turns.append(turn)
    except json.JSONDecodeError:
        logger.warning("malformed_json_line_skipped", line_num=line_num)
        continue
```

**Why flexible index extraction**: Claude Code transcript format may vary. Try `index`, `turn`, or fall back to line number.

**Turn separator format**:
```
---
Turn 1:
<content>
---
Turn 2:
<content>
```

Provides clear context for LLM summarization.

### Git Worker Processing

**Commit message extraction**:
```python
def _extract_commit_message(diff_output: str) -> str:
    lines = diff_output.split('\n')
    found_date = False
    for line in lines:
        if line.startswith('Date:'):
            found_date = True
            continue
        if found_date and line.strip():
            return line.strip()
    return ""
```

Finds first non-blank line after `Date:` header. This is the commit subject line.

**Pre-filtering logic**:
```python
for sha in commit_hashes:
    diff = fetch_commit_diff(sha, max_lines_per_file=500)
    commit_message = _extract_commit_message(diff)

    if not filter_relevant_commit(commit_message):
        logger.debug("commit_skipped_not_relevant", sha=sha[:8])
        skipped_count += 1
        continue

    relevant_diffs.append(diff)
```

Skip early to avoid batching irrelevant commits.

**Batch processing with partial flush**:
```python
for diff in relevant_diffs:
    batch = accumulator.add(diff)
    if batch:
        # Process full batch
        await summarize_and_store(batch, ...)

# After loop: flush partial batch
partial_batch = accumulator.flush()
if partial_batch:
    await summarize_and_store(partial_batch, ...)
```

Ensures no commits are lost (partial batches are processed too).

### Integration Points

**Phase 6 Plan 1** (Capture Pipeline):
- `summarize_and_store()`: High-level bridge to graph storage
- `summarize_batch()`: LLM summarization with security filtering
- `filter_relevant_commit()`: Content relevance checking

**Phase 5** (Queue Infrastructure):
- `enqueue()`: Add git processing jobs to background queue
- Sequential job ordering (parallel=False)

**Phase 2** (Security):
- Security filtering happens inside `summarize_batch()` before LLM
- Automatic for all capture sources

## Deviations from Plan

None - plan executed exactly as written.

## Testing & Verification

All verification checks passed:
- ✅ All imports work (`capture_conversation`, `process_pending_commits`, etc.)
- ✅ Metadata operations work (`_load_metadata`, `_save_metadata`)
- ✅ Graceful handling of missing files (returns empty list)
- ✅ Git worker loads with correct defaults (batch_size=10, max_lines=500)
- ✅ Commit message extraction works
- ✅ All exports available from `src.capture` package
- ✅ Metadata file path under `~/.graphiti/`

Manual verification:
```python
# Conversation capture
from src.capture import capture_conversation, read_transcript

# Read transcript (handles missing file gracefully)
turns = read_transcript(Path("/nonexistent"), since_turn=0)
assert turns == []  # Empty list, not exception

# Git worker
from src.capture import process_pending_commits, DEFAULT_BATCH_SIZE

assert DEFAULT_BATCH_SIZE == 10  # Locked user decision
assert DEFAULT_MAX_LINES_PER_FILE == 500  # Claude's discretion

# Message extraction
from src.capture.git_worker import _extract_commit_message
msg = _extract_commit_message("commit abc\nAuthor: Test\nDate: now\n\n    feat: add new feature\n")
assert "feat" in msg
```

## Files Created

| File | Purpose | Lines | Key Functions |
|------|---------|-------|---------------|
| src/capture/conversation.py | Claude Code transcript capture | 400 | capture_conversation, read_transcript, extract_conversation_text, capture_manual |
| src/capture/git_worker.py | Git commit processing pipeline | 330 | process_pending_commits, enqueue_git_processing, _extract_commit_message |
| src/capture/__init__.py | Module exports (updated) | 32 | Package interface with new exports |

**Total**: 2 new files + 1 modified, ~762 lines of code

## Success Criteria Met

- ✅ src/capture/conversation.py reads JSONL transcripts and tracks last_captured_turn per session
- ✅ Conversation capture supports both auto (incremental) and manual (full) modes
- ✅ src/capture/git_worker.py processes pending commits end-to-end: read → filter → batch → summarize → store
- ✅ Default batch size is 10 (locked decision)
- ✅ Default truncation is 500 lines per file (Claude's discretion)
- ✅ Relevance filtering runs before batching (skip irrelevant commits early)
- ✅ Processing integrates with Phase 5 queue via enqueue_git_processing()
- ✅ All new functions exported from src/capture/__init__.py

## Next Steps

**Phase 6 Plan 4** (CLI Hook Commands): Add CLI commands for manual capture triggers (`graphiti capture`, `graphiti process-commits`)

The capture processing modules are ready. Hooks can now call `capture_conversation()` from Stop events and `enqueue_git_processing()` from post-commit hooks. Background workers can call `process_pending_commits()` to process batches.

## Self-Check: PASSED

All created files exist:
```bash
✅ FOUND: src/capture/conversation.py
✅ FOUND: src/capture/git_worker.py
✅ FOUND: src/capture/__init__.py (modified)
```

All commits exist:
```bash
✅ FOUND: cfce6eb (Task 1: conversation capture module)
✅ FOUND: 7746de4 (Task 2: git worker and exports)
```

All verification tests passed:
```bash
✅ All Phase 6 Plan 03 exports OK
✅ Metadata file path: /home/tasostilsi/.graphiti/capture_metadata.json
✅ Batch size matches locked decision (10)
✅ Truncation limit set correctly (500)
✅ Git worker OK
✅ Message extraction OK
✅ All exports OK
```
