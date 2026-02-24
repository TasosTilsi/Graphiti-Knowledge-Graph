---
phase: 06-automatic-capture
plan: 02
subsystem: hooks
tags: [git-hooks, shell-script, subprocess, json, markers, idempotent]

# Dependency graph
requires:
  - phase: 05-background-queue
    provides: Queue foundation for background processing of captured commits
  - phase: 04-cli-interface
    provides: Config management system for hooks.enabled toggle
provides:
  - Shell script template for git post-commit hook with config check
  - Non-destructive hook installer with marker-based detection
  - Claude Code Stop hook integration for .claude/settings.json
  - Hook lifecycle manager for install/uninstall/enable/disable
affects: [06-03, 06-04, cli-hooks-command]

# Tech tracking
tech-stack:
  added: [subprocess for config interaction]
  patterns: [marker-based hook detection, append strategy for existing hooks, idempotent operations]

key-files:
  created:
    - src/hooks/templates/post-commit.sh
    - src/hooks/installer.py
    - src/hooks/manager.py
    - src/hooks/__init__.py
  modified: []

key-decisions:
  - "Append strategy for existing hooks (non-destructive, preserves other tools' hooks)"
  - "GRAPHITI_HOOK_START/END markers for idempotent detection and removal"
  - "Config check on every hook run (exit immediately if hooks.enabled=false)"
  - "Default enabled=True when config key missing (hooks installed intentionally)"
  - "Graceful failure handling (try both git and Claude hooks even if one fails)"

patterns-established:
  - "Marker-based detection: Use START/END markers for safe append and removal"
  - "Idempotent operations: Check is_installed before attempting install/uninstall"
  - "Executable permissions: Always set 0o755 on installed shell scripts"
  - "Silent defaults: Default to enabled when graphiti CLI not in PATH"

# Metrics
duration: 33min
completed: 2026-02-13

requirements-completed: [R4.1, R4.2]
---

# Phase 6 Plan 2: Hook Installation and Management Summary

**Git post-commit hook template with config toggle, non-destructive installer using marker-based append strategy, and lifecycle manager for both git and Claude Code hooks**

## Performance

- **Duration:** 33 min
- **Started:** 2026-02-13T18:33:20Z
- **Completed:** 2026-02-13T19:06:06Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Shell script template appends commit hash to ~/.graphiti/pending_commits in 1-2ms
- Non-destructive hook installation preserves existing hooks via append strategy
- Idempotent install/uninstall operations via GRAPHITI_HOOK_START/END markers
- Config-based enable/disable toggle checked on every hook execution
- Claude Code Stop hook configured with async:true and 10s timeout

## Task Commits

Each task was committed atomically:

1. **Task 1: Create hook templates and installer** - `18d3641` (feat)
2. **Task 2: Create hook manager for lifecycle operations** - `3497852` (feat)

## Files Created/Modified
- `src/hooks/templates/post-commit.sh` - Shell script template that checks hooks.enabled config and appends commit hash to pending file
- `src/hooks/installer.py` - Non-destructive hook installation with marker-based detection for both git and Claude Code hooks
- `src/hooks/manager.py` - High-level lifecycle management (install_hooks, uninstall_hooks, get_hook_status, get/set_hooks_enabled)
- `src/hooks/__init__.py` - Package exports for all public hook functions

## Decisions Made

**1. Append strategy for existing hooks**
- When post-commit hook already exists, append graphiti section with markers rather than replacing
- Enables coexistence with pre-commit framework and other tools
- Detected pre-commit framework triggers warning suggesting native integration

**2. Marker-based idempotent detection**
- Use GRAPHITI_HOOK_START and GRAPHITI_HOOK_END markers for precise section identification
- Enables safe removal (remove only graphiti section if other content exists)
- Enables idempotent install check (already installed if markers present)

**3. Config check on every hook run**
- Hook calls `graphiti config get hooks.enabled` before executing
- Exits immediately (no-op) if disabled or graphiti not in PATH
- Provides zero-overhead disable without removing hook files

**4. Default enabled when config missing**
- get_hooks_enabled() returns True if config key missing or graphiti unavailable
- Rationale: Hooks are installed intentionally, so enabled by default is sensible
- Prevents hook failure on first install before config set

**5. Graceful failure handling**
- install_hooks() and uninstall_hooks() try both git and Claude hooks individually
- If one fails, still attempt the other and log the error
- Returns dict indicating success/failure for each hook type

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all hook operations worked as specified.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Hook installation and management system complete and ready for:
- Plan 06-03: Integration with CLI commands (`graphiti hooks install/uninstall/status`)
- Plan 06-04: Background worker integration to process pending commits
- Auto-install on first `graphiti add` command (per locked decision)

Key infrastructure in place:
- Non-destructive git hook installation with append strategy
- Claude Code Stop hook configuration for conversation capture
- Config-based enable/disable toggle without removing hooks
- Status reporting for installation state

## Self-Check: PASSED

All files verified:
- FOUND: src/hooks/templates/post-commit.sh
- FOUND: src/hooks/installer.py
- FOUND: src/hooks/manager.py
- FOUND: src/hooks/__init__.py

All commits verified:
- FOUND: 18d3641 (Task 1: Create hook templates and installer)
- FOUND: 3497852 (Task 2: Create hook manager for lifecycle operations)

---
*Phase: 06-automatic-capture*
*Completed: 2026-02-13*
