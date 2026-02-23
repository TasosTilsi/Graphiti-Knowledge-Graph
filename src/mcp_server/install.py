"""graphiti mcp install — zero-config MCP server registration for Claude Code.

Writes the stdio server entry to ~/.claude.json so Claude Code auto-starts
the graphiti MCP server. Also installs SKILL.md to ~/.claude/skills/graphiti/
to teach Claude how to use graphiti autonomously.
"""
import json
import shutil
import sys
from pathlib import Path

# SKILL.md content — embedded here so it can be installed without external files.
# Written to ~/.claude/skills/graphiti/SKILL.md (user-scope: all projects).
SKILL_MD_CONTENT = """\
---
name: graphiti
description: >
  graphiti is this user's personal knowledge graph for coding projects.
  Use when: starting a new session (inject context), after key decisions or
  architecture discussions (capture knowledge), when user mentions a specific
  file or topic (surface relevant knowledge), or when explicitly asked about
  past context or preferences. Never show TOON format or raw CLI output to
  the user — always present results as natural human-readable prose.
---

## What graphiti does

graphiti stores and retrieves project knowledge: decisions made, architecture
patterns chosen, bug fixes, library preferences, and workflow discoveries.
It learns from conversations and git commit history.

## When to act (automatic behaviors)

**Session start**: Call `graphiti_search` with query "decisions architecture recent"
to load relevant context. If results exist, weave them into your understanding
silently — do not announce "I queried graphiti." Only mention findings if
they change how you approach the user's question.

**After key moments**: After architecture decisions, important bug resolutions,
library choices, or stated preferences, call `graphiti_add` with a concise
summary. Keep the entry focused on the "why", not the "what". Example:
"Decided to use Kuzu instead of SQLite for graph storage because of native
graph query support and embedded deployment model."

**Topic surfacing**: When the user mentions a file, feature, or concept you
haven't encountered in this session, call `graphiti_search` proactively.
Only surface findings if they are actually relevant to the current task.

**Explicit requests**: When asked "what do you know about X", "check your
memory", or "do you remember when we decided Y" — always use graphiti.

## How to present results

TOON format is an internal wire encoding — never show it to the user. Always
translate tool results into natural conversational prose:

- BAD: "Here are the TOON results: [3,]{id,name}:\\n1,auth-decision..."
- GOOD: "From your knowledge graph: the auth module uses JWT with refresh
  token rotation, a decision made to avoid session storage complexity."

## Tool reference

| Tool | Purpose | When to use |
|------|---------|-------------|
| `graphiti_search(query, limit=10)` | Semantic search | Session start, topic surfacing |
| `graphiti_add(content, tags="")` | Store knowledge | After decisions, bug fixes |
| `graphiti_list(limit=15)` | List all items | Overview, browsing |
| `graphiti_show(name_or_id)` | Show one item | Detail view |
| `graphiti_delete(name_or_id)` | Remove an item | Cleanup |
| `graphiti_summarize()` | Graph summary | Status overview |
| `graphiti_compact()` | Deduplicate | Maintenance |
| `graphiti_capture()` | Capture conversation | Non-blocking, use sparingly |
| `graphiti_health()` | System check | Debugging |
| `graphiti_config(key, value="")` | Get/set config | Configuration |

## Token self-management

Always use `--limit` flags. Default (10-15 items) is fine for most searches.
For broad exploratory searches, use `--limit 5`. Never fetch more than 20 items.
The `graphiti://context` resource at session start already respects the 8K
token budget — you do not need to manually limit it.

## Scope

graphiti supports two scopes:
- **project** (default in git repos): knowledge specific to this project
- **global**: preferences and patterns that apply across all projects

Use `scope="global"` for personal preferences; `scope="project"` or default
for project-specific decisions.
"""


def _find_graphiti_executable() -> tuple[str, list[str]]:
    """Find the graphiti executable and return (command, extra_args).

    Returns:
        Tuple of (command, extra_args) where command is the executable path
        and extra_args are prepended before the caller's args.
    """
    # First check PATH
    path = shutil.which("graphiti")
    if path:
        return path, []
    # Check the same venv/prefix as the running Python interpreter
    exe_dir = Path(sys.executable).parent
    venv_graphiti = exe_dir / "graphiti"
    if venv_graphiti.exists():
        return str(venv_graphiti), []
    # Last resort: use the console_scripts entry point via python -c
    return sys.executable, ["-c", "from src.cli import cli_entry; cli_entry()"]


def install_mcp_server(force: bool = False) -> dict:
    """Write graphiti MCP server config to ~/.claude.json and install SKILL.md.

    This enables zero-config Claude Code integration:
    1. Adds 'graphiti' entry to mcpServers in ~/.claude.json
    2. Writes SKILL.md to ~/.claude/skills/graphiti/SKILL.md

    Args:
        force: Overwrite existing entries even if already present

    Returns:
        Dict with 'claude_json_updated' and 'skill_md_installed' boolean results
    """
    results = {"claude_json_updated": False, "skill_md_installed": False}
    command, extra_args = _find_graphiti_executable()

    # --- 1. Write to ~/.claude.json ---
    claude_json_path = Path.home() / ".claude.json"
    config = {}
    if claude_json_path.exists():
        try:
            config = json.loads(claude_json_path.read_text())
        except (json.JSONDecodeError, IOError):
            config = {}  # Treat as empty if malformed

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    already_present = "graphiti" in config["mcpServers"]
    if not already_present or force:
        config["mcpServers"]["graphiti"] = {
            "type": "stdio",
            "command": command,
            "args": extra_args + ["mcp", "serve"],
            "env": {}
        }
        claude_json_path.write_text(json.dumps(config, indent=2))
        results["claude_json_updated"] = True

    # --- 2. Install SKILL.md ---
    skill_dir = Path.home() / ".claude" / "skills" / "graphiti"
    skill_path = skill_dir / "SKILL.md"

    if not skill_path.exists() or force:
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(SKILL_MD_CONTENT)
        results["skill_md_installed"] = True

    return results
