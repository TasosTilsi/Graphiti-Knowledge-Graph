# graphiti-knowledge-graph

Dual-scope knowledge graph CLI using Kuzu DB, local Ollama LLMs, and graphiti-core.

## Commands

```bash
pip install -e ".[dev]"          # install with dev deps
pip install -e ".[reranking]"    # optional BGE reranker

graphiti <cmd>                   # or: gk <cmd>
graphiti mcp serve               # start MCP server (stdio)
graphiti mcp install             # register in Claude Desktop

pytest tests/                    # run test suite
```

Config: `~/.graphiti/llm.toml`

## Architecture

```
src/
  cli/              # Typer CLI entrypoint (cli_entry)
  graph/
    adapters.py     # OllamaLLMClient, OllamaEmbedder, NoOpCrossEncoder
    service.py      # GraphService — all graph operations
  storage/
    graph_manager.py  # KuzuDriver + FTS workarounds
  llm/
    client.py       # OllamaClient with cloud/local failover
    config.py       # LLMConfig dataclass, load_config()
  mcp_server/
    tools.py        # MCP tool handlers
    toon_utils.py   # TOON encoding/decoding
  capture/
    summarizer.py   # Async conversation capture
.planning/          # GSD phase plans
```

## Code Standards

### Logging
- Use `structlog.get_logger()` everywhere **except** `src/mcp_server/`
- In `src/mcp_server/`: use standard `logging` routed to **stderr only**
- Never print to stdout in MCP server — corrupts the stdio transport
- Never call `logger.error("msg", error=e)` with stdlib logging — use structlog-style kwargs

### Async
- `run_graph_operation()` → `asyncio.run(coro)` — no retry wrapper (causes "cannot reuse awaited coroutine")
- `_get_graphiti()` is async (required for `await build_indices_and_constraints()`)
- SQLiteAckQueue: use `multithreading=True` when `ollama_chat` runs in `run_in_executor`

### LLM Config (`llm.toml`)
```toml
[cloud]
models = ["model-name"]    # cloud chat/generate

[local]
models = ["gemma2:9b"]     # local fallback

[embeddings]
models = ["nomic-embed-text"]  # always local
```

- `_is_cloud_available("embed")` always returns False (API key lacks embed access)
- Cloud calls strip `format=` kwarg — use `_inject_example()` for structural guidance instead

## Known Workarounds (graphiti-core==0.28.1)

**`src/storage/graph_manager.py`**
1. `KuzuDriver` never sets `_database` — fix: `driver._database = str(db_path)` after construction
2. `build_indices_and_constraints()` is a no-op for FTS — fix: call `_create_fts_indices()` manually using `get_fulltext_indices(GraphProvider.KUZU)`

**`src/graph/adapters.py`**
3. `EmbedderClient.create_batch()` raises `NotImplementedError` — fix: implement in `OllamaEmbedder` by looping `create()`

**Ollama SDK v0.6+**
- `local_client.list()` returns Pydantic objects: use `.models` (not `["models"]`) and `.model` (not `["name"]`)
- Tag normalization: check `model + ":latest"` if exact match fails
- Constrained generation: pass `format=response_model.model_json_schema()` — strip schema suffix first via `_strip_schema_suffix()` (~3x faster)
