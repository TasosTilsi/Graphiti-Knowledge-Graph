---
phase: 04-cli-interface
plan: 01
subsystem: cli-foundation
tags: [cli, typer, rich, io, scope-resolution]
dependency_graph:
  requires: [storage-selector, context-models]
  provides: [cli-app, output-formatting, input-handling, scope-utils]
  affects: [all-future-cli-commands]
tech_stack:
  added: [typer>=0.15.0, rich>=10.11.0, shellingham>=1.3.0]
  patterns: [singleton-console, scope-resolution, error-handling]
key_files:
  created:
    - src/cli/__init__.py
    - src/cli/output.py
    - src/cli/input.py
    - src/cli/utils.py
    - src/cli/commands/__init__.py
  modified:
    - pyproject.toml
decisions:
  - Remove unused suggest_command import from __init__.py to avoid circular dependency
  - DEFAULT_LIMIT = 15 for result pagination (user decision: 10-20 range)
  - Positional args take precedence over stdin (matches git behavior)
metrics:
  duration: 161s
  tasks_completed: 2
  files_created: 5
  files_modified: 1
  commits: 2
  completed_at: 2026-02-11T00:17:24Z
requirements-completed: [R2.1, R2.2, R2.3]
---

# Phase 04 Plan 01: CLI Foundation Summary

Complete CLI infrastructure with Typer app instance, Rich output formatters, stdin/positional input handling, scope resolution, and dual entry points (graphiti/gk).

## What Was Built

Created the foundational CLI infrastructure that all command implementations depend on:

1. **Typer App Instance** (`src/cli/__init__.py`)
   - Main app with version callback
   - Dual entry points: `graphiti` and `gk`
   - Error handling wrapper with proper exit codes
   - Scaffold for future command registration

2. **Rich Output Module** (`src/cli/output.py`)
   - Singleton console instances (stdout and stderr)
   - Formatters: `print_success`, `print_error`, `print_warning`
   - Data formatters: `print_table`, `print_json`, `print_compact`
   - Dispatch function: `format_output` for auto-detection

3. **Input Handling** (`src/cli/input.py`)
   - `read_content()` with positional arg priority
   - TTY detection for stdin reading
   - UTF-8 encoding with error replacement
   - Clear error messages for missing content

4. **Utility Functions** (`src/cli/utils.py`)
   - `resolve_scope()` for --global/--project flag handling
   - `suggest_command()` for typo suggestions (difflib)
   - `confirm_action()` for dangerous operation prompts
   - Exit code constants: 0/1/2
   - DEFAULT_LIMIT = 15

5. **Entry Points** (pyproject.toml)
   - `graphiti = "src.cli:cli_entry"`
   - `gk = "src.cli:cli_entry"`
   - Added typer[all]>=0.15.0 dependency

## Verification Results

All success criteria met:

- ✓ Typer app instance importable and `--help` works
- ✓ Rich console singleton with TTY auto-detection
- ✓ stdin reading handles both piped and interactive modes
- ✓ Typo suggestions work (`suggest_command('delte')` → `'delete'`)
- ✓ Exit codes follow POSIX convention (0/1/2)
- ✓ Both entry points registered in pyproject.toml
- ✓ Scope resolution respects flags and auto-detects

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed premature suggest_command import**
- **Found during:** Task 1 verification
- **Issue:** `__init__.py` imported `suggest_command` from `utils.py` before utils existed, causing ModuleNotFoundError
- **Fix:** Removed unused import since suggest_command isn't called in current implementation (will be added when commands registered)
- **Files modified:** src/cli/__init__.py
- **Commit:** e309f89 (part of Task 1 commit)

**2. [Rule 3 - Blocking] Installed typer dependency before verification**
- **Found during:** Task 1 verification
- **Issue:** typer not installed, preventing module import tests
- **Fix:** Ran `pip install "typer[all]>=0.15.0"` in venv
- **Files modified:** None (dependency installation)
- **Commit:** None (not tracked in git)

## Technical Details

### Key Implementation Patterns

1. **Singleton Console Pattern**: Single Rich Console instance prevents duplicate initialization and ensures consistent output styling across all commands.

2. **Scope Resolution Logic**:
   ```python
   # Priority: explicit flags > auto-detect
   if global_flag: return (GLOBAL, None)
   if project_flag: return (PROJECT, find_root())
   return determine_scope()  # auto-detect
   ```

3. **Input Priority**: Positional args > stdin (matches git/other CLIs)

4. **Error Handling**: Typer exceptions caught in entry point, mapped to POSIX exit codes.

### Dependencies Added

- `typer[all]>=0.15.0` - CLI framework (includes rich, shellingham)
- `rich>=10.11.0` - Terminal formatting (included via typer[all])
- `shellingham>=1.3.0` - Shell detection (included via typer[all])

### Integration Points

- **Storage Layer**: Uses `GraphSelector.find_project_root()` and `determine_scope()`
- **Models**: Imports `GraphScope` enum for type-safe scope routing
- **Future Commands**: All commands in plans 02-05 will import from these modules

## Files Created

1. `src/cli/__init__.py` - 67 lines - Typer app, version callback, entry point
2. `src/cli/output.py` - 146 lines - Rich console and formatters
3. `src/cli/input.py` - 60 lines - stdin/positional content resolution
4. `src/cli/utils.py` - 124 lines - scope resolution, typo suggestions, utilities
5. `src/cli/commands/__init__.py` - 9 lines - Package marker

## Files Modified

1. `pyproject.toml` - Added typer dependency and dual entry points

## Commits

1. `e309f89` - feat(04-01): create CLI foundation with Typer app and Rich output
2. `8da57d7` - feat(04-01): add input handling and utility modules

## Next Steps

This plan provides the foundation for all CLI commands. Next plans will implement:

- **Plan 02**: `add` command - Add content to knowledge graph
- **Plan 03**: `search` command - Search with filters and formatting
- **Plan 04**: `delete`, `list`, `summarize` commands
- **Plan 05**: `compact`, `config`, `health`, `show` commands

All commands will import from these modules and register with the app instance.

## Self-Check: PASSED

**Files Created:**
- FOUND: src/cli/__init__.py
- FOUND: src/cli/output.py
- FOUND: src/cli/input.py
- FOUND: src/cli/utils.py
- FOUND: src/cli/commands/__init__.py

**Commits:**
- FOUND: e309f89
- FOUND: 8da57d7

**Imports:**
- PASSED: from src.cli import app
- PASSED: from src.cli.output import console
- PASSED: from src.cli.input import read_content
- PASSED: from src.cli.utils import resolve_scope

All artifacts created, all commits exist, all imports work.
