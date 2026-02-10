# Phase 4: CLI Interface - Research

**Researched:** 2026-02-10
**Domain:** Python CLI development with rich terminal output
**Confidence:** HIGH

## Summary

This phase builds a comprehensive Python CLI tool for knowledge graph operations. The research reveals that **Typer + Rich** is the modern standard stack for building sophisticated Python CLIs in 2026. Typer provides type-safe command definition with automatic help generation, while Rich handles rich terminal output with colors, tables, and spinners. Both libraries integrate seamlessly and are actively maintained.

The user has made specific decisions about command structure (flat like git), input patterns (positional args + stdin), output formatting (rich colored output with JSON mode), and confirmation flows (interactive prompts with --force bypass). These constraints guide all architectural choices.

**Primary recommendation:** Use Typer for CLI framework, Rich for terminal output, Click's File type for stdin handling, and difflib for typo suggestions. Structure as src-layout with cli/ module containing command handlers that call existing storage/llm modules.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Command structure:**
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

**Output & formatting:**
- Rich colored terminal output by default — like cargo or gh CLI
- Format flag: `--format json` (leaves room for other formats like yaml, csv later)
- Mutation feedback: always confirm success ("Added entity: [name]"), `--quiet` to suppress for scripting
- Long operations: animated spinner with status text ("Summarizing 42 entities...")
- Auto-detect TTY: colors on when terminal, off when piped — standard behavior
- Search results show: title + snippet (highlighted match) + metadata (type, created date, scope)
- `--compact` flag: one-line-per-result view for scanning large result sets
- Relationships: brief inline hints in list/search, full details with dedicated `show` command

**Flag & argument design:**
- Destructive operations (delete, compact): interactive confirmation prompt, `--force` to skip
- Entity references: accept name or ID. If name is ambiguous, prompt to choose — smart matching
- Tagging: LLM auto-categorizes entities, user can override or add tags with `--tag`
- Bulk delete: multiple args supported (`graphiti delete entity1 entity2`), confirmation before executing
- Search filters: full filter set — `--global`/`--project`, `--since 7d`/`--before DATE`, `--type entity|relationship`, `--tag`
- Summarize: both whole-graph (no args) and targeted (with topic arg)
- Compact: confirmation prompt, no dry-run — confirmation is sufficient
- Source provenance: auto-detect source by default (git commit, conversation, manual), `--source` overrides
- Auto-init on first use: first `graphiti add` in a project auto-creates `.graphiti/` — no explicit init step

**Error messages & help:**
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

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| typer | 0.15+ | CLI framework | Modern type-hint based API, auto-generates help/completion, built on Click with better DX |
| rich | 14.1+ | Terminal output | Industry standard for colored output, tables, spinners, progress bars, JSON rendering |
| click | 8.3+ | Low-level CLI | Typer's foundation, provides File type for stdin/stdout handling with `-` convention |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| difflib | stdlib | Typo suggestions | "Did you mean?" corrections for mistyped commands/options |
| sys.stdin | stdlib | TTY detection | Detect if input is piped vs interactive with `sys.stdin.isatty()` |
| pytest | 8.0+ | Testing | Test CLI with `typer.testing.CliRunner` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Typer | Click alone | Click requires more boilerplate, no type hints, but more mature stdin handling |
| Typer | argparse | Standard library (no deps), but verbose, no colors/completion built-in |
| Rich | colorama | Lighter weight but minimal features (only colors, no tables/spinners/layouts) |

**Installation:**
```bash
# Add to pyproject.toml dependencies
pip install "typer[all]>=0.15.0" "rich>=14.1.0"
```

Note: `typer[all]` includes rich, shellingham (shell detection), and other extras.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── cli/                      # NEW: CLI layer
│   ├── __init__.py          # App instance and entry point
│   ├── commands/            # Command handlers
│   │   ├── __init__.py
│   │   ├── add.py          # graphiti add
│   │   ├── search.py       # graphiti search
│   │   ├── delete.py       # graphiti delete
│   │   ├── list.py         # graphiti list
│   │   ├── summarize.py    # graphiti summarize
│   │   ├── compact.py      # graphiti compact
│   │   ├── config.py       # graphiti config
│   │   └── health.py       # graphiti health
│   ├── output.py           # Rich console wrapper, formatters
│   ├── input.py            # stdin/file input handling
│   └── utils.py            # Typo suggestions, confirmations
├── storage/                 # EXISTING: Database layer
├── llm/                     # EXISTING: LLM integration
├── config/                  # EXISTING: Configuration
├── models/                  # EXISTING: Data models
└── security/                # EXISTING: Security checks
```

**Rationale:** Separate CLI layer keeps presentation logic isolated from business logic. Commands call existing storage/llm APIs. Output module wraps Rich console for consistent formatting.

### Pattern 1: Typer App with Command Modules

**What:** Create app instance in `cli/__init__.py`, register commands from separate modules
**When to use:** All multi-command CLIs (our case)

**Example:**
```python
# src/cli/__init__.py
import typer
from .commands import add, search, delete, list_cmd, summarize, compact, config, health

app = typer.Typer(
    name="graphiti",
    help="Knowledge graph operations for global preferences and project memory",
    no_args_is_help=True,  # Show help when no command given
)

# Register commands
app.command(name="add")(add.main)
app.command(name="search")(search.main)
app.command(name="delete")(delete.main)
app.command(name="list")(list_cmd.main)
app.command(name="summarize")(summarize.main)
app.command(name="compact")(compact.main)
app.command(name="config")(config.main)
app.command(name="health")(health.main)

def cli_entry():
    """Entry point for console_scripts"""
    app()
```

### Pattern 2: Rich Console as Singleton

**What:** Single console instance shared across CLI for consistent output
**When to use:** All output operations

**Example:**
```python
# src/cli/output.py
from rich.console import Console
from rich.table import Table
from rich.json import JSON
import sys

# Singleton console with auto TTY detection
console = Console()

def print_success(message: str):
    """Print success message in green"""
    console.print(f"[green]✓[/green] {message}")

def print_error(message: str):
    """Print error message in red"""
    console.print(f"[red]✗[/red] {message}", file=sys.stderr)

def print_table(data: list[dict], title: str = None):
    """Print data as formatted table"""
    if not data:
        return

    table = Table(title=title, show_header=True)
    # Add columns from first item keys
    for key in data[0].keys():
        table.add_column(key.title(), style="cyan")

    # Add rows
    for item in data:
        table.add_row(*[str(v) for v in item.values()])

    console.print(table)

def print_json(data: dict):
    """Print data as formatted JSON"""
    console.print_json(data=data)

def is_tty() -> bool:
    """Check if output is to terminal (for color decisions)"""
    return console.is_terminal
```

### Pattern 3: stdin + Positional Argument Handling

**What:** Accept content from positional arg OR stdin, prefer positional
**When to use:** Commands that need text input (add, etc.)

**Example:**
```python
# src/cli/commands/add.py
import sys
import typer
from typing import Optional
from typing_extensions import Annotated

def main(
    content: Annotated[Optional[str], typer.Argument(help="Content to add")] = None,
    tag: Annotated[Optional[str], typer.Option("--tag", "-t")] = None,
    global_scope: Annotated[bool, typer.Option("--global", "-g")] = False,
):
    """Add content to the knowledge graph"""
    # If no positional arg, try reading from stdin
    if content is None:
        if not sys.stdin.isatty():
            # Data is piped, read it
            content = sys.stdin.read().strip()
        else:
            # No arg and no pipe = error
            typer.echo("Error: No content provided", err=True)
            typer.echo("Usage: graphiti add 'content' or echo 'content' | graphiti add", err=True)
            raise typer.Exit(2)

    # Now process content...
    from src.cli.output import console, print_success
    from src.storage import get_graph_manager

    with console.status("Adding to knowledge graph..."):
        # Call storage layer
        result = add_entity(content, tag=tag, global_scope=global_scope)

    print_success(f"Added entity: {result['name']}")
```

### Pattern 4: Confirmation Prompts with Force Flag

**What:** Require interactive confirmation for destructive ops, --force to skip
**When to use:** delete, compact commands

**Example:**
```python
# src/cli/commands/delete.py
import typer
from typing import List
from typing_extensions import Annotated

def main(
    entities: Annotated[List[str], typer.Argument(help="Entity names or IDs")],
    force: Annotated[bool, typer.Option("--force", "-f")] = False,
):
    """Delete entities from the knowledge graph"""
    if not force:
        # Show what will be deleted
        typer.echo(f"About to delete {len(entities)} entities:")
        for entity in entities:
            typer.echo(f"  - {entity}")

        # Confirm
        if not typer.confirm("Are you sure?"):
            typer.echo("Cancelled")
            raise typer.Exit(0)

    # Proceed with deletion
    from src.cli.output import console, print_success

    with console.status(f"Deleting {len(entities)} entities..."):
        # Call storage layer
        deleted = delete_entities(entities)

    print_success(f"Deleted {deleted} entities")
```

### Pattern 5: Typo Suggestions with difflib

**What:** Suggest correct command when user mistypes
**When to use:** Invalid command errors

**Example:**
```python
# src/cli/utils.py
from difflib import get_close_matches

VALID_COMMANDS = ["add", "search", "delete", "list", "summarize", "compact", "config", "health"]

def suggest_command(invalid: str, cutoff: float = 0.6) -> str | None:
    """Suggest correct command for typo

    Args:
        invalid: The mistyped command
        cutoff: Similarity threshold (0.0-1.0)

    Returns:
        Suggested command or None
    """
    matches = get_close_matches(invalid, VALID_COMMANDS, n=1, cutoff=cutoff)
    return matches[0] if matches else None

# Usage in main app error handler
def handle_unknown_command(command: str):
    suggestion = suggest_command(command)
    if suggestion:
        typer.echo(f"Error: Unknown command '{command}'", err=True)
        typer.echo(f"Did you mean '{suggestion}'?", err=True)
    else:
        typer.echo(f"Error: Unknown command '{command}'", err=True)
        typer.echo("Run 'graphiti --help' for available commands", err=True)
    raise typer.Exit(2)
```

### Pattern 6: Exit Code Conventions

**What:** Use standard POSIX exit codes
**When to use:** All error paths

**Example:**
```python
# Exit codes
EXIT_SUCCESS = 0       # Normal completion
EXIT_ERROR = 1         # Runtime error (LLM unavailable, DB error, etc.)
EXIT_BAD_ARGS = 2      # Invalid arguments/options

# In command handlers:
try:
    result = perform_operation()
    typer.Exit(EXIT_SUCCESS)  # Explicit success (Typer defaults to 0)
except ValueError as e:
    typer.echo(f"Error: {e}", err=True)
    raise typer.Exit(EXIT_BAD_ARGS)
except Exception as e:
    typer.echo(f"Error: {e}", err=True)
    raise typer.Exit(EXIT_ERROR)
```

### Anti-Patterns to Avoid

- **Mixing presentation and business logic:** Commands should call storage/llm APIs, not implement logic directly
- **Multiple Console instances:** Creates inconsistent output, use singleton pattern
- **Ignoring TTY detection:** Always respect `console.is_terminal` for color/formatting decisions
- **Using input() for file data:** Use `sys.stdin.read()` for piped input, not `input()`
- **Catching broad exceptions:** Catch specific exceptions, let unexpected errors propagate with exit code 1
- **Manual color codes:** Use Rich markup `[green]text[/green]` not ANSI codes `\033[32m`

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Argument parsing | Custom argv parser | Typer/Click | Type validation, help generation, shell completion, error messages |
| Terminal colors | ANSI escape codes | Rich | TTY detection, 16M colors, styled markup, works cross-platform |
| Progress indicators | Custom spinner with threading | Rich.status/Progress | Handles TTY detection, cleanup on interrupt, multiple spinners |
| Table formatting | String concatenation with spacing | Rich.table | Auto-width, borders, alignment, styles, overflow handling |
| Typo suggestions | Levenshtein distance from scratch | difflib.get_close_matches | Tested algorithm, handles edge cases, stdlib (no deps) |
| JSON output | json.dumps with indent | Rich.print_json() | Syntax highlighting, auto-formatting, consistent with other output |
| stdin detection | Checking sys.argv | sys.stdin.isatty() | Standard approach, handles edge cases, cross-platform |
| Confirmation prompts | input("y/n?") loops | typer.confirm() | Handles yes/no variations, integrates with testing, proper errors |

**Key insight:** CLI tools have deceptively complex edge cases. Professional libraries handle TTY detection, signal interrupts (Ctrl+C), encoding issues, terminal size changes, and cross-platform differences. Rich and Typer have solved these problems at production scale.

## Common Pitfalls

### Pitfall 1: stdin Blocks When No Data Piped
**What goes wrong:** Calling `sys.stdin.read()` when stdin is a TTY blocks waiting for user input
**Why it happens:** Developers forget to check `isatty()` before reading stdin
**How to avoid:** Always check `sys.stdin.isatty()` before attempting to read piped data
**Warning signs:** Command hangs when run without piped input
**Fix:**
```python
# WRONG - blocks on interactive terminal
content = sys.stdin.read()

# CORRECT - check first
if not sys.stdin.isatty():
    content = sys.stdin.read()
else:
    # No piped data, handle appropriately
    content = None
```

### Pitfall 2: Colors in Piped Output
**What goes wrong:** ANSI color codes appear in piped output: `cat output.txt` shows `[32mSuccess[0m`
**Why it happens:** Not respecting TTY detection, forcing colors when output is redirected
**How to avoid:** Use Rich console (auto-detects) or explicitly check `is_terminal`
**Warning signs:** CI logs show color codes, piped output has escape sequences
**Fix:**
```python
# WRONG - forces colors even when piped
console = Console(force_terminal=True)

# CORRECT - auto-detect
console = Console()  # Respects TTY by default

# Or explicit check
if console.is_terminal:
    console.print("[green]Success[/green]")
else:
    print("Success")  # Plain text when piped
```

### Pitfall 3: Inconsistent Exit Codes
**What goes wrong:** Script returns 0 on errors, breaks shell scripting with `graphiti add || fallback_action`
**Why it happens:** Forgetting to raise `typer.Exit()` with error code, letting Python exit with 0
**How to avoid:** Explicitly raise `typer.Exit(1)` or `typer.Exit(2)` on errors
**Warning signs:** Shell scripts can't detect failures, CI doesn't fail on errors
**Fix:**
```python
# WRONG - exits with 0 even on error
def main():
    try:
        do_something()
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        # Exits with 0!

# CORRECT - explicit exit code
def main():
    try:
        do_something()
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
```

### Pitfall 4: Testing Without CliRunner
**What goes wrong:** Tests run actual commands, modify real databases, can't capture output
**Why it happens:** Calling command functions directly instead of using test runner
**How to avoid:** Always use `typer.testing.CliRunner` in tests
**Warning signs:** Tests modify production data, can't assert on output, hard to test errors
**Fix:**
```python
# WRONG - calls function directly
def test_add():
    result = add.main(content="test")  # No output capture, real DB

# CORRECT - use CliRunner
from typer.testing import CliRunner

def test_add():
    runner = CliRunner()
    result = runner.invoke(app, ["add", "test"])
    assert result.exit_code == 0
    assert "Added entity" in result.output
```

### Pitfall 5: Not Handling Unicode in stdin
**What goes wrong:** `UnicodeDecodeError` when piping non-UTF8 content
**Why it happens:** stdin defaults to system encoding, may not be UTF-8
**How to avoid:** Reconfigure stdin encoding or handle decode errors
**Warning signs:** Works with ASCII, breaks with emojis/international text
**Fix:**
```python
# WRONG - assumes UTF-8
content = sys.stdin.read()

# CORRECT - handle encoding explicitly
import sys
if not sys.stdin.isatty():
    # Reconfigure stdin to UTF-8 with error handling
    sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    content = sys.stdin.read()
```

### Pitfall 6: Confirmation Prompts in CI/Scripts
**What goes wrong:** Scripts hang waiting for confirmation in non-interactive environments
**Why it happens:** `typer.confirm()` blocks when stdin is not a TTY
**How to avoid:** Always provide `--force` flag to skip confirmation
**Warning signs:** CI pipelines timeout, automation scripts hang
**Fix:**
```python
# ALWAYS provide force flag for destructive operations
force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation")

if not force:
    if not typer.confirm("Are you sure?"):
        raise typer.Exit(0)

# Usage in CI:
# graphiti delete --force entity1 entity2
```

### Pitfall 7: Long Operations Without Feedback
**What goes wrong:** User thinks command hung, hits Ctrl+C during long operation
**Why it happens:** No progress indicator for operations taking >1 second
**How to avoid:** Use `console.status()` or Progress for any operation that might take time
**Warning signs:** Users report "hanging", interrupt operations prematurely
**Fix:**
```python
# WRONG - silent long operation
result = process_large_graph()

# CORRECT - show progress
with console.status("Processing graph..."):
    result = process_large_graph()
```

## Code Examples

Verified patterns from official sources:

### Testing CLI Commands
```python
# Source: https://typer.tiangolo.com/tutorial/testing/
from typer.testing import CliRunner
from src.cli import app

runner = CliRunner()

def test_add_command():
    result = runner.invoke(app, ["add", "test content", "--tag", "test"])
    assert result.exit_code == 0
    assert "Added entity" in result.output

def test_add_from_stdin():
    # Simulate piped input
    result = runner.invoke(app, ["add"], input="piped content\n")
    assert result.exit_code == 0
    assert "Added entity" in result.output

def test_add_no_content():
    # Should fail with exit code 2 (bad args)
    result = runner.invoke(app, ["add"])
    assert result.exit_code == 2
    assert "No content provided" in result.output
```

### Entry Points in pyproject.toml
```toml
# Source: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
[project.scripts]
graphiti = "src.cli:cli_entry"
gk = "src.cli:cli_entry"  # Alias
```

### Rich Console with TTY Detection
```python
# Source: https://rich.readthedocs.io/en/stable/console.html
from rich.console import Console

console = Console()

# Auto-detects TTY
if console.is_terminal:
    console.print("[green]✓[/green] Success")
else:
    print("Success")  # Plain text when piped

# Force disable colors
console = Console(color_system=None)

# Environment variables respected:
# NO_COLOR=1 - disables colors
# FORCE_COLOR=1 - enables colors even when piped
```

### Rich Status Spinner
```python
# Source: https://rich.readthedocs.io/en/stable/console.html
from rich.console import Console

console = Console()

with console.status("Searching knowledge graph...", spinner="dots"):
    results = search_graph(query)

# Or with dynamic updates:
with console.status("Starting...") as status:
    status.update("Step 1/3: Loading...")
    load_data()
    status.update("Step 2/3: Processing...")
    process()
    status.update("Step 3/3: Saving...")
    save()
```

### Rich Table Formatting
```python
# Source: https://rich.readthedocs.io/en/stable/introduction.html
from rich.console import Console
from rich.table import Table

console = Console()

table = Table(title="Search Results", show_header=True)
table.add_column("Name", style="cyan", no_wrap=True)
table.add_column("Type", style="magenta")
table.add_column("Created", style="green")

for result in results:
    table.add_row(result.name, result.type, result.created)

console.print(table)
```

### Confirmation with Force Flag
```python
# Source: https://typer.tiangolo.com/tutorial/prompt/
import typer
from typing_extensions import Annotated

def delete(
    entities: list[str],
    force: Annotated[bool, typer.Option("--force", "-f")] = False
):
    if not force:
        if not typer.confirm(f"Delete {len(entities)} entities?"):
            typer.echo("Cancelled")
            raise typer.Exit(0)

    # Proceed with deletion
    for entity in entities:
        delete_entity(entity)

    typer.echo(f"Deleted {len(entities)} entities")
```

### Typo Suggestions with difflib
```python
# Source: https://docs.python.org/3/library/difflib.html
from difflib import get_close_matches

VALID_COMMANDS = ["add", "search", "delete", "list", "summarize", "compact", "config", "health"]

def suggest_command(invalid: str) -> str | None:
    """Suggest correct command for typo"""
    matches = get_close_matches(invalid, VALID_COMMANDS, n=1, cutoff=0.6)
    return matches[0] if matches else None

# Example: "serch" -> "search", "delte" -> "delete"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| argparse | Typer | 2019-2020 | Type hints replace decorator-heavy Click, automatic completion/validation |
| colorama | Rich | 2020-2021 | Full terminal control (tables, layouts, spinners) not just colors |
| Manual `-` handling | click.File | Always standard | Click's File type handles `-` for stdin/stdout consistently |
| setup.py | pyproject.toml | 2020+ (PEP 621) | Declarative config, no code execution during build |
| unittest | pytest | 2015-2020 | CliRunner makes testing CLIs trivial, better assertions |

**Deprecated/outdated:**
- **setup.py entry_points:** Still works but pyproject.toml `[project.scripts]` is preferred (PEP 621)
- **optparse:** Deprecated since Python 3.2, use argparse or Typer
- **Manual ANSI codes:** fragile, use Rich markup instead

## Open Questions

1. **stdin + positional arg precedence**
   - What we know: User wants both positional arg AND stdin support
   - What's unclear: If both provided (positional + piped), which wins?
   - Recommendation: Positional arg takes precedence (matches git behavior: `git commit -m "msg"` ignores stdin)

2. **JSON output with colors**
   - What we know: `--format json` needed for programmatic use
   - What's unclear: Should JSON mode disable colors entirely or use Rich's JSON rendering?
   - Recommendation: JSON mode should output plain JSON (no colors) for reliable parsing: `console = Console(force_terminal=False)`

3. **Default result limit**
   - What we know: User wants 10-20 default
   - What's unclear: Exact number
   - Recommendation: Use 15 (common middle ground, matches GitHub PR list default)

4. **Compact mode formatting**
   - What we know: `--compact` shows one-line-per-result
   - What's unclear: Exact format and which fields to show
   - Recommendation: `{name} ({type}) - {snippet[:50]}...` similar to grep output

## Sources

### Primary (HIGH confidence)
- [Typer Official Documentation](https://typer.tiangolo.com/) - Features, installation, testing patterns
- [Rich Official Documentation](https://rich.readthedocs.io/en/stable/) - Console API, tables, spinners, TTY detection
- [Click Documentation - Handling Files](https://click.palletsprojects.com/en/stable/handling-files/) - stdin/stdout patterns
- [Python Packaging User Guide - Writing pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) - Entry points configuration
- [Python difflib Documentation](https://docs.python.org/3/library/difflib.html) - Typo suggestion algorithm

### Secondary (MEDIUM confidence)
- [Typer Alternatives Comparison](https://typer.tiangolo.com/alternatives/) - Click vs Typer tradeoffs
- [Medium: Navigating the CLI Landscape](https://medium.com/@mohd_nass/navigating-the-cli-landscape-in-python-a-comparative-study-of-argparse-click-and-typer-480ebbb7172f) - Framework comparison
- [Real Python: Python Application Layouts](https://realpython.com/python-application-layouts/) - Project structure patterns
- [TheLinuxCode: Python Exit Codes](https://thelinuxcode.com/python-exit-codes/) - Exit code conventions
- [PyTutorial: Typer User Prompting Guide](https://pytutorial.com/python-typer-user-prompting-guide/) - Confirmation patterns

### Tertiary (LOW confidence - community sources)
- [GitHub: Rich Library Repository](https://github.com/Textualize/rich) - Table formatting examples
- [Medium: Practical Guide to Rich](https://medium.com/@jainsnehasj6/a-practical-guide-to-rich-12-ways-to-instantly-beautify-your-python-terminal-3a4a3434d04a) - Rich usage patterns
- [ArjanCodes: Rich Python Library](https://arjancodes.com/blog/rich-python-library-for-interactive-cli-tools/) - Advanced CLI design patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Typer and Rich are actively maintained (2026), widely adopted, official docs comprehensive
- Architecture: HIGH - Patterns verified from official docs, src-layout is Python packaging standard
- Pitfalls: HIGH - All pitfalls verified from official docs and known Python CLI gotchas
- stdin handling: MEDIUM - Click's File type fully documented, but Typer's integration less mature (issue #345)

**Research date:** 2026-02-10
**Valid until:** ~30 days (stack stable, but verify Typer release notes for stdin improvements)
