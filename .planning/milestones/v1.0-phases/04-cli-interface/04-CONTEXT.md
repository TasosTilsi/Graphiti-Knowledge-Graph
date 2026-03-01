# Phase 4: CLI Interface - Context

**Gathered:** 2026-02-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Build comprehensive CLI as single source of truth for all knowledge graph operations: add, search, delete, list, summarize, compact, configure, and health check. Configuration viewing/modification via CLI. JSON output mode for programmatic use. Help text and error messages guide users effectively.

</domain>

<decisions>
## Implementation Decisions

### Command structure
- Flat command organization: `graphiti add`, `graphiti search`, `graphiti config` — like git
- Entry point is `graphiti` with `gk` as a built-in alias — both installed
- Content input: both positional argument and stdin — positional for quick entries, stdin when piped (like `git commit -m` vs editor)
- Config command: `graphiti config` (shows all), `graphiti config --set key=value` — flags not subcommands
- Scope auto-detected: project scope if in git repo, global otherwise. `--global` / `--project` flags to override
- Search modes: default is semantic (natural language), `--exact` flag for literal string matching
- Health check: quick pass/fail per component by default, `--verbose` for full diagnostics
- Results: default limit (10-20), `--limit N` or `--all` to override
- Summarize: no args = whole graph summary, with arg = focused summary of a topic
- No separate status command — health covers diagnostics

### Output & formatting
- Rich colored terminal output by default — like cargo or gh CLI
- Format flag: `--format json` (leaves room for other formats like yaml, csv later)
- Mutation feedback: always confirm success ("Added entity: [name]"), `--quiet` to suppress for scripting
- Long operations: animated spinner with status text ("Summarizing 42 entities...")
- Auto-detect TTY: colors on when terminal, off when piped — standard behavior
- Search results show: title + snippet (highlighted match) + metadata (type, created date, scope)
- `--compact` flag: one-line-per-result view for scanning large result sets
- Relationships: brief inline hints in list/search, full details with dedicated `show` command

### Flag & argument design
- Destructive operations (delete, compact): interactive confirmation prompt, `--force` to skip
- Entity references: accept name or ID. If name is ambiguous, prompt to choose — smart matching
- Tagging: LLM auto-categorizes entities, user can override or add tags with `--tag`
- Bulk delete: multiple args supported (`graphiti delete entity1 entity2`), confirmation before executing
- Search filters: full filter set — `--global`/`--project`, `--since 7d`/`--before DATE`, `--type entity|relationship`, `--tag`
- Summarize: both whole-graph (no args) and targeted (with topic arg)
- Compact: confirmation prompt, no dry-run — confirmation is sufficient
- Source provenance: auto-detect source by default (git commit, conversation, manual), `--source` overrides
- Auto-init on first use: first `graphiti add` in a project auto-creates `.graphiti/` — no explicit init step

### Error messages & help
- Actionable errors with suggestions: "Error: No project graph found. Run 'graphiti init' or use --global."
- Typo correction: "Did you mean 'search'?" — like git's typo suggestion
- Tiered help: `--help` shows brief description + 2-3 examples, `--help-all` for comprehensive docs
- Exit codes: 0 = success, 1 = runtime error, 2 = bad arguments — standard convention

### Claude's Discretion
- Exact CLI framework choice (click, typer, argparse, etc.)
- Internal command routing architecture
- Spinner implementation library
- Color/styling library
- Typo matching algorithm
- Default result limit number (somewhere in 10-20 range)

</decisions>

<specifics>
## Specific Ideas

- Command feel should be like git — flat, familiar, predictable
- Config UX inspired by `graphiti config` (show all) with `--set` for changes — not subcommand trees
- Entity matching UX like git branch — accepts names or IDs, prompts on ambiguity
- Rich output like cargo/gh CLI — colored, structured, professional

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-cli-interface*
*Context gathered: 2026-02-10*
