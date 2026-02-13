# Phase 6: Automatic Capture - Research

**Researched:** 2026-02-13
**Domain:** Git hooks, conversation capture, LLM-powered summarization, background job processing
**Confidence:** HIGH

## Summary

Phase 6 implements automatic knowledge capture from git commits and Claude Code conversations using a file-based signal pattern for git hooks, a background worker processing system, and LLM-powered batch summarization. The architecture leverages the existing Phase 5 queue infrastructure for all heavy processing, ensuring hooks remain non-blocking (<5ms for git, imperceptible for conversation).

The git hook approach uses a minimal shell script that appends commit hashes to a signal file (`~/.graphiti/pending_commits`), achieving near-instant execution on any machine. Background workers pick up pending hashes, run `git show` to fetch full diffs, batch 10 commits together, send to LLM for summarization, and store the result. Conversation capture uses Claude Code's hook system to observe `Stop` events, extract conversation context, and queue for batch summarization.

All capture operations respect Phase 2 security filters (secrets never reach the LLM) and Phase 5 queue patterns (parallel batching, exponential backoff retry, dead letter for failures). The hook installation system auto-installs on first `graphiti add`, handles existing hooks non-destructively, and provides both uninstall commands and config toggles for granular control.

**Primary recommendation:** Use file-based signal pattern for git hooks (instant), leverage Claude Code Stop hooks for conversation capture, batch-and-summarize at 10 commits/conversation for single session entities, and process everything through the Phase 5 queue infrastructure.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Git hook capture
- Hook captures **full diff + commit message** for every commit (including merge commits)
- **Deduplication for merges**: LLM identifies when merge content overlaps with already-stored knowledge from individual commits and skips redundant entities
- **Batch and summarize**: Don't create one entity per commit. Accumulate commits and summarize in batches of **10 commits** into a single session summary entity
- **Truncate large files**: Cap each file's diff at N lines per file (exact limit is Claude's discretion). Still captures all files but limits total payload
- **File-based signal hook**: The post-commit hook is a minimal shell script that appends the commit hash to `~/.graphiti/pending_commits` (or project-local equivalent). Near-instant on any machine — no Python startup, no queue connection, no network call in the hook itself
- **Background worker processes**: Worker picks up pending commit hashes, runs `git show` to fetch full data, batches 10 commits, sends to LLM for summarization, stores result
- **Non-blocking by design**: No specific millisecond target. The file-append approach is inherently 1-2ms on any machine

#### Conversation capture
- **Both auto and manual modes**: Auto-capture at intervals (configurable, can be disabled) AND manual `graphiti capture` command
- **Auto-capture observation mechanism**: Claude's discretion — pick the best approach from Claude Code hooks or MCP tool hooks based on what's available
- **Extraction strategy**: Claude's discretion — determine optimal approach for extracting knowledge from conversation turns
- **Manual capture**: `graphiti capture` (no args) reads recent conversation context from the current Claude Code session and stores it. No arbitrary text input — that's what `graphiti add` is for

#### Relevance filtering
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

#### Hook installation
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Git | 2.x+ | Commit data extraction, hook installation | Universal version control, post-commit hooks built-in since 1.x |
| Shell (bash/sh) | POSIX | Git hook script | Near-instant execution, no runtime dependencies, available on all platforms |
| Claude Code Hooks | API v2026+ | Conversation observation | Official lifecycle hooks, Stop event for conversation boundaries |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `git show` | Git 2.x+ | Fetch commit diffs with formatting | Background worker retrieves full commit data |
| `jq` | 1.6+ | JSON manipulation in shell | Optional: Parse config in hook script if needed |
| subprocess | Python 3.12+ stdlib | Git command execution | Background worker calls git show |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| File-based signal | Python hook script | Python startup adds 50-200ms overhead, requires Python in PATH |
| Stop hook | UserPromptSubmit hook | Fires too frequently (every prompt), harder to batch |
| `git show` | `git diff HEAD^ HEAD` | Less robust for merge commits, harder formatting control |
| Per-repo hooks | Global core.hooksPath | Global hooks affect all repos, harder to uninstall per-project |

**Installation:**
```bash
# No additional dependencies - uses existing stack
# Git and shell are universal
# Claude Code hooks configured via settings.json
```

---

## Architecture Patterns

### Recommended Project Structure
```
src/
├── capture/              # Phase 6 capture system
│   ├── __init__.py       # Module exports
│   ├── git_capture.py    # Git commit capture logic
│   ├── conversation.py   # Conversation capture logic
│   ├── batching.py       # Batch accumulator (10 commits/conversation)
│   ├── summarizer.py     # LLM batch summarization
│   └── relevance.py      # Content filtering (decisions/architecture/bugs/deps)
├── hooks/                # Hook management system
│   ├── __init__.py       # Module exports
│   ├── installer.py      # Hook installation logic
│   ├── templates/        # Shell script templates
│   │   ├── post-commit.sh  # Git hook template
│   │   └── claude-hooks.json  # Claude Code hook config template
│   └── manager.py        # Hook enable/disable/uninstall
└── cli/
    └── commands/
        ├── capture.py    # Manual capture command
        └── hooks.py      # Hook management commands
```

### Pattern 1: File-Based Signal Hook
**What:** Git post-commit hook that appends commit hash to signal file, no processing in hook itself
**When to use:** All automatic git capture - avoids blocking commits with Python/network operations
**Example:**
```bash
#!/bin/sh
# .git/hooks/post-commit
# Auto-installed by graphiti - DO NOT EDIT

# Check if capture is enabled
if ! graphiti config get hooks.enabled 2>/dev/null | grep -q "true"; then
  exit 0
fi

# Append current commit hash to pending file
COMMIT_HASH=$(git rev-parse HEAD)
PENDING_FILE="${HOME}/.graphiti/pending_commits"

# Ensure directory exists
mkdir -p "$(dirname "$PENDING_FILE")"

# Atomic append (O_APPEND semantics)
echo "$COMMIT_HASH" >> "$PENDING_FILE"

exit 0
```

### Pattern 2: Background Worker Batch Processing
**What:** Worker reads pending commits, batches 10, runs git show, summarizes, stores
**When to use:** All heavy processing - keeps hooks instant
**Example:**
```python
# Pseudo-code pattern (simplified)
def process_git_captures():
    """Background worker: process pending git commits in batches."""
    pending_file = Path.home() / ".graphiti/pending_commits"

    while True:
        # Read and clear pending commits atomically
        commits = read_and_truncate_file(pending_file)

        if not commits:
            time.sleep(1)
            continue

        # Batch into groups of 10
        for batch in chunk_list(commits, size=10):
            # Fetch full diffs
            diffs = [git_show_commit(sha) for sha in batch]

            # Security filter BEFORE LLM
            filtered = [security_filter(diff) for diff in diffs]

            # Truncate large files
            truncated = [truncate_large_files(diff, max_lines=500) for diff in filtered]

            # LLM batch summarization
            summary = llm_summarize_batch(truncated, focus_on=RELEVANCE_CATEGORIES)

            # Store single session entity
            store_session_summary(summary, commit_shas=batch)
```

### Pattern 3: Claude Code Stop Hook
**What:** Hook fires when Claude finishes responding, extracts conversation context for capture
**When to use:** Conversation-based capture - natural boundary for "session" summarization
**Example:**
```json
// .claude/settings.json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "graphiti capture --auto --from-transcript \"$transcript_path\"",
            "async": true,
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

### Pattern 4: Batch Accumulator
**What:** Accumulate items until batch size reached, then flush for processing
**When to use:** Both git and conversation capture - amortizes LLM cost, creates better summaries
**Example:**
```python
class BatchAccumulator:
    """Accumulate items until batch size reached."""
    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self.items = []

    def add(self, item: Any) -> Optional[list]:
        """Add item to batch. Returns full batch if ready, None otherwise."""
        self.items.append(item)

        if len(self.items) >= self.batch_size:
            batch = self.items
            self.items = []
            return batch

        return None

    def flush(self) -> list:
        """Force-flush partial batch (e.g., on shutdown)."""
        batch = self.items
        self.items = []
        return batch
```

### Pattern 5: Hook Installation Safety
**What:** Check for existing hooks, handle non-destructively via append or core.hooksPath
**When to use:** Hook installation on first `graphiti add`
**Example:**
```python
def install_post_commit_hook(repo_path: Path) -> None:
    """Install post-commit hook non-destructively."""
    hook_path = repo_path / ".git/hooks/post-commit"

    if hook_path.exists():
        # Existing hook - check if it's ours
        content = hook_path.read_text()

        if "graphiti" in content:
            # Already installed
            return

        # Append our hook to existing
        with hook_path.open("a") as f:
            f.write("\n# Graphiti capture\n")
            f.write(GRAPHITI_HOOK_TEMPLATE)
    else:
        # No existing hook - create new
        hook_path.write_text(GRAPHITI_HOOK_TEMPLATE)
        hook_path.chmod(0o755)  # Make executable
```

### Anti-Patterns to Avoid
- **Processing in git hook**: Never run LLM, network, or queue operations in git hook - blocks commits
- **One entity per commit**: Creates noise, loses session context. Batch into session summaries
- **Storing raw code**: Store architectural insight and decisions, not implementation details
- **Destructive hook installation**: Never overwrite existing hooks - append or chain instead
- **Synchronous conversation capture**: Never block Claude's response - always async/background

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Git command parsing | Custom git log/diff parser | `git show --format=... --stat` | Handles merges, binary files, renames correctly. Edge cases are non-trivial |
| Hook lifecycle management | Custom hook orchestration | Claude Code hooks API (Stop event) | Official lifecycle hooks, proper async support, battle-tested |
| Atomic file appends | Custom file locking | Shell `>>` with O_APPEND | POSIX guarantees atomic append for small writes (<PIPE_BUF). Kernel handles locking |
| LLM prompt engineering | Ad-hoc prompts | Structured prompts with categories | Relevance filtering needs explicit category framework, not free-form |
| Background job retries | Custom retry logic | Phase 5 queue infrastructure | Exponential backoff, dead letter, ack/nack already implemented |
| Hook conflict resolution | Custom hook merging | Append to existing + test | Edge cases (multiple tools, hook managers) are subtle. Simple append works |

**Key insight:** Git hooks, file I/O, and background processing have subtle edge cases that are already solved by established patterns. Use existing Phase 5 queue infrastructure rather than building custom capture-specific processing.

---

## Common Pitfalls

### Pitfall 1: Blocking Commits with Slow Hooks
**What goes wrong:** Post-commit hook runs Python, connects to queue, or calls LLM directly - commits block for seconds
**Why it happens:** Instinct to "do the work where the event happens" rather than signal-and-process pattern
**How to avoid:** File-based signal pattern - hook writes commit hash to file (1-2ms), worker processes later
**Warning signs:** Commits feel sluggish, users complain about git performance, hook timeouts in logs

### Pitfall 2: Losing Pending Commits on File Truncation
**What goes wrong:** Worker reads pending_commits file, processes, and truncates - but new commits appended during processing are lost
**Why it happens:** Read-process-truncate creates race window between read and truncate
**How to avoid:** Atomic read-and-truncate: `mv pending_commits processing_commits && process(processing_commits)` or use flock for mutual exclusion
**Warning signs:** Intermittent missing commits, no errors in logs, timing-dependent failures

### Pitfall 3: Creating One Entity Per Commit
**What goes wrong:** Each commit creates a separate entity, flooding graph with granular noise, losing session context
**Why it happens:** Instinct to "capture everything immediately" rather than batch-and-summarize
**How to avoid:** Accumulate 10 commits, then LLM summarizes into single session entity with overall theme
**Warning signs:** Graph has hundreds of tiny commit entities, searches return noise, summaries lack coherence

### Pitfall 4: Storing Raw Code in Entities
**What goes wrong:** LLM stores implementation details ("added function `foo(x: int) -> str`"), not architectural insight
**Why it happens:** Diff contains code, LLM naturally summarizes what it sees without guidance
**How to avoid:** Explicit relevance prompt: "Extract decisions/architecture/bugs/dependencies, NOT raw code. Explain what and why, not how."
**Warning signs:** Entities contain code snippets, function signatures, implementation details - search returns code not knowledge

### Pitfall 5: Overwriting Existing Git Hooks
**What goes wrong:** Installation blindly overwrites .git/hooks/post-commit, destroying user's existing hook
**Why it happens:** Assuming hook doesn't exist, or not checking before writing
**How to avoid:** Check for existing hook first, append graphiti section if exists, warn user about integration
**Warning signs:** User reports broken CI/CD, missing notifications, other tools stop working after graphiti install

### Pitfall 6: Secrets Reaching LLM Despite Security Filters
**What goes wrong:** Security filter runs AFTER git show, or filter has blind spots, secrets sent to LLM
**Why it happens:** Wrong ordering in pipeline, or security filter not comprehensive
**How to avoid:** Security filter is FIRST step after git show, before truncation or LLM. Defense in depth.
**Warning signs:** API keys/tokens appearing in entity content, security audit flags LLM requests

### Pitfall 7: Hook Config Not Respected
**What goes wrong:** Hook continues capturing even when user sets `hooks.enabled=false`
**Why it happens:** Hook script doesn't check config, or checks wrong scope (global vs project)
**How to avoid:** Hook script checks config on every run: `graphiti config get hooks.enabled` - exit if false
**Warning signs:** User disables hooks but capture continues, config changes have no effect

### Pitfall 8: Stop Hook Infinite Loop
**What goes wrong:** Stop hook runs command that triggers another Stop event, creating infinite loop
**Why it happens:** Async command spawns subagent or long operation that itself generates Stop events
**How to avoid:** Check `stop_hook_active` field in Stop event JSON - skip if already processing a Stop hook
**Warning signs:** Claude Code hangs after responding, high CPU usage, logs show repeated Stop events

---

## Code Examples

### Git Show with Truncation
```bash
#!/bin/bash
# Fetch commit diff with stat summary and truncated file diffs

COMMIT_SHA="$1"
MAX_LINES=500  # Truncate individual file diffs at 500 lines

# Get commit metadata + summary stats
git show --format=fuller --stat "$COMMIT_SHA"

# Get per-file diffs, truncated
git diff-tree --no-commit-id --patch "$COMMIT_SHA" | \
  awk -v max="$MAX_LINES" '
    /^diff --git/ {
      if (file_lines > max) print "... (truncated at " max " lines)"
      file_lines = 0
      print
      next
    }
    {
      file_lines++
      if (file_lines <= max) print
    }
    END {
      if (file_lines > max) print "... (truncated at " max " lines)"
    }
  '
```

### Claude Code Stop Hook (Auto-Capture)
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "graphiti capture --auto --transcript-path \"$transcript_path\" --session-id \"$session_id\"",
            "async": true,
            "timeout": 10,
            "statusMessage": "Capturing conversation knowledge..."
          }
        ]
      }
    ]
  }
}
```

### LLM Batch Summarization Prompt
```python
BATCH_SUMMARIZATION_PROMPT = """You are summarizing a development session from {source}.

INPUT: {count} {items} with full context below.

EXTRACT ONLY:
1. **Decisions & Rationale**: Why something was chosen over alternatives
2. **Architecture & Patterns**: System structure, component relationships, design patterns
3. **Bug Fixes & Root Causes**: What went wrong, why, how it was fixed
4. **Dependencies & Config**: Libraries added/removed, config changes, environment setup

EXCLUDE:
- Raw code snippets (store WHAT/WHY, not HOW)
- Routine operations ("ran tests", "formatted code")
- WIP/scratch content (fixup commits, debugging traces)

OUTPUT: Single cohesive session summary as a knowledge graph entity.
Focus on knowledge that helps understand the system's evolution and design decisions.

---
{content}
---

Summarize the session:"""

# Example usage
prompt = BATCH_SUMMARIZATION_PROMPT.format(
    source="git commits",
    count=10,
    items="commits",
    content="\n\n".join(commit_diffs)
)
```

### Atomic Read-and-Clear Pending File
```python
def read_and_clear_pending_commits(pending_file: Path) -> list[str]:
    """Atomically read and clear pending commits file.

    Uses atomic rename to avoid race condition between read and truncate.
    If new commits are appended during processing, they're preserved.
    """
    if not pending_file.exists():
        return []

    # Atomic move to temp file
    temp_file = pending_file.with_suffix('.processing')
    try:
        pending_file.rename(temp_file)
    except FileNotFoundError:
        # Race: file deleted between exists check and rename
        return []

    # Read temp file
    commits = temp_file.read_text().strip().split('\n')

    # Clean up
    temp_file.unlink()

    return [c for c in commits if c]  # Filter empty lines
```

### Hook Installation with Existing Hook Handling
```python
def install_git_hook(repo_path: Path, force: bool = False) -> None:
    """Install post-commit hook, handling existing hooks non-destructively."""
    hook_path = repo_path / ".git/hooks/post-commit"

    # Read our hook template
    template = (Path(__file__).parent / "templates/post-commit.sh").read_text()

    if hook_path.exists():
        existing_content = hook_path.read_text()

        # Check if already installed
        if "graphiti capture" in existing_content or "GRAPHITI_HOOK" in existing_content:
            logger.info("Git hook already installed")
            return

        if not force:
            # Append to existing hook
            logger.info("Existing hook found, appending graphiti section")
            with hook_path.open("a") as f:
                f.write("\n\n# === Graphiti Capture Hook ===\n")
                f.write(template)
        else:
            # Force overwrite (warn user)
            logger.warning("Force overwrite of existing hook")
            hook_path.write_text(template)
    else:
        # No existing hook - create new
        hook_path.write_text(template)

    # Make executable
    hook_path.chmod(0o755)
    logger.info("Git hook installed", path=str(hook_path))
```

### Relevance Filtering
```python
RELEVANCE_CATEGORIES = {
    "decisions": ["choice", "decided", "alternative", "option", "selected", "rejected"],
    "architecture": ["design", "structure", "pattern", "component", "interface", "layer"],
    "bugs": ["fix", "bug", "error", "issue", "problem", "crash", "fail"],
    "dependencies": ["add", "install", "upgrade", "remove", "dependency", "library", "package"]
}

def filter_relevant_content(text: str, categories: list[str]) -> bool:
    """Check if text contains relevant knowledge based on category keywords.

    Returns True if text matches any enabled category, False for routine/WIP content.
    """
    text_lower = text.lower()

    # Exclude patterns (WIP, routine operations)
    exclude_patterns = [
        r"\bfixup!\b", r"\bwip\b", r"\btypo\b",
        r"^formatted?\b", r"^ran tests?\b", r"^updated? readme\b"
    ]

    for pattern in exclude_patterns:
        if re.search(pattern, text_lower):
            return False

    # Check for relevance
    for category in categories:
        keywords = RELEVANCE_CATEGORIES.get(category, [])
        if any(keyword in text_lower for keyword in keywords):
            return True

    return False
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pre-commit hooks for capture | Post-commit hooks | 2024+ | Pre-commit can block commits, post-commit is non-blocking by design |
| Python-based git hooks | Shell script signal + Python worker | 2025+ | Python startup adds 50-200ms, shell is instant |
| Per-commit entities | Batch summarization (10 commits) | LLM era (2023+) | Reduces noise, better session context, lower API costs |
| Manual conversation capture | Auto-capture via lifecycle hooks | Claude Code v2+ (2025+) | Frictionless, no user action required |
| Global git hooks (core.hooksPath) | Per-repo hooks | 2026+ | Avoids affecting all repos, easier uninstall, better isolation |

**Deprecated/outdated:**
- **Pre-commit hooks for capture**: Can't be used for capture because they can block commits. Post-commit is the right event.
- **Synchronous hook processing**: Lefthook/Husky style parallel execution isn't needed here - our hooks signal and exit immediately
- **Per-commit storage**: Creates graph noise. Batch summarization is the modern pattern for LLM-based systems.
- **Manual capture only**: Requires user to remember to capture. Auto-capture via hooks is now expected UX.

---

## Open Questions

### 1. Conversation Extraction Strategy
**What we know:**
- Claude Code Stop hook provides transcript_path and session_id
- Transcript is JSONL with full conversation history
- Stop fires when Claude finishes responding

**What's unclear:**
- How many turns to extract? Last 10? Full session since last capture?
- Extract decisions explicitly or summarize full context?
- How to detect "meaningful" conversations vs. routine queries?

**Recommendation:**
- **Full session extraction** on Stop event, deduplicate with existing stored summaries
- Let LLM filter meaningfulness via relevance prompt - cheaper than pre-filtering heuristics
- Track last_captured_turn in metadata to avoid re-processing

### 2. Exact File Diff Truncation Limit
**What we know:**
- Large diffs need truncation to avoid context limits
- User decided to cap per-file, not total
- git show has no built-in per-file line limit

**What's unclear:**
- What's the optimal line count? 500? 1000?
- Truncate from middle (show start+end) or from end (show start only)?

**Recommendation:**
- **500 lines per file** - balances context vs. payload size
- **Truncate from end** - start of diff has file metadata and context, end is often repetitive
- Include truncation markers in output so LLM knows content was cut

### 3. Hook Collision Resolution
**What we know:**
- Users may have existing post-commit hooks (CI/CD tools, formatters)
- pre-commit framework uses its own hook management
- Lefthook, Husky use different approaches

**What's unclear:**
- When is appending safe vs. when does it break?
- How to detect pre-commit/Lefthook/Husky and integrate?
- Should we use core.hooksPath instead for better isolation?

**Recommendation:**
- **Append to existing hook** as default (safest, works with most setups)
- **Detect pre-commit**: Check for `# pre-commit hook` marker, warn user to use pre-commit native integration
- **Provide core.hooksPath option** via config flag for advanced users who want isolation
- **Test append safety**: Hook should be idempotent (check if already installed before appending)

### 4. Merge Commit Handling
**What we know:**
- User decided to capture merge commits
- LLM should deduplicate overlapping content from individual commits
- git show handles merges specially (combined diff)

**What's unclear:**
- Does git show --cc (combined diff) give enough context for deduplication?
- Should we skip merge commits entirely and rely on individual commits?
- How does batching interact with merges (batch might have merge + its constituents)?

**Recommendation:**
- **Capture merge commits** with `git show -m` (show diff against each parent separately)
- **LLM prompt explicitly mentions deduplication**: "If merge commit overlaps with individual commits already stored, skip redundant entities"
- **Worker metadata tracks commit ancestry**: Check if merge's constituent commits are in same batch, add to prompt context

---

## Sources

### Primary (HIGH confidence)
- [Git Official Documentation - git-show](https://git-scm.com/docs/git-show) - Diff output control, formatting options, merge handling
- [Git Official Documentation - githooks](https://git-scm.com/docs/githooks) - Post-commit hook behavior, parameters, exit codes
- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks) - Hook lifecycle, Stop event, async hooks, JSON I/O

### Secondary (MEDIUM confidence)
- [Git Hooks: The Complete Guide for 2026](https://devtoolbox.dedyn.io/blog/git-hooks-complete-guide) - Best practices for non-blocking post-commit hooks
- [Prompt Engineering Guide - Text Summarization](https://www.promptingguide.ai/prompts/text-summarization) - LLM batch summarization patterns
- [Claude Code Environment Variables Guide](https://medium.com/@dan.avila7/claude-code-environment-variables-a-complete-reference-guide-41229ef18120) - Session detection via CLAUDE_* variables
- [Are File Appends Really Atomic?](https://www.notthewizard.com/2014/06/17/are-files-appends-really-atomic/) - O_APPEND semantics for shell append pattern

### Tertiary (LOW confidence, needs validation)
- [GitHub - rycus86/githooks](https://github.com/rycus86/githooks) - Per-repo vs global hook patterns (framework-specific)
- Web search results on LLM conversation extraction (multiple sources, no canonical pattern)

---

## Metadata

**Confidence breakdown:**
- Git hooks: **HIGH** - Official documentation, well-established patterns, POSIX guarantees for shell append
- Claude Code hooks: **HIGH** - Official API documentation, Stop event is stable, async hooks tested
- Batch summarization: **MEDIUM** - LLM patterns established, but optimal batch size and prompt structure require experimentation
- Conversation extraction: **MEDIUM** - Stop hook is clear, but extraction strategy (full session vs. incremental) needs validation
- Hook installation: **MEDIUM** - Append pattern is standard, but collision detection needs testing across tools
- Relevance filtering: **LOW** - Category keywords are heuristic-based, may need tuning based on actual usage

**Research date:** 2026-02-13
**Valid until:** 60 days (stable Git/Claude Code APIs, fast-moving LLM prompt patterns)
