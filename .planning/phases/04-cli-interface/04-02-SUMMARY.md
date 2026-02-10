---
phase: 04-cli-interface
plan: 02
subsystem: cli-commands-core
tags: [cli, add, search, semantic-search, typer, commands]
dependency_graph:
  requires: [cli-foundation, storage-selector, llm-client, security-sanitizer]
  provides: [add-command, search-command]
  affects: [all-cli-users, knowledge-graph-write, knowledge-graph-read]
tech_stack:
  added: []
  patterns: [stub-functions, spinner-feedback, dual-input-modes, result-formatting, scope-resolution]
key_files:
  created:
    - src/cli/commands/add.py
    - src/cli/commands/search.py
  modified:
    - src/cli/__init__.py
decisions:
  - Auto-init .graphiti/ directory on first project-scope add operation
  - Stub functions return mock data for CLI flow testing before full graph integration
  - Remove explicit Exit(SUCCESS) calls - Typer handles normal exit automatically
  - Default search mode is semantic (--exact enables literal matching)
  - Search result table shows truncated snippets (60 chars) for readability
  - Pagination hint shown when results hit limit
metrics:
  duration: 355s
  tasks_completed: 2
  files_created: 2
  files_modified: 1
  commits: 2
  completed_at: 2026-02-11T00:25:49Z
---

# Phase 04 Plan 02: Add and Search Commands Summary

Implement `graphiti add` and `graphiti search` commands - the fundamental write/read operations for the knowledge graph with flexible input handling, scope resolution, and rich result formatting.

## What Was Built

Created the two most essential CLI commands for knowledge graph operations:

1. **Add Command** (`src/cli/commands/add.py`)
   - Accepts content via positional argument or stdin (piped input)
   - Auto-detects source provenance from git remote or defaults to "manual"
   - Resolves scope with --global/--project flags or auto-detection
   - Auto-creates .graphiti/ directory for project scope on first use
   - Supports --tag for manual categorization (repeatable flag)
   - Supports --format json for parseable output
   - Supports --quiet to suppress success messages
   - Shows spinner during operation with console.status()
   - Stub _add_entity() prepares data structure for future graph integration
   - Returns entity metadata: name, type, scope, created_at, tags, source

2. **Search Command** (`src/cli/commands/search.py`)
   - Semantic search by default, --exact for literal string matching
   - Filters: --since, --before, --type, --tag
   - Result control: --limit (default 15), --all for unlimited
   - Output formats: table (default), --compact (one-liner), --format json
   - Shows spinner during search operation
   - Stub _search_entities() returns mock results for CLI flow testing
   - Table view: Name, Type, Snippet (60 chars), Score, Created
   - Compact view: name (type) - snippet format
   - Shows result count and pagination hints
   - Handles no results gracefully with warning message

3. **Command Registration** (`src/cli/__init__.py`)
   - Imported add_command and search_command
   - Registered both with Typer app
   - Both visible in `graphiti --help` output

## Verification Results

All success criteria met:

- ✓ `graphiti add "content"` adds content and shows success message
- ✓ `echo "content" | graphiti add` reads from stdin
- ✓ `graphiti add --quiet` suppresses output
- ✓ `graphiti add --format json` outputs JSON
- ✓ `graphiti search "query"` shows formatted table of results
- ✓ `graphiti search --exact "literal"` uses literal matching mode
- ✓ `graphiti search --compact` shows one-line-per-result
- ✓ `graphiti search --format json` outputs JSON array
- ✓ Scope auto-detection works, --global/--project flags override
- ✓ Both commands visible in `graphiti --help`

**CLI Runner Tests:**
- Add command: Exit code 0, success message displayed
- Add JSON: Exit code 0, valid JSON output
- Add quiet: Exit code 0, no output except logs
- Search: Exit code 0, results table rendered
- Search exact: Exit code 0, exact mode activated
- Search compact: Exit code 0, one-line-per-result format
- Search JSON: Exit code 0, JSON array output

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed explicit Exit(SUCCESS) calls**
- **Found during:** Overall verification testing
- **Issue:** Commands raised `typer.Exit(EXIT_SUCCESS)` which caused exception handlers to catch and print error messages even on success. Exit code was 0 but output showed "Failed to add content: 0"
- **Fix:** Removed `raise typer.Exit(EXIT_SUCCESS)` statements - Typer automatically handles normal function return as exit code 0. Only keep explicit Exit() for error cases with EXIT_ERROR
- **Files modified:** src/cli/commands/add.py, src/cli/commands/search.py
- **Commit:** a4f4ee8 (amended Task 2 commit)
- **Impact:** Commands now exit cleanly with code 0 on success without triggering exception handlers

## Technical Details

### Key Implementation Patterns

1. **Stub Functions for CLI Testing**: Both commands use stub functions (_add_entity, _search_entities) that return realistic mock data. This allows full end-to-end CLI flow testing before graph operations are wired. Stubs log what they would do for visibility during development.

2. **Dual Input Mode**: Add command handles both positional args and stdin, matching common CLI tool behavior (like git commit -m). Positional arg takes precedence when both are available.

3. **Auto-Init Pattern**: Add command automatically creates .graphiti/ directory when first using project scope, reducing friction for new users. No explicit init command needed.

4. **Flexible Output Formatting**: Both commands support --format json for programmatic use, plus human-friendly formats (table/compact for search, success messages for add).

5. **Spinner Feedback**: All operations show a spinner via console.status() to indicate progress and prevent users thinking the CLI is frozen.

6. **Graceful Error Handling**: Typer exceptions (BadParameter) are re-raised to get proper formatting. General exceptions are caught and formatted with print_error before Exit(ERROR).

### Add Command Flow

```
1. read_content(positional_arg) → resolve stdin/arg
2. resolve_scope(flags) → determine GLOBAL or PROJECT
3. _detect_source() → git remote or "manual"
4. _ensure_project_directory() → auto-create .graphiti/
5. _add_entity() → prepare data (stub)
6. Output: JSON or success message (unless --quiet)
```

### Search Command Flow

```
1. resolve_scope(flags) → determine search scope
2. Compute effective_limit → None if --all, else DEFAULT_LIMIT
3. _search_entities() → execute search (stub)
4. Check results count → warn if empty, else format
5. Format: JSON, compact, or table (default)
6. Show result count and pagination hint
```

### Mock Data Structure

**Add Result:**
```json
{
  "name": "entity_20260211_002442",
  "type": "entity",
  "scope": "project",
  "created_at": "2026-02-11T00:24:42",
  "tags": ["tag1", "tag2"],
  "source": "git@github.com:user/repo.git",
  "content_length": 123
}
```

**Search Results:**
```json
[
  {
    "name": "meeting_notes_20260211",
    "type": "entity",
    "snippet": "Meeting notes discussing query...",
    "score": 0.95,
    "created_at": "2026-02-11T00:00:00",
    "scope": "project",
    "tags": ["meeting", "notes"]
  }
]
```

### Integration Points

- **CLI Foundation**: Uses console, print_success, print_error, print_warning, print_table, print_compact, print_json from output.py
- **Input Handling**: Uses read_content() from input.py for positional/stdin resolution
- **Utilities**: Uses resolve_scope(), DEFAULT_LIMIT, EXIT_SUCCESS, EXIT_ERROR from utils.py
- **Storage Layer**: Will integrate with GraphManager/selector when graph operations are wired
- **LLM Layer**: Search will use semantic embeddings when LLM integration is complete
- **Security Layer**: Add will sanitize content via security filters before storage

## Files Created

1. `src/cli/commands/add.py` - 167 lines - Add command with input resolution, scope handling, auto-init
2. `src/cli/commands/search.py` - 191 lines - Search command with filters, formatting, pagination

## Files Modified

1. `src/cli/__init__.py` - Added add_command and search_command imports and registrations

## Commits

1. `eb7c646` - feat(04-02): implement add command with scope resolution and auto-init
2. `a4f4ee8` - feat(04-02): implement search command with semantic and exact modes

## Next Steps

These commands provide the core read/write operations. Future work:

- **Plan 03**: Implement delete, list, summarize commands
- **Plan 04**: Implement compact, config, health, show commands
- **Integration**: Wire stub functions to actual graph operations when storage layer ready
- **LLM Integration**: Replace mock semantic search with real embeddings
- **Security**: Integrate content sanitization before graph writes
- **Enhancement**: Add LLM-based auto-tagging when tags not provided

The stub pattern allows CLI development and testing to proceed independently of graph/LLM implementation, then swap in real functionality without CLI changes.

## Self-Check: PASSED

**Files Created:**
- FOUND: src/cli/commands/add.py
- FOUND: src/cli/commands/search.py

**Commits:**
- FOUND: eb7c646
- FOUND: a4f4ee8

**Imports:**
- PASSED: from src.cli.commands.add import add_command
- PASSED: from src.cli.commands.search import search_command
- PASSED: from src.cli import app (both commands registered)

**CLI Tests:**
- PASSED: graphiti add "content" → exit 0, success message
- PASSED: graphiti add --format json → exit 0, JSON output
- PASSED: graphiti add --quiet → exit 0, suppressed output
- PASSED: graphiti search "query" → exit 0, results table
- PASSED: graphiti search --exact → exit 0, exact mode
- PASSED: graphiti search --compact → exit 0, one-liner format
- PASSED: graphiti search --format json → exit 0, JSON array
- PASSED: graphiti --help → both commands visible

All artifacts created, all commits exist, all imports work, all CLI tests pass.
