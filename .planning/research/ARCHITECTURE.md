# Architecture Research

**Domain:** Multi-interface knowledge graph systems
**Researched:** 2026-02-02
**Confidence:** HIGH

## Standard Architecture

### System Overview

Multi-interface knowledge graph systems with CLI-first architecture follow a layered pattern where a core engine provides the single source of truth, with multiple interface wrappers exposing functionality through different channels.

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTERFACE LAYER                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │   CLI    │  │  Hooks   │  │   MCP    │  │   HTTP   │        │
│  │ (typer)  │  │ (git +   │  │ (stdio + │  │  API     │        │
│  │          │  │ session) │  │  HTTP)   │  │          │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │             │               │
│       └─────────────┴─────────────┴─────────────┘               │
│                          ↓                                       │
├─────────────────────────────────────────────────────────────────┤
│                      CORE ENGINE                                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Knowledge Graph Operations (Single Source of Truth)   │     │
│  │  - Add entities/relationships  - Search knowledge      │     │
│  │  - Delete/update operations    - Summarize graph       │     │
│  └────────────────────────────────────────────────────────┘     │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │ Security       │  │ Background     │  │ Graph          │    │
│  │ Filter         │  │ Queue          │  │ Selector       │    │
│  │ (pre-capture)  │  │ (async proc)   │  │ (global/proj)  │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                    PROCESSING LAYER                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  LLM Processing                          │    │
│  │  Cloud Ollama (primary) → Local Ollama (fallback)       │    │
│  └─────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────┤
│                     STORAGE LAYER                                │
│  ┌──────────────────────┐  ┌──────────────────────────────┐     │
│  │  Global Graph        │  │  Per-Project Graphs          │     │
│  │  ~/.graphiti/global/ │  │  .graphiti/ (git-safe)       │     │
│  │  (Kuzu embedded DB)  │  │  (Kuzu embedded DB)          │     │
│  └──────────────────────┘  └──────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **CLI** | Primary interface; single source of truth for operations | Python Typer with subcommands (add, search, delete, summarize) |
| **Hooks** | Git integration (post-commit) and session management | Shell scripts calling CLI commands |
| **MCP Server** | Model Context Protocol interface for AI assistants | Python MCP SDK wrapping CLI operations via subprocess/API |
| **Core Engine** | Business logic for knowledge operations | Python library with graph operations and orchestration |
| **Security Filter** | Pre-capture filtering (files, secrets, PII) | Pattern matching + entropy detection + entity sanitization |
| **Background Queue** | Non-blocking async processing | Python asyncio queue or RQ (Redis Queue) for job processing |
| **Graph Selector** | Route operations to global or project graph | Path-based detection with fallback to global |
| **LLM Processing** | Entity extraction and knowledge graph generation | Cloud Ollama API (primary) with local fallback |
| **Storage Layer** | Persistent graph storage with ACID transactions | Kuzu embedded graph database (per instance) |

## Recommended Project Structure

```
graphiti/
├── cli/                   # CLI interface (primary entry point)
│   ├── __init__.py
│   ├── main.py           # Typer app with commands
│   ├── commands/         # Subcommand implementations
│   │   ├── add.py
│   │   ├── search.py
│   │   ├── delete.py
│   │   └── summarize.py
│   └── output.py         # Output formatting (JSON, table, text)
├── core/                  # Core engine (business logic)
│   ├── __init__.py
│   ├── graph.py          # Graph operations interface
│   ├── selector.py       # Global vs project graph routing
│   ├── security/         # Security filtering
│   │   ├── file_filter.py    # File-level exclusions
│   │   ├── entity_filter.py  # Entity-level sanitization
│   │   └── patterns.py       # Secret detection patterns
│   ├── queue/            # Background processing
│   │   ├── manager.py    # Queue orchestration
│   │   ├── jobs.py       # Job definitions
│   │   └── worker.py     # Background worker
│   └── llm/              # LLM processing
│       ├── client.py     # Unified LLM client
│       ├── cloud.py      # Cloud Ollama integration
│       └── local.py      # Local Ollama fallback
├── storage/              # Storage layer
│   ├── __init__.py
│   ├── kuzu_adapter.py   # Kuzu graph database adapter
│   └── schema.py         # Graph schema definitions
├── hooks/                # Hook integrations
│   ├── git/              # Git hooks
│   │   ├── post-commit
│   │   └── install.sh
│   └── session/          # Session hooks (future)
│       └── start.sh
├── mcp/                  # MCP server interface
│   ├── __init__.py
│   ├── server.py         # MCP server implementation
│   ├── tools.py          # MCP tool definitions
│   ├── resources.py      # MCP resources
│   └── transports/       # Transport implementations
│       ├── stdio.py
│       └── http.py
└── config/               # Configuration management
    ├── __init__.py
    ├── global_config.py  # ~/.graphiti/config.toml
    └── project_config.py # .graphiti/config.toml
```

### Structure Rationale

- **cli/**: Entry point for all operations; provides the canonical interface that other wrappers call
- **core/**: Business logic is isolated from interfaces, making it testable and reusable across CLI, hooks, and MCP
- **storage/**: Kuzu adapter abstracts database details; schema defines graph structure separately from implementation
- **hooks/**: Wrapper scripts that invoke CLI commands; minimal logic to ensure maintainability
- **mcp/**: MCP server wraps core operations, not CLI (for better error handling), but CLI remains primary interface
- **config/**: Hierarchical config (global defaults, project overrides) using standard patterns

## Architectural Patterns

### Pattern 1: CLI-First with Interface Wrappers

**What:** Core functionality exposed through CLI as primary interface, with hooks and MCP as thin wrappers calling CLI operations.

**When to use:** When building multi-interface tools where consistency is critical and you want a single source of truth for operations.

**Trade-offs:**
- **Pros:** Single implementation to maintain; CLI provides excellent debugging; consistent behavior across interfaces; easier testing
- **Cons:** Slight performance overhead from subprocess calls; serialization/deserialization of data between processes; less type safety at boundaries

**Example:**
```python
# hooks/git/post-commit (shell script calling CLI)
#!/bin/bash
graphiti add --mode commit --async --project-dir "$PWD"

# mcp/tools.py (Python calling CLI via subprocess)
async def add_knowledge(content: str, mode: str = "manual"):
    result = await asyncio.create_subprocess_exec(
        "graphiti", "add",
        "--content", content,
        "--mode", mode,
        "--format", "json",  # Machine-readable output
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await result.communicate()
    return json.loads(stdout)

# Alternative: MCP wraps core library directly (better for error handling)
from graphiti.core.graph import KnowledgeGraph

async def add_knowledge(content: str, mode: str = "manual"):
    graph = KnowledgeGraph.from_context()
    return await graph.add(content, mode=mode)
```

**Recommendation:** Use direct core library calls for MCP (better error handling, type safety) but keep CLI as the canonical human interface. Hooks should call CLI (simpler, shell-based).

### Pattern 2: Graph Selector (Global vs Per-Project)

**What:** Routing layer that determines whether operations target global preferences graph or project-specific knowledge graph based on context.

**When to use:** When managing multiple knowledge domains with different scopes (user-wide vs project-specific).

**Trade-offs:**
- **Pros:** Clean separation of concerns; git-safe project graphs; global preferences apply everywhere
- **Cons:** Must handle "which graph?" decision for every operation; potential confusion if routing logic is unclear

**Example:**
```python
# core/selector.py
class GraphSelector:
    def __init__(self):
        self.global_path = Path.home() / ".graphiti" / "global"

    def select_graph(self, project_dir: Optional[Path] = None) -> Path:
        """Route to global or project graph based on context."""
        if project_dir is None:
            # No project context, use global
            return self.global_path

        project_graph = project_dir / ".graphiti"
        if project_graph.exists():
            # Project graph initialized, use it
            return project_graph

        # Fallback to global (project not initialized)
        return self.global_path

    def get_merged_context(self, project_dir: Optional[Path] = None) -> list:
        """Retrieve knowledge from both global and project graphs."""
        contexts = []

        # Always include global preferences
        global_graph = KuzuGraph(self.global_path)
        contexts.append(global_graph.search(query))

        # Add project-specific if available
        if project_dir and (project_dir / ".graphiti").exists():
            project_graph = KuzuGraph(project_dir / ".graphiti")
            contexts.append(project_graph.search(query))

        return contexts
```

### Pattern 3: Background Async Queue

**What:** Non-blocking capture system using local queue for job submission with background worker processing.

**When to use:** When operations must never block user workflow but need expensive processing (LLM calls, graph updates).

**Trade-offs:**
- **Pros:** Zero latency impact on dev work; graceful degradation if processing fails; can batch operations
- **Cons:** Eventual consistency (knowledge not immediately available); need monitoring/failure handling; additional complexity

**Example:**
```python
# core/queue/manager.py
import asyncio
from asyncio import Queue
from dataclasses import dataclass
from typing import Optional

@dataclass
class CaptureJob:
    content: str
    mode: str
    project_dir: Optional[Path]
    timestamp: float

class QueueManager:
    def __init__(self):
        self.queue = Queue()
        self.worker = None

    async def submit(self, content: str, mode: str, project_dir: Optional[Path] = None):
        """Submit job to queue (non-blocking)."""
        job = CaptureJob(
            content=content,
            mode=mode,
            project_dir=project_dir,
            timestamp=time.time()
        )
        await self.queue.put(job)

    async def start_worker(self):
        """Start background worker to process queue."""
        self.worker = asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """Background worker processing jobs."""
        while True:
            try:
                job = await self.queue.get()
                await self._process_job(job)
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                # Don't crash worker on errors

    async def _process_job(self, job: CaptureJob):
        """Process individual capture job."""
        # Filter content
        if not security_filter.is_safe(job.content):
            return

        # Extract entities via LLM
        entities = await llm_client.extract_entities(job.content)

        # Store in graph
        graph = graph_selector.select_graph(job.project_dir)
        await graph.add_entities(entities)

# Usage in CLI
queue_manager = QueueManager()
await queue_manager.submit(content, mode="conversation", project_dir=cwd)
# Returns immediately, processing happens in background
```

### Pattern 4: Security Filter Pipeline

**What:** Multi-stage filtering to prevent secrets, PII, and sensitive data from entering knowledge graphs.

**When to use:** When capturing automatic context that must be git-safe and never leak credentials.

**Trade-offs:**
- **Pros:** Defense in depth (file-level + entity-level); configurable patterns; catches secrets before storage
- **Cons:** False positives (over-filtering); maintenance burden for patterns; can't catch novel secret formats

**Example:**
```python
# core/security/file_filter.py
class FileFilter:
    """File-level exclusions."""
    DEFAULT_PATTERNS = [
        "**/.env*",
        "**/*secret*",
        "**/*credential*",
        "**/*.key",
        "**/*.pem",
        "**/config/prod*.yaml",
    ]

    def should_exclude(self, filepath: Path) -> bool:
        """Check if file should be excluded from capture."""
        for pattern in self.patterns:
            if filepath.match(pattern):
                return True
        return False

# core/security/entity_filter.py
class EntityFilter:
    """Entity-level sanitization."""

    # Pattern-based detection
    SECRET_PATTERNS = [
        r"AKIA[0-9A-Z]{16}",  # AWS access key
        r"sk-[a-zA-Z0-9]{32,}",  # OpenAI API key
        r"ghp_[a-zA-Z0-9]{36}",  # GitHub token
    ]

    # Entropy-based detection
    MIN_ENTROPY = 4.5  # High-randomness strings

    def sanitize_entity(self, text: str) -> Optional[str]:
        """Remove secrets from entity text."""
        # Pattern matching
        for pattern in self.SECRET_PATTERNS:
            if re.search(pattern, text):
                return None  # Discard entity entirely

        # Entropy detection
        if self._calculate_entropy(text) > self.MIN_ENTROPY:
            # Could be a secret
            if len(text) > 16 and not " " in text:
                return None

        return text

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy."""
        if not text:
            return 0
        entropy = 0
        for char in set(text):
            p = text.count(char) / len(text)
            entropy -= p * math.log2(p)
        return entropy

# core/security/filter.py
class SecurityFilter:
    """Orchestrate file and entity filtering."""

    def __init__(self):
        self.file_filter = FileFilter()
        self.entity_filter = EntityFilter()

    def is_safe_file(self, filepath: Path) -> bool:
        """Check if file is safe to process."""
        return not self.file_filter.should_exclude(filepath)

    def sanitize_content(self, content: str) -> Optional[str]:
        """Sanitize content, return None if unsafe."""
        return self.entity_filter.sanitize_entity(content)
```

### Pattern 5: Embedded Graph Database per Scope

**What:** Separate Kuzu embedded database instances for global and each project, providing isolation and git-safety.

**When to use:** When different knowledge domains require separate persistence with different sharing/security properties.

**Trade-offs:**
- **Pros:** Complete isolation; project graphs are git-committable; no cross-contamination; simple backup
- **Cons:** Can't easily query across graphs; duplication if same knowledge in multiple projects; multiple database instances

**Example:**
```python
# storage/kuzu_adapter.py
import kuzu

class KuzuGraph:
    """Adapter for Kuzu embedded graph database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.db = kuzu.Database(str(db_path))
        self.conn = kuzu.Connection(self.db)
        self._init_schema()

    def _init_schema(self):
        """Initialize graph schema."""
        # Create node tables
        self.conn.execute("""
            CREATE NODE TABLE IF NOT EXISTS Entity(
                id STRING PRIMARY KEY,
                type STRING,
                content STRING,
                created_at TIMESTAMP,
                last_accessed TIMESTAMP,
                access_count INT64
            )
        """)

        self.conn.execute("""
            CREATE NODE TABLE IF NOT EXISTS Concept(
                id STRING PRIMARY KEY,
                name STRING,
                embedding FLOAT[768]
            )
        """)

        # Create relationship tables
        self.conn.execute("""
            CREATE REL TABLE IF NOT EXISTS RELATES_TO(
                FROM Entity TO Entity,
                relationship_type STRING,
                confidence FLOAT
            )
        """)

    async def add_entity(self, entity_id: str, entity_type: str, content: str):
        """Add entity to graph."""
        self.conn.execute("""
            CREATE (:Entity {
                id: $id,
                type: $type,
                content: $content,
                created_at: timestamp(),
                last_accessed: timestamp(),
                access_count: 0
            })
        """, parameters={"id": entity_id, "type": entity_type, "content": content})

    async def search(self, query: str, embedding: list[float]) -> list:
        """Search graph using semantic similarity."""
        # Vector search using Kuzu's built-in vector indexing
        results = self.conn.execute("""
            MATCH (c:Concept)
            WHERE array_cosine_similarity(c.embedding, $embedding) > 0.7
            MATCH (c)-[:RELATES_TO]->(e:Entity)
            RETURN e.content, e.type, c.name
            ORDER BY array_cosine_similarity(c.embedding, $embedding) DESC
            LIMIT 10
        """, parameters={"embedding": embedding})

        return results.get_as_df().to_dict('records')

    async def prune_unused(self, days: int = 90):
        """Remove entities not accessed in N days."""
        self.conn.execute("""
            MATCH (e:Entity)
            WHERE e.last_accessed < timestamp() - interval($days DAY)
              AND e.access_count < 3
            DELETE e
        """, parameters={"days": days})
```

### Pattern 6: LLM Client with Graceful Fallback

**What:** Unified LLM client that tries cloud Ollama first, falls back to local Ollama if quota exhausted or unavailable.

**When to use:** When you want cost-efficiency (free tier) but need reliability (local fallback).

**Trade-offs:**
- **Pros:** Cost-efficient; always available; transparent to callers; can tune quality vs speed
- **Cons:** Inconsistent latency; different model capabilities; quota management complexity

**Example:**
```python
# core/llm/client.py
class LLMClient:
    """Unified LLM client with cloud-first, local-fallback strategy."""

    def __init__(self):
        self.cloud = CloudOllamaClient()
        self.local = LocalOllamaClient()
        self.quota_exhausted = False

    async def extract_entities(self, content: str) -> dict:
        """Extract entities using LLM, with fallback."""
        try:
            if not self.quota_exhausted:
                # Try cloud first (free tier)
                return await self.cloud.extract_entities(content)
        except QuotaExhausted:
            self.quota_exhausted = True
            logger.warning("Cloud quota exhausted, falling back to local")
        except NetworkError as e:
            logger.warning(f"Cloud unreachable: {e}, using local")

        # Fallback to local Ollama
        return await self.local.extract_entities(content)

# core/llm/cloud.py
class CloudOllamaClient:
    """Cloud Ollama integration (free tier)."""

    def __init__(self):
        self.base_url = "https://ollama.ai/api"  # Example
        self.model = "gemma2:9b"

    async def extract_entities(self, content: str) -> dict:
        """Extract entities via cloud LLM."""
        response = await self._call_api(
            prompt=f"Extract entities from: {content}",
            temperature=0.1,
            max_tokens=500
        )
        return self._parse_entities(response)

# core/llm/local.py
class LocalOllamaClient:
    """Local Ollama fallback."""

    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.model = "llama3.2:3b"  # Faster, lower quality

    async def extract_entities(self, content: str) -> dict:
        """Extract entities via local LLM."""
        response = await self._call_api(
            prompt=f"Extract entities from: {content}",
            temperature=0.1
        )
        return self._parse_entities(response)
```

## Data Flow

### Request Flow: Manual Add Operation

```
User: graphiti add --content "Use pytest for testing"
    ↓
[CLI] Parse arguments, validate input
    ↓
[Core Engine] Determine target graph (global vs project)
    ↓
[Security Filter] Check content safety (no secrets/PII)
    ↓ (if async flag)
[Background Queue] Submit job to queue → returns immediately
    ↓ (background worker)
[LLM Processing] Extract entities (Cloud Ollama → Local fallback)
    ↓
[Storage Layer] Store entities/relationships in Kuzu graph
    ↓
[CLI] Output success message
```

### Request Flow: Automatic Capture (Git Hook)

```
Git Event: post-commit hook triggered
    ↓
[Hook] Call CLI: graphiti add --mode commit --async
    ↓
[CLI] Parse commit message and diff
    ↓
[Core Engine] Select project graph (.graphiti/)
    ↓
[Security Filter]
    ├─ File-level: Skip .env*, *secret*, etc.
    └─ Entity-level: Detect and remove secrets/high-entropy strings
    ↓
[Background Queue] Submit job (non-blocking, hook returns immediately)
    ↓ (background worker)
[LLM Processing] Extract architectural decisions and patterns
    ↓
[Storage Layer] Store in project graph
    ↓
[Smart Retention] Update access timestamps for relevant entities
```

### Request Flow: MCP Search Operation

```
AI Assistant (Claude): Needs context about project architecture
    ↓
[MCP Client] Call tools/call with "search_knowledge" tool
    ↓
[MCP Server] Receive request via stdio/HTTP transport
    ↓
[Core Engine] Determine context (global + project if available)
    ↓
[Storage Layer]
    ├─ Query global graph for user preferences
    └─ Query project graph for project-specific knowledge
    ↓
[Core Engine] Merge and rank results by relevance
    ↓
[MCP Server] Format as MCP resource response
    ↓
[AI Assistant] Use context for informed responses
```

### Background Processing Flow

```
[Background Worker] Loop waiting for jobs
    ↓
[Queue] Pop next job
    ↓
[Security Filter] Final safety check
    ↓
[LLM Processing]
    ├─ Try Cloud Ollama (free tier)
    │   ├─ Success → Continue
    │   └─ Quota/Network Error → Fallback to Local
    └─ Local Ollama (CPU-only, slower but reliable)
    ↓
[Storage Layer]
    ├─ Add new entities/relationships
    ├─ Update existing entity access timestamps
    └─ ACID transaction (all-or-nothing)
    ↓
[Smart Retention] (periodic)
    └─ Prune entities unused for 90+ days with <3 accesses
```

### Key Data Flows

1. **Synchronous operations (CLI manual add, MCP search):** Direct flow through core → storage, returns result immediately
2. **Asynchronous operations (git hooks, conversation capture):** Submit to queue, return immediately, background processing
3. **Multi-graph context (MCP search):** Query both global and project graphs, merge results, rank by relevance
4. **Graceful degradation (LLM calls):** Cloud Ollama → Local Ollama → Return error (never crash)

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-10 projects | Embedded Kuzu per project works perfectly; global graph stays small (<10k entities) |
| 10-100 projects | Consider project graph archival (compress unused projects); background worker may need rate limiting on LLM calls |
| 100+ projects | May need shared Kuzu instance for global; consider removing graph data from very old projects |

### Scaling Priorities

1. **First bottleneck: LLM API rate limits**
   - **What breaks:** Cloud Ollama quota exhausted frequently, local Ollama queue backs up
   - **Fix:** Implement smarter capture (less frequent, only on meaningful changes), batch entity extraction, tune to extract fewer entities

2. **Second bottleneck: Background queue processing time**
   - **What breaks:** Queue grows faster than worker can process, delays in knowledge availability
   - **Fix:** Add multiple background workers (careful with LLM rate limits), prioritize jobs (commits > conversations), implement job expiration

3. **Third bottleneck: Graph query performance**
   - **What breaks:** Searches slow down as graphs grow (>100k entities)
   - **Fix:** Kuzu's built-in indexing helps, but consider graph compaction (merge similar entities), prune more aggressively, add caching layer for common queries

**Non-bottlenecks (unlikely to be issues):**
- Kuzu storage size: Graph databases are compact, even 100k entities ~= few hundred MB
- Disk I/O: Kuzu's columnar storage optimized for reads, embedded = no network overhead
- CPU: LLM processing is bottleneck, not graph operations; Kuzu is highly optimized
- Memory: Kuzu efficient with memory, unlikely to exhaust 32GB RAM on reasonable graph sizes

## Anti-Patterns

### Anti-Pattern 1: Bypassing CLI for Core Operations

**What people do:** Other interfaces (MCP, hooks) directly import and call core library instead of going through CLI.

**Why it's wrong:** Creates multiple paths to same functionality, leading to inconsistent behavior, divergent implementations, and difficult debugging. CLI stops being the source of truth.

**Do this instead:**
- For hooks: Always call CLI via subprocess (shell scripts)
- For MCP: Can use core library directly (better error handling) BUT keep CLI as canonical human interface
- Never duplicate logic in multiple interfaces

**Correct approach:**
```python
# GOOD: Hook calls CLI
# hooks/git/post-commit
#!/bin/bash
graphiti add --mode commit --async

# ACCEPTABLE: MCP calls core library (for error handling)
# mcp/tools.py
from graphiti.core.graph import KnowledgeGraph
async def add_knowledge(content: str):
    graph = KnowledgeGraph.from_context()
    return await graph.add(content)

# BAD: MCP reimplements logic
# mcp/tools.py
async def add_knowledge(content: str):
    # Custom entity extraction here (diverges from CLI)
    entities = custom_extract(content)
    # Direct storage access (bypasses security filter)
    graph.store(entities)
```

### Anti-Pattern 2: Synchronous Capture in Git Hooks

**What people do:** Git hooks call `graphiti add` without `--async` flag, waiting for LLM processing to complete.

**Why it's wrong:** Blocks git commits for 2-10 seconds while waiting for LLM, terrible UX. Users will disable hooks or abandon tool.

**Do this instead:** Always use `--async` flag in hooks; submit to background queue and return immediately. User never waits.

**Correct approach:**
```bash
# BAD: Blocks commit
graphiti add --mode commit  # Waits for LLM

# GOOD: Non-blocking
graphiti add --mode commit --async  # Returns immediately
```

### Anti-Pattern 3: Shared Mutable State Across Graph Instances

**What people do:** Create singleton or module-level Kuzu connection shared across global and project graphs.

**Why it's wrong:** Kuzu embedded instances are per-database; sharing connections causes data corruption, transaction conflicts, and debugging nightmares.

**Do this instead:** Each graph scope (global, each project) gets its own Kuzu instance. Use GraphSelector to route operations.

**Correct approach:**
```python
# BAD: Shared connection
_kuzu_conn = None  # Module-level singleton
def get_graph():
    global _kuzu_conn
    if _kuzu_conn is None:
        _kuzu_conn = kuzu.Connection(...)
    return _kuzu_conn

# GOOD: Per-scope instances
class KuzuGraph:
    def __init__(self, db_path: Path):
        self.db = kuzu.Database(str(db_path))  # Separate instance
        self.conn = kuzu.Connection(self.db)

# Usage
global_graph = KuzuGraph(Path.home() / ".graphiti" / "global")
project_graph = KuzuGraph(Path.cwd() / ".graphiti")
```

### Anti-Pattern 4: Filtering Only at File Level

**What people do:** Implement file exclusions (skip .env files) but skip entity-level sanitization, assuming file filtering is sufficient.

**Why it's wrong:** Secrets leak into graphs from allowed files (e.g., test files with hardcoded tokens, commits with pasted API keys). Git history contains sensitive data in unexpected places.

**Do this instead:** Defense in depth: file-level AND entity-level filtering. Both are necessary.

**Correct approach:**
```python
# BAD: Only file filtering
if not file_filter.should_exclude(filepath):
    content = read_file(filepath)
    graph.add(content)  # No entity-level sanitization

# GOOD: Both file and entity filtering
if not file_filter.should_exclude(filepath):
    content = read_file(filepath)
    sanitized = entity_filter.sanitize_content(content)
    if sanitized:  # None if secrets detected
        graph.add(sanitized)
```

### Anti-Pattern 5: Coupling MCP Transport to Business Logic

**What people do:** Write MCP server with stdio-specific assumptions embedded throughout, making HTTP transport difficult to add later.

**Why it's wrong:** Violates separation of concerns; transport is orthogonal to business logic. Makes testing hard and alternative transports impossible.

**Do this instead:** Abstract transport layer; core MCP server logic is transport-agnostic. Use transport adapters.

**Correct approach:**
```python
# BAD: Transport coupled to logic
class MCPServer:
    def __init__(self, stdio_reader, stdio_writer):
        self.reader = stdio_reader  # Assumes stdio
        self.writer = stdio_writer

    async def handle_tool_call(self, request):
        result = await self.process_tool(request)
        # Writes directly to stdio
        await self.writer.write(json.dumps(result))

# GOOD: Transport abstraction
class MCPServer:
    """Transport-agnostic MCP server."""
    async def handle_tool_call(self, request: dict) -> dict:
        # Pure business logic, returns dict
        return await self.process_tool(request)

class StdioTransport:
    """Stdio transport adapter."""
    def __init__(self, server: MCPServer):
        self.server = server

    async def run(self, reader, writer):
        async for request in self._read_requests(reader):
            response = await self.server.handle_tool_call(request)
            await writer.write(json.dumps(response))

class HTTPTransport:
    """HTTP transport adapter."""
    def __init__(self, server: MCPServer):
        self.server = server

    async def handle_request(self, request):
        mcp_request = self._parse_http_request(request)
        response = await self.server.handle_tool_call(mcp_request)
        return self._format_http_response(response)
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Cloud Ollama | HTTP REST API with retry + quota tracking | Free tier limits; need quota management and graceful fallback |
| Local Ollama | HTTP REST API via localhost:11434 | Assumes Ollama running locally; handle connection refused gracefully |
| Git | Shell script hooks in .git/hooks/ or via Githooks manager | post-commit for capture; must be non-blocking (--async) |
| MCP Clients | JSON-RPC 2.0 via stdio or HTTP transports | Claude Desktop (stdio), generic clients (HTTP); need transport abstraction |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI ↔ Core | Direct Python function calls | CLI is thin layer over core; validates args, formats output |
| Hooks ↔ CLI | Subprocess execution | Shell scripts call CLI commands; simple, maintainable |
| MCP ↔ Core | Direct Python function calls | Better error handling than subprocess; skip CLI serialization overhead |
| Core ↔ Storage | Adapter pattern (KuzuGraph interface) | Isolates Kuzu details; easier to test, could swap storage later |
| Core ↔ LLM | Async HTTP client with fallback strategy | Try cloud, fall back to local; unified interface hides complexity |
| Core ↔ Queue | asyncio.Queue for job submission | Non-blocking submission; background worker processes asynchronously |

## Build Order Implications

Suggested implementation order based on dependencies:

### Phase 1: Storage Foundation
**Why first:** Everything depends on persistent storage; need to migrate from in-memory to Kuzu.
- Implement Kuzu adapter with schema
- Test basic graph operations (add, search, delete)
- Verify embedded architecture works with separate instances

### Phase 2: Core Engine
**Why second:** Business logic layer that all interfaces will use.
- Graph selector (global vs project routing)
- Core operations (add, search, delete, summarize)
- LLM client with cloud/local fallback
- Security filter (file + entity level)

### Phase 3: CLI Interface
**Why third:** Primary interface; needed before building wrappers.
- Typer CLI with subcommands
- Output formatting (JSON, table, text)
- Config management (global + project)
- Integration with core engine

### Phase 4: Background Queue
**Why fourth:** Required for non-blocking hooks; can be added incrementally to CLI.
- asyncio queue implementation
- Background worker
- Job definitions
- Integration with CLI (--async flag)

### Phase 5: Git Hooks
**Why fifth:** Depends on CLI and background queue.
- post-commit hook implementation
- Hook installation script
- Test non-blocking behavior

### Phase 6: MCP Server
**Why last:** Wrapper around core; can be built after CLI is stable.
- MCP server using Python SDK
- Tool definitions (add, search, delete, summarize)
- Transport implementations (stdio, HTTP)
- Resource definitions (context retrieval)

**Rationale:** Bottom-up approach ensures each layer has solid foundation. Storage → Core → CLI → Queue → Hooks → MCP matches dependency graph.

## Sources

**CLI Architecture & Patterns:**
- [Command Line Interface Guidelines](https://clig.dev/) - CLI design principles for human-first interfaces
- [Tailor Gemini CLI to your workflow with hooks](https://developers.googleblog.com/tailor-gemini-cli-to-your-workflow-with-hooks/) - 2026 CLI hooks patterns
- [Unix Interface Design Patterns](https://homepage.cs.uri.edu/~thenry/resources/unix_art/ch11s06.html) - Separation of engine from interface
- [Designing and Architecting the Confluent CLI](https://www.confluent.io/blog/how-we-designed-and-architected-the-confluent-cli/) - Multi-backend unified CLI experience

**Knowledge Graph Architecture:**
- [GraphRAG & Knowledge Graphs: Making Your Data AI-Ready for 2026](https://flur.ee/fluree-blog/graphrag-knowledge-graphs-making-your-data-ai-ready-for-2026/) - Modern KG architecture patterns
- [Kuzu GitHub Repository](https://github.com/kuzudb/kuzu) - Embedded graph database architecture
- [Building Production-Ready Graph Systems in 2025](https://medium.com/@claudiubranzan/from-llms-to-knowledge-graphs-building-production-ready-graph-systems-in-2025-2b4aff1ec99a) - MEDIUM confidence

**MCP Architecture:**
- [MCP Architecture Overview](https://modelcontextprotocol.io/docs/learn/architecture) - Official MCP protocol architecture (HIGH confidence)
- [MCP Server Best Practices for 2026](https://www.cdata.com/blog/mcp-server-best-practices-2026) - Security and OAuth 2.1 patterns
- [Building Scalable MCP Servers with Domain-Driven Design](https://medium.com/@chris.p.hughes10/building-scalable-mcp-servers-with-domain-driven-design-fb9454d4c726) - DDD patterns for MCP

**Background Processing:**
- [Python asyncio Queues Documentation](https://docs.python.org/3/library/asyncio-queue.html) - Official asyncio queue patterns (HIGH confidence)
- [Taskiq: Distributed task queue with async support](https://github.com/taskiq-python/taskiq) - Modern async queue library
- [RQ: Simple job queues for Python](https://python-rq.org/) - Redis-backed job processing (HIGH confidence)

**Security & Filtering:**
- [Yelp detect-secrets](https://github.com/Yelp/detect-secrets) - Enterprise secrets detection patterns
- [Bandit: Python security scanner](https://www.helpnetsecurity.com/2026/01/21/bandit-open-source-tool-find-security-issues-python-code/) - 2026 Python security tool
- [Pydantic Validation Layers](https://johal.in/pydantic-validation-layers-secure-python-ml-input-sanitization-2025/) - Multi-layer sanitization patterns (MEDIUM confidence)
- [Top 8 Git Secrets Scanners in 2026](https://www.jit.io/resources/appsec-tools/git-secrets-scanners-key-features-and-top-tools-) - Secret detection tools comparison

**Architecture Patterns:**
- [Layered Architecture in Software Design](https://www.sayonetech.com/blog/software-architecture-patterns/) - 2026 architecture patterns overview
- [The 2026 Guide to AI Agent Architecture Components](https://procreator.design/blog/guide-to-ai-agent-architecture-components/) - Modern agent architecture patterns
- [Google's Multi-Agent Design Patterns](https://www.infoq.com/news/2026/01/multi-agent-design-patterns/) - Microservices-style agent architecture

**Configuration Management:**
- [A Design Pattern for Configuration Management in Python](https://www.hackerearth.com/practice/notes/samarthbhargav/a-design-pattern-for-configuration-management-in-python/) - Python config patterns
- [Best Practices for Working with Configuration in Python](https://tech.preferred.jp/en/blog/working-with-configuration-in-python/) - Hierarchical config patterns (MEDIUM confidence)

---
*Architecture research for: Multi-interface knowledge graph systems*
*Researched: 2026-02-02*
*Confidence: HIGH (verified with official docs and 2026 sources)*
