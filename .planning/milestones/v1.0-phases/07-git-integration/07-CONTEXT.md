# Phase 7: Git Integration — Implementation Context

## Decision Summary

Make project knowledge graphs (Kuzu DB + journal) safe for git by using Git LFS for the binary database, individual timestamped journal files for merge-proof operation logs, auto-staging with code commits, incremental rebuild on merge with last-write-wins conflict resolution, and pre-commit validation that scans new entries for secrets and validates schema.

---

## Git-Friendly Format

**Decision**: Journal operations as individual timestamped files (migration-style), Kuzu DB via Git LFS with journal rebuild as fallback

**Rationale**:
- Individual journal files (`.graphiti/journal/20260217_143022_abc123.json`) eliminate merge conflicts — two devs never edit the same file
- Git LFS keeps the binary Kuzu database available for instant use on clone without bloating the repo
- Journal serves as the authoritative source of truth — if LFS isn't available (some environments), the DB can be rebuilt from journal
- Migration-style pattern is proven (Alembic, Django, Flyway) and well-understood by developers

**Constraints**:
- Journal entries have TTL-based cleanup after being successfully applied to the DB (prevents indefinite growth)
- SQLite queue database is **always .gitignored** — it's per-developer transient state (pending jobs, retries, dead letters) that shouldn't be shared
- Journal and queue serve different lifecycle stages: queue = pre-processing (pending), journal = post-processing (successful operations)

**Structure**:
```
.graphiti/
├── database/              # Kuzu DB (Git LFS tracked)
├── journal/               # Operation log (regular git)
│   ├── 20260217_143022_abc123.json
│   ├── 20260217_143045_def456.json
│   └── ...
├── queue.db              # SQLite (.gitignored)
└── .gitignore            # Excludes queue, temp, locks
```

---

## Commit Behavior

**Decision**: Journal entries auto-stage and commit alongside code changes

**Rationale**:
- Developers shouldn't think about graph management separately — it's automatic
- Graph knowledge evolves with the codebase, so they should travel together in commits
- Pre-commit hook + .gitattributes (belt + suspenders) ensures journal changes never get left behind

**Workflow**:
1. Developer makes code changes and commits
2. Pre-commit hook auto-stages any new `.graphiti/journal/*.json` files
3. `.gitattributes` ensures journal directory is always tracked
4. Git LFS-tracked Kuzu DB updates with every commit (stays in sync with journal)

**Skip mechanism**: `GRAPHITI_SKIP=1 git commit` or `--no-graphiti` flag allows developers to skip graph updates for quick fixes or WIP commits

**First clone experience**:
- Auto-setup on first `graphiti` command (not explicit `graphiti init`)
- Detects missing DB, rebuilds from journal, installs git hooks
- Zero manual setup required

---

## Multi-Developer Safety

**Decision**: Last-write-wins by timestamp with incremental journal replay

**Rationale**:
- Timestamp-based ordering is deterministic and simple — no complex merge logic needed
- If two devs modify the same entity, the later operation (by timestamp) wins
- Incremental replay is fast (only apply new journal entries since last sync)
- Git author attribution in journal entries enables auditing and future smart-merge capabilities

**Conflict resolution flow**:
1. Two devs pull and their branches both have new journal entries
2. Git merges cleanly (individual files = no conflicts)
3. Post-merge hook or next `graphiti` command triggers auto-heal
4. Journal entries are replayed in timestamp order
5. Last write wins for any entity-level conflicts

**Health check**: Extended `graphiti health` command includes journal-vs-DB consistency verification

**Rebuild strategy**:
- Track last-applied journal entry in checkpoint file
- On auto-heal, replay only new entries (incremental)
- Full rebuild only on explicit request or detected corruption

---

## Validation Gates

**Decision**: Pre-commit validation with secret scanning, schema validation, and size warnings

**Rationale**:
- Secret scanning on new journal entries catches bypasses (belt + suspenders with Phase 2)
- Schema validation prevents corrupt/malformed entries from entering git
- Size warnings (not blocks) inform developers when `.graphiti/` grows large, suggest `graphiti compact`

**Pre-commit checks**:
1. **Secret scan** — Only scan new journal entries created since last commit (not full re-scan, not skipped)
2. **Schema validation** — Verify each new journal entry has required fields and valid format
3. **Size threshold** — Warn if `.graphiti/` exceeds configurable limit (e.g., 50MB), suggest `graphiti compact` tool

**Exclusions** (`.graphiti/.gitignore`):
- SQLite queue database (`queue.db`)
- Temp files (`.tmp`, `*.lock`)
- Rebuild-in-progress markers
- Logs and debug artifacts

---

## Out of Scope

*No deferred ideas captured — all discussion stayed within phase boundary*

---

## Open Questions

1. **Journal entry format** — What exact JSON schema should journal entries follow? (Fields: operation type, timestamp, author, entity ID, data, etc.)
2. **TTL cleanup timing** — How many days/commits should journal entries persist after being applied? (Suggest: 30 days or 100 commits)
3. **Size threshold default** — What's a reasonable default size warning for `.graphiti/`? (Suggest: 50MB warning, 100MB strongly suggest compaction)
4. **Checkpoint storage** — Where should the "last-applied journal entry" checkpoint be stored? (Options: in DB metadata, separate `.graphiti/checkpoint` file, or git config)
5. **LFS configuration** — Should LFS setup be automatic (detect and configure) or require manual `git lfs install`?
6. **Hook installation** — Should hooks be installed via `core.hooksPath` (project-level) or copied to `.git/hooks/` (repo-local)?
7. **Compact strategy** — What should `graphiti compact` do? (Journal pruning, DB vacuum, entity deduplication, or all of the above?)
