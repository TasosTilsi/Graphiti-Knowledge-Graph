# Technology Stack Research

**Project:** Graphiti Knowledge Graph with CLI/Hooks/MCP Integration
**Researched:** 2026-02-02
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.10+ | Runtime environment | Required by graphiti-core, MCP SDK, and modern async features. 3.10 minimum for structural pattern matching and better type hints. |
| **Kuzu** | 0.11.3 | Graph database | Embeddable, serverless architecture. Native vector search and full-text search. Cypher query language. Columnar storage with excellent performance. Pre-installed extensions (algo, fts, json, vector). |
| **Graphiti Core** | 0.26.3 | Knowledge graph framework | Temporally-aware knowledge graphs with bi-temporal model. Real-time incremental updates. Supports Kuzu backend. Built for AI agents. |
| **MCP SDK** | 1.26.0 | Protocol implementation | Official Anthropic SDK. Stable v1.x for production. Provides stdio and HTTP transports. Well-documented standard for LLM integration. |
| **Ollama** | 0.6.1 | LLM client | Official Python client with async support. Local and cloud hybrid support. Streaming responses. Model management built-in. |
| **Typer** | 0.21.1 | CLI framework | Modern type-hint-based CLI. Built on Click but with better DX. Auto-completion and --help generation. Rich formatting included by default. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pre-commit** | 4.5.1 | Git hooks framework | Essential for automated git capture. Multi-language hook support. Standard in Python ecosystem. Use for all git-triggered actions. |
| **aiojobs** | 1.4.0 | Async task scheduler | Background processing for non-blocking operations. Graceful shutdown support. Use for conversation capture and git processing. |
| **watchdog** | 6.0.0 | File system monitoring | Cross-platform file change detection. Use for local file-based triggers if needed (secondary to git hooks). |
| **pydantic-settings** | 2.12.0 | Configuration management | Type-safe settings with validation. .env file support. Twelve-factor app compliant. Use for all configuration (Ollama endpoints, quotas, etc.). |
| **python-dotenv** | 1.2.1 | Environment variables | Load .env files into environment. Simple integration with pydantic-settings. Use for local development config. |
| **httpx** | latest | HTTP client | Already required by Ollama client. Async support built-in. Use for cloud Ollama API calls. |
| **rich** | latest | Terminal formatting | Already included with Typer. Beautiful CLI output. Progress bars for long operations. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **pytest** | Testing framework | Standard Python testing. Async test support via pytest-asyncio. |
| **pytest-asyncio** | Async test support | Required for testing async components (MCP server, Ollama client, aiojobs). |
| **black** | Code formatter | PEP8 compliance. Use as pre-commit hook. |
| **ruff** | Linter | Fast modern linter replacing flake8. Use as pre-commit hook. |
| **mypy** | Type checker | Static type checking for Python 3.10+ features. Use as pre-commit hook. |

## Installation

```bash
# Core dependencies
pip install kuzu==0.11.3 \
    graphiti-core==0.26.3 \
    "mcp[cli]==1.26.0" \
    ollama==0.6.1 \
    typer[all]==0.21.1

# Configuration and environment
pip install pydantic-settings==2.12.0 \
    python-dotenv==1.2.1

# Async and background processing
pip install aiojobs==1.4.0 \
    httpx

# Git hooks
pip install pre-commit==4.5.1

# Optional: File monitoring (if needed beyond git hooks)
pip install watchdog==6.0.0

# Dev dependencies
pip install -D pytest \
    pytest-asyncio \
    black \
    ruff \
    mypy
```

## Alternatives Considered

| Category | Recommended | Alternative | When to Use Alternative |
|----------|-------------|-------------|-------------------------|
| **Graph DB** | Kuzu | Neo4j | If you need multi-node clustering or have existing Neo4j infrastructure. Requires separate server process. |
| **Graph DB** | Kuzu | FalkorDB | If Redis ecosystem alignment is important. Less mature than Kuzu. |
| **CLI Framework** | Typer | Click | If you have existing Click codebase or need more low-level control. Typer builds on Click. |
| **CLI Framework** | Typer | argparse | Never. argparse is standard library but inferior DX. |
| **Task Queue** | aiojobs | Celery | If you need distributed task processing across multiple machines. Requires Redis/RabbitMQ. Overkill for local processing. |
| **Task Queue** | aiojobs | asyncio.Queue | If tasks are very simple and don't need lifecycle management. aiojobs provides better control. |
| **MCP SDK** | Official (mcp) | FastMCP | If you want simpler API and faster development. FastMCP is unofficial but more Pythonic. Trade stability for convenience. |
| **Config Management** | pydantic-settings | dynaconf | If you need multi-environment config with complex hierarchies. More overhead than needed for this project. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **In-memory storage** | Data loss on restart. Already identified as limitation in existing implementation. | Kuzu with persistent database file. |
| **Synchronous Ollama calls** | Blocks CLI and git hooks. Poor UX for large operations. | AsyncClient with aiojobs for background processing. |
| **Environment variables for secrets in git** | Project knowledge graphs must be git-safe. Secrets would leak. | pydantic-settings with validation. Use .env files (gitignored) for local secrets. Separate project graph from secrets. |
| **argparse** | Verbose boilerplate. Poor auto-completion support. Outdated patterns. | Typer with type hints. |
| **Hardcoded Ollama endpoints** | Can't switch between cloud/local. No quota management. | pydantic-settings with BaseSettings for endpoint configuration. |
| **GitPython for hooks** | Slower than native git hooks. Additional dependency. | pre-commit framework with shell hooks or Python hooks. |
| **Manual .gitignore management** | Error-prone for sensitive data. | pre-commit hook to validate no secrets in project graphs. |
| **Simple queue (asyncio.Queue)** | No shutdown management. No task lifecycle tracking. | aiojobs.Scheduler for proper background task management. |

## Stack Patterns by Variant

**CLI-first architecture:**
- CLI commands are primary interface
- MCP server wraps CLI via subprocess calls
- Rationale: Single source of truth. MCP just provides protocol translation.

**Async everywhere:**
- All I/O operations use async/await
- Ollama client uses AsyncClient
- Kuzu queries may be CPU-bound but wrapped in async context
- Rationale: Never block CLI or git hooks. User experience is paramount.

**Hybrid Ollama (cloud + local):**
- pydantic-settings manages endpoint list with priorities
- Cloud Ollama (free tier) as primary
- Local Ollama as fallback
- Quota tracking in Kuzu database
- Rationale: Maximize free tier, graceful degradation.

**Git-safe knowledge graphs:**
- Project-specific graphs stored in repo (gitignored patterns for secrets)
- Automatic .gitignore validation in pre-commit
- Sensitive data detection before commit
- Rationale: Enable team sharing without security risks.

## Architecture Integration Points

### CLI → MCP Flow
```python
# CLI command (typer)
@app.command()
async def add_knowledge(text: str):
    # Process with Kuzu + Graphiti
    # Return immediately or queue for background

# MCP server wraps CLI
async def handle_mcp_tool_call(name: str, args: dict):
    # Invoke CLI command
    result = await asyncio.create_subprocess_exec(
        "kgraph", "add-knowledge", args["text"]
    )
```

### Git Hook → Background Processing Flow
```python
# pre-commit hook (shell)
#!/bin/bash
kgraph capture-commit --async

# CLI queues background job
@app.command()
async def capture_commit(async_mode: bool = True):
    if async_mode:
        # Queue in aiojobs
        await scheduler.spawn(process_commit())
    else:
        # Synchronous for testing
        await process_commit()
```

### Ollama Hybrid Flow
```python
class OllamaManager(BaseSettings):
    endpoints: list[str] = [
        "https://cloud.ollama.ai",
        "http://localhost:11434"
    ]
    quota_limit: int = 1000  # requests per day

    async def generate(self, prompt: str):
        for endpoint in self.endpoints:
            if await self.check_quota(endpoint):
                try:
                    return await self.call_endpoint(endpoint, prompt)
                except Exception:
                    continue  # fallback to next
        raise QuotaExceededError()
```

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| graphiti-core 0.26.3 | Kuzu 0.11.2+ | Graphiti explicitly supports Kuzu 0.11.2. Version 0.11.3 is compatible (patch version). |
| graphiti-core 0.26.3 | Python 3.10-3.13 | Requires Python <4, >=3.10 |
| MCP SDK 1.26.0 | Python 3.10-3.13 | Stable v1.x series. v2 coming Q1 2026 but not required. |
| Typer 0.21.1 | Python 3.9+ | We're on 3.10+ so fully compatible. |
| Ollama 0.6.1 | Python 3.8+ | Uses httpx for transport. |
| pre-commit 4.5.1 | Python 3.10+ | Perfect match for our baseline. |
| aiojobs 1.4.0 | Python 3.9+ | Production/Stable status. |
| pydantic-settings 2.12.0 | Python 3.8+ | Mature, production-ready. |

## Critical Constraint: CPU-Only

**Hardware:** Intel i7-13620H, 32GB RAM, no GPU

**Implications:**
- Ollama models must be CPU-optimized
- Use smaller models (mistral:7b not mistral:70b)
- Embedding models: nomic-embed-text (CPU-friendly)
- Kuzu performance is excellent on CPU (columnar storage)
- Avoid GPU-dependent libraries

**Recommended Ollama models:**
- LLM: `mistral:7b-instruct` or `phi3:mini`
- Embeddings: `nomic-embed-text`
- Why: These run efficiently on CPU with 32GB RAM

## Quota Management Strategy

Store in Kuzu database:
```cypher
CREATE NODE TABLE OllamaEndpoint(
    url STRING,
    quota_limit INT64,
    quota_used INT64,
    reset_date TIMESTAMP,
    PRIMARY KEY (url)
)

CREATE NODE TABLE RequestLog(
    endpoint_url STRING,
    timestamp TIMESTAMP,
    tokens_used INT64,
    model STRING,
    PRIMARY KEY (timestamp)
)

CREATE REL TABLE LOGGED_TO(
    FROM RequestLog TO OllamaEndpoint
)
```

## Sources

**Official Package Documentation (HIGH confidence):**
- [Kuzu PyPI](https://pypi.org/project/kuzu/) - Version 0.11.3
- [Kuzu Docs](https://kuzudb.github.io/docs/tutorials/) - Getting started guide
- [Graphiti Core PyPI](https://pypi.org/project/graphiti-core/) - Version 0.26.3
- [MCP Python SDK PyPI](https://pypi.org/project/mcp/) - Version 1.26.0
- [Typer PyPI](https://pypi.org/project/typer/) - Version 0.21.1
- [Ollama Python PyPI](https://pypi.org/project/ollama/) - Version 0.6.1
- [pre-commit PyPI](https://pypi.org/project/pre-commit/) - Version 4.5.1
- [aiojobs PyPI](https://pypi.org/project/aiojobs/) - Version 1.4.0
- [watchdog PyPI](https://pypi.org/project/watchdog/) - Version 6.0.0
- [pydantic-settings PyPI](https://pypi.org/project/pydantic-settings/) - Version 2.12.0
- [python-dotenv PyPI](https://pypi.org/project/python-dotenv/) - Version 1.2.1

**Architecture and Best Practices (MEDIUM-HIGH confidence):**
- [Typer Documentation](https://typer.tiangolo.com/) - CLI framework guidance
- [MCP Documentation](https://modelcontextprotocol.io/docs/develop/build-server) - Server implementation patterns
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) - Configuration best practices
- [pre-commit Documentation](https://pre-commit.com/) - Git hooks framework
- [GitHub: graphiti](https://github.com/getzep/graphiti) - Knowledge graph implementation

**Comparative Analysis (MEDIUM confidence):**
- [Click vs Typer comparison](https://typer.tiangolo.com/alternatives/) - Framework decision rationale
- [Python task queues overview](https://www.fullstackpython.com/task-queues.html) - Background processing options
- [Python secrets management 2026](https://blog.gitguardian.com/how-to-handle-secrets-in-python/) - Security best practices

---
*Stack research for: Knowledge Graph System with CLI/Hooks/MCP Integration*
*Researched: 2026-02-02*
*Confidence: HIGH for core stack, MEDIUM for integration patterns*
