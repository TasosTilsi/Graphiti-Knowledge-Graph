---
phase: 03-llm-integration
plan: 01
status: complete
subsystem: llm-config
tags: [configuration, toml, dependencies, ollama]

requires:
  - phases: [01-storage-foundation, 02-security-filtering]
    reason: Foundation established, security patterns available

provides:
  - LLMConfig dataclass with frozen immutability
  - load_config() function with TOML + env var override support
  - Extensive configuration template with WHY/WHEN documentation
  - LLM dependencies (ollama, tenacity, persist-queue)

affects:
  - 03-02: Cloud client depends on LLMConfig
  - 03-03: Local client depends on LLMConfig
  - 03-04: Unified client depends on LLMConfig
  - 03-05: Async queue depends on queue configuration

tech-stack:
  added:
    - ollama==0.6.1: Official Ollama Python client
    - tenacity==9.1.2: Retry logic with decorators
    - persist-queue==1.1.0: SQLite-backed persistent queue
    - httpx>=0.28.0: HTTP client with granular timeout control
  patterns:
    - frozen-dataclass: Immutable configuration via dataclass(frozen=True)
    - toml-config: TOML-based configuration with tomllib
    - env-override: Environment variable priority pattern
    - state-persistence: JSON state files in ~/.graphiti/

key-files:
  created:
    - src/llm/__init__.py: Module exports
    - src/llm/config.py: LLMConfig dataclass and load_config()
    - config/llm.toml: Default configuration template
  modified:
    - pyproject.toml: Added LLM dependencies

decisions:
  - id: llm-config-frozen-dataclass
    decision: Use frozen dataclass for LLMConfig
    rationale: Immutability prevents accidental modification, type safety via dataclass
    alternative: Pydantic BaseModel (too heavy for simple config)
    affects: [03-02, 03-03, 03-04]

  - id: llm-config-toml-format
    decision: TOML configuration format
    rationale: Python 3.11+ stdlib support, human-readable, type-safe parsing
    alternative: YAML (requires extra dependency), JSON (less human-friendly)
    affects: All configuration management

  - id: llm-config-env-priority
    decision: Environment variables override TOML
    rationale: Security best practice (never commit API keys), 12-factor app pattern
    alternative: TOML-only (would expose secrets in version control)
    affects: [03-02]

  - id: llm-config-extensive-docs
    decision: WHY/WHEN/GOTCHA documentation for every option
    rationale: Per CONTEXT.md requirement - users need to understand trade-offs
    alternative: Minimal comments (would require reading source code)
    affects: User configuration experience

metrics:
  duration: 3 minutes
  completed: 2026-02-05

requirements-completed: [R5.1, R5.2, R5.3]
---

# Phase 3 Plan 01: LLM Configuration Foundation Summary

**One-liner:** TOML-based LLM configuration with env var overrides, frozen dataclass, and extensive WHY/WHEN documentation for 14 configurable options.

## What Was Built

Created the configuration foundation for all LLM operations:

1. **Dependencies**: Added ollama (0.6.1), tenacity (9.1.2), persist-queue (1.1.0), and httpx to pyproject.toml
2. **LLMConfig dataclass**: Frozen dataclass with 14 configuration fields (cloud/local endpoints, retry, timeout, quota, queue)
3. **load_config() function**: TOML parser with environment variable overrides (priority: env > TOML > defaults)
4. **Configuration template**: 152-line config/llm.toml with extensive documentation (14 WHY + 14 WHEN TO CHANGE comments)

## Architecture

**Configuration Loading Pattern:**

```
Environment Variables (highest priority)
    ↓
~/.graphiti/llm.toml (user overrides)
    ↓
Hardcoded defaults in LLMConfig (fallback)
    ↓
Frozen LLMConfig instance (immutable)
```

**Key Design Decisions:**

- **Frozen dataclass**: `dataclass(frozen=True)` prevents accidental modification after load
- **TOML format**: Python 3.11+ stdlib tomllib support, no extra dependencies
- **Environment overrides**: OLLAMA_API_KEY, OLLAMA_CLOUD_ENDPOINT, OLLAMA_LOCAL_ENDPOINT
- **State persistence**: `~/.graphiti/llm_state.json` for cooldown tracking (see get_state_path())

## Configuration Fields

All 14 fields from CONTEXT.md decisions:

| Field                          | Default              | Purpose                               |
| ------------------------------ | -------------------- | ------------------------------------- |
| cloud_endpoint                 | https://ollama.com   | Cloud Ollama API URL                  |
| cloud_api_key                  | None                 | API key (from env var)                |
| local_endpoint                 | localhost:11434      | Local Ollama server                   |
| local_auto_start               | False                | Auto-start local server (disabled)    |
| local_models                   | [gemma2:9b, llama3.2:3b] | Fallback model chain         |
| embeddings_model               | nomic-embed-text     | Embedding model                       |
| retry_max_attempts             | 3                    | 1 initial + 2 retries                 |
| retry_delay_seconds            | 10                   | Fixed delay (not exponential)         |
| request_timeout_seconds        | 90                   | Per-request timeout                   |
| quota_warning_threshold        | 0.8                  | Warn at 80% quota                     |
| rate_limit_cooldown_seconds    | 600                  | 10 min cooldown (429 only)            |
| failover_logging               | True                 | Log every failover                    |
| queue_max_size                 | 1000                 | Bounded queue                         |
| queue_item_ttl_hours           | 24                   | Skip stale items                      |

## Documentation Quality

Configuration template provides three levels of documentation per option:

1. **WHAT**: What the option controls
2. **WHY**: Why the default was chosen
3. **WHEN TO CHANGE**: When/why you might change it
4. **GOTCHA**: Common pitfalls or relationships (where applicable)

Example:
```toml
# WHAT: Maximum number of retry attempts (includes initial attempt)
# WHY: 3 attempts = 1 initial + 2 retries balances reliability vs latency
# WHEN TO CHANGE: Increase for flaky networks, decrease for faster failure feedback
# GOTCHA: Total time = max_attempts × (request_timeout + delay)
max_attempts = 3
```

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Blockers:** None

**Concerns:** None

**Ready for:**
- **03-02 (Cloud Client)**: LLMConfig provides cloud_endpoint, cloud_api_key, retry settings
- **03-03 (Local Client)**: LLMConfig provides local_endpoint, local_models, timeout settings
- **03-04 (Unified Client)**: LLMConfig provides failover and quota settings
- **03-05 (Async Queue)**: LLMConfig provides queue_max_size, queue_item_ttl_hours

## Verification

All verification checks passed:

- ✓ `pip install -e .` installs all dependencies
- ✓ `import ollama; import tenacity; from persistqueue import SQLiteAckQueue` succeeds
- ✓ `from src.llm import LLMConfig, load_config` succeeds
- ✓ `load_config()` returns LLMConfig with defaults when no file exists
- ✓ `config/llm.toml` parses as valid TOML
- ✓ Every option has WHY and WHEN-TO-CHANGE documentation (14 each)
- ✓ Configuration template includes priority explanation
- ✓ rate_limit_cooldown_seconds comment clarifies 429-only behavior

## Commits

| Task | Commit  | Message                                      |
| ---- | ------- | -------------------------------------------- |
| 1    | c64948b | chore(03-01): add LLM dependencies           |
| 2    | 085c6de | feat(03-01): create LLM configuration module |
| 3    | 063d5f6 | docs(03-01): create default LLM config template |

## Knowledge for Future Sessions

**Configuration pattern established:**

- TOML files in `config/` for templates
- User configs in `~/.graphiti/` (per Path.home() pattern from Phase 1)
- Frozen dataclasses for immutable configuration
- Environment variables for secrets (never commit API keys)

**Documentation standard:**

- Every configurable option needs WHY/WHEN/GOTCHA docs
- Not just WHAT it does - explain trade-offs and decision context
- This pattern should apply to all future configuration modules

**Dependencies now available:**

- `ollama` client for LLM API calls
- `tenacity` for retry decorators
- `persist-queue` for SQLite-backed queues
- `httpx` for granular timeout control (used by ollama)

**State persistence pattern:**

- `get_state_path()` returns `~/.graphiti/llm_state.json`
- This pattern (state files in ~/.graphiti/) can be reused for other state tracking
