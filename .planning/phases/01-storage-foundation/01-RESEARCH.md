# Phase 1: Storage Foundation - Research

**Researched:** 2026-02-02
**Domain:** Embedded Graph Database (Kuzu) + Knowledge Graph Framework (Graphiti)
**Confidence:** MEDIUM

## Summary

This phase replaces in-memory dictionary storage with persistent Kuzu embedded graph database, implementing dual-scope storage (global preferences at `~/.graphiti/global/` and per-project graphs at `.graphiti/`). Kuzu 0.11.3 is an embedded, CPU-optimized graph database that provides ACID transactions, native vector search for embeddings, and Cypher query language. Graphiti 0.26.3 is a temporal knowledge graph framework with native Kuzu backend support via `KuzuDriver`.

The standard approach is to instantiate separate Kuzu `Database` objects for global and project scopes, each with their own database directory. A graph selector/router determines which database instance to use based on operation context (checking for project root via `.git` presence). Graphiti's `KuzuDriver` handles schema initialization automatically, creating node types (Episodic, Entity, Community) and relationship types (RELATES_TO, MENTIONS, HAS_MEMBER) with bi-temporal tracking (created_at/expired_at for database time, valid_at/invalid_at for real-world time).

Critical findings: Kuzu is CPU-optimized (SIMD vectorization, morsel-driven parallelism) making it ideal for the Intel i7-13620H hardware. The embedded nature means no network overhead, but requires careful connection lifecycle management. Kuzu allows only one write transaction at a time (multiple concurrent reads allowed). The project was archived October 2025 but v0.11.3 remains stable and fully functional.

**Primary recommendation:** Use Graphiti's KuzuDriver abstraction rather than raw Kuzu connections to leverage automatic schema management and Graphiti's temporal model. Implement a graph selector that lazy-loads database instances and maintains them as singletons per scope to avoid connection overhead.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| kuzu | 0.11.3 | Embedded graph database with Cypher queries, vector search, ACID transactions | CPU-optimized, serverless architecture, excellent performance (5-188x faster than Neo4j on analytical queries), native vector storage for embeddings |
| graphiti-core[kuzu] | 0.26.3 | Temporal knowledge graph framework with Kuzu backend support | Provides schema management, bi-temporal data model, automatic entity/relationship extraction, direct Kuzu integration via KuzuDriver |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | Path manipulation for database directories | Always use for cross-platform path handling (~/.graphiti/global/, .graphiti/) |
| asyncio | stdlib | Async connection handling | Graphiti uses async patterns, KuzuDriver provides AsyncConnection |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw Kuzu connections | Direct kuzu.Database + kuzu.Connection | More control but lose Graphiti's schema management, temporal model, and entity extraction. Don't do this - Graphiti's abstraction is worth it |
| Neo4j backend | graphiti-core[neo4j] | More mature but requires separate server process, higher memory overhead, overkill for local-first tool |

**Installation:**
```bash
pip install kuzu==0.11.3
pip install graphiti-core[kuzu]==0.26.3
```

## Architecture Patterns

### Recommended Project Structure
```
graphiti-knowledge-graph/
├── src/
│   ├── storage/              # Storage layer
│   │   ├── __init__.py
│   │   ├── graph_manager.py  # Dual-scope manager
│   │   ├── kuzu_store.py     # Kuzu database wrapper
│   │   └── selector.py       # Context-based routing
│   ├── config/               # Configuration
│   │   └── paths.py          # Path constants
│   └── models/               # Data models
│       └── context.py        # GraphContext enum (GLOBAL, PROJECT)
├── ~/.graphiti/              # User data (created at runtime)
│   └── global/               # Global scope database
│       └── graphiti.kuzu/    # Kuzu database files
└── .graphiti/                # Project scope database (gitignored)
    └── graphiti.kuzu/        # Kuzu database files
```

### Pattern 1: Dual-Instance Singleton Manager
**What:** Single `GraphManager` class maintains two separate Kuzu database instances (global and project), lazy-loading them on first access. Each database instance is a singleton per scope to avoid connection overhead.

**When to use:** Always - this is the core architecture pattern for dual-scope storage.

**Example:**
```python
# Source: Synthesized from Graphiti KuzuDriver pattern + dual-scope requirements
from graphiti_core import Graphiti
from graphiti_core.driver.kuzu_driver import KuzuDriver
from pathlib import Path
from enum import Enum
from typing import Optional

class GraphScope(Enum):
    GLOBAL = "global"
    PROJECT = "project"

class GraphManager:
    """Manages dual-scope Kuzu database instances"""

    def __init__(self):
        self._global_driver: Optional[KuzuDriver] = None
        self._project_driver: Optional[KuzuDriver] = None
        self._global_graphiti: Optional[Graphiti] = None
        self._project_graphiti: Optional[Graphiti] = None

    def get_driver(self, scope: GraphScope, project_root: Optional[Path] = None) -> KuzuDriver:
        """Get or create KuzuDriver for the specified scope"""
        if scope == GraphScope.GLOBAL:
            if self._global_driver is None:
                db_path = Path.home() / ".graphiti" / "global" / "graphiti.kuzu"
                db_path.parent.mkdir(parents=True, exist_ok=True)
                self._global_driver = KuzuDriver(db=str(db_path))
            return self._global_driver
        else:  # PROJECT
            if project_root is None:
                raise ValueError("project_root required for PROJECT scope")
            if self._project_driver is None:
                db_path = project_root / ".graphiti" / "graphiti.kuzu"
                db_path.parent.mkdir(parents=True, exist_ok=True)
                self._project_driver = KuzuDriver(db=str(db_path))
            return self._project_driver

    def get_graphiti(self, scope: GraphScope, project_root: Optional[Path] = None) -> Graphiti:
        """Get or create Graphiti instance for the specified scope"""
        driver = self.get_driver(scope, project_root)

        if scope == GraphScope.GLOBAL:
            if self._global_graphiti is None:
                self._global_graphiti = Graphiti(
                    graph_driver=driver,
                    # LLM and embedder config here
                )
            return self._global_graphiti
        else:
            if self._project_graphiti is None:
                self._project_graphiti = Graphiti(
                    graph_driver=driver,
                    # LLM and embedder config here
                )
            return self._project_graphiti

    def close_all(self):
        """Close all database connections"""
        # Note: KuzuDriver.close() relies on GC, but explicit cleanup is good practice
        if self._global_driver:
            self._global_driver.close()
        if self._project_driver:
            self._project_driver.close()
```

### Pattern 2: Context-Based Graph Selection
**What:** Determine which graph scope (global vs project) to use based on current working directory and operation type. Preferences are always global, project-specific knowledge uses project graph if available, falls back to global.

**When to use:** Every knowledge graph operation must route through this selector.

**Example:**
```python
# Source: Synthesized from dual-scope requirements
from pathlib import Path
from typing import Optional

class GraphSelector:
    """Selects appropriate graph scope based on context"""

    @staticmethod
    def find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
        """Find project root by looking for .git directory"""
        current = start_path or Path.cwd()

        # Walk up directory tree looking for .git
        for parent in [current, *current.parents]:
            if (parent / ".git").exists():
                return parent

        return None

    @staticmethod
    def determine_scope(
        operation_type: str,
        prefer_project: bool = True,
        start_path: Optional[Path] = None
    ) -> tuple[GraphScope, Optional[Path]]:
        """Determine which graph scope to use

        Args:
            operation_type: Type of operation (e.g., 'preference', 'project_knowledge')
            prefer_project: Whether to prefer project scope when available
            start_path: Starting path for project detection (defaults to cwd)

        Returns:
            Tuple of (scope, project_root_path)
        """
        # Preferences always use global scope
        if operation_type == "preference":
            return (GraphScope.GLOBAL, None)

        # Check if we're in a project
        project_root = GraphSelector.find_project_root(start_path)

        if project_root and prefer_project:
            return (GraphScope.PROJECT, project_root)
        else:
            return (GraphScope.GLOBAL, None)

# Usage example
selector = GraphSelector()
manager = GraphManager()

# Determine scope
scope, project_root = selector.determine_scope("project_knowledge")

# Get appropriate Graphiti instance
graphiti = manager.get_graphiti(scope, project_root)

# Now use graphiti.add_episode(), graphiti.search(), etc.
```

### Pattern 3: Schema Initialization via KuzuDriver
**What:** Let Graphiti's KuzuDriver handle all schema setup automatically. The driver creates node tables (Episodic, Entity, Community, RelatesToNode_) and relationship tables (RELATES_TO, MENTIONS, HAS_MEMBER) with proper indexes on first connection.

**When to use:** Always use KuzuDriver, never manually create schema. Schema is initialized automatically in `KuzuDriver.__init__()`.

**Example:**
```python
# Source: Graphiti KuzuDriver implementation
# https://github.com/getzep/graphiti/blob/main/graphiti_core/driver/kuzu_driver.py

# This happens automatically when you create KuzuDriver:
driver = KuzuDriver(db="/path/to/graphiti.kuzu")

# Schema is already created with these node types:
# - Episodic: uuid, name, content, created_at, valid_at, invalid_at, source_description
# - Entity: uuid, name, group_id, labels, created_at, summary, attributes, name_embedding
# - Community: uuid, name, created_at, summary, name_embedding
# - RelatesToNode_: uuid, fact, fact_embedding, created_at, expired_at, valid_at, invalid_at

# And these relationship types:
# - RELATES_TO: Entity -> Entity (the main knowledge graph edges)
# - MENTIONS: Episodic -> Entity (episodes mentioning entities)
# - HAS_MEMBER: Community -> Entity (community membership)

# Vector indexes are automatically created on embedding fields
```

### Pattern 4: Bi-Temporal Data Model
**What:** Graphiti tracks two time dimensions: database time (when facts were added/removed from system) and real-world time (when events actually occurred). Every edge has created_at, expired_at (database time) and optional valid_at, invalid_at (real-world time).

**When to use:** Leverage this for historical queries and understanding when knowledge changed vs when events happened.

**Example:**
```python
# Source: Graphiti temporal model documentation
# https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types

# When adding episodes, Graphiti extracts temporal information:
await graphiti.add_episode(
    name="career_change",
    content="Sarah started working at TechCorp on January 3, 2024 as a Senior Engineer",
    reference_time=datetime(2024, 1, 15)  # When this info was learned
)

# This creates an edge with:
# - created_at: 2024-01-15 (when added to database)
# - expired_at: None (still current)
# - valid_at: 2024-01-03 (when Sarah actually started)
# - invalid_at: None (relationship is ongoing)

# Later, if Sarah changes jobs:
await graphiti.add_episode(
    name="new_position",
    content="Sarah left TechCorp and joined CloudCo on June 1, 2024",
    reference_time=datetime(2024, 6, 5)
)

# Graphiti automatically updates the old edge:
# - expired_at: 2024-06-05 (relationship no longer current in database)
# - invalid_at: 2024-06-01 (when relationship actually ended)

# Point-in-time queries can now accurately query "What was Sarah's job on April 1?"
```

### Anti-Patterns to Avoid
- **Multiple Database objects to same path:** Only create one `kuzu.Database` object per database path. Multiple Database objects to the same path will cause concurrency issues. Use the singleton pattern per scope.
- **Ignoring connection lifecycle:** While KuzuDriver relies on GC for cleanup, long-running processes should explicitly call `close()` to release resources when switching projects.
- **Manual schema creation:** Don't write custom CREATE TABLE statements. Graphiti's schema is specifically designed for its temporal model and entity extraction. Manual changes will break Graphiti's assumptions.
- **Blocking operations in main thread:** Kuzu operations can be I/O intensive. Use Graphiti's async API (KuzuDriver provides AsyncConnection) to avoid blocking.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph schema for knowledge graphs | Custom node/edge tables in Kuzu | Graphiti's KuzuDriver schema | Graphiti's schema includes bi-temporal tracking, embedding indexes, full-text search on relationship facts, and community detection structures. Getting this right is complex. |
| Entity extraction from text | Custom NER + relationship parsing | Graphiti's `add_episode()` method | Graphiti uses LLMs to extract entities, relationships, and temporal information from natural language. This involves prompt engineering, structured output parsing, and handling ambiguity - already solved. |
| Vector similarity search | Custom cosine similarity on embeddings | Kuzu's built-in HNSW vector index | Kuzu includes optimized vector search with `CREATE VECTOR INDEX` and similarity queries. HNSW index provides log(n) search performance vs linear scan. |
| Database path resolution | Manual path joining | pathlib.Path for cross-platform paths | Handles Windows/Unix differences, tilde expansion, path normalization automatically. |
| Temporal queries | Custom filtering by timestamps | Graphiti's built-in temporal query support | Graphiti provides methods for point-in-time queries considering both database time and real-world time. Complex logic around expired_at, valid_at, invalid_at. |

**Key insight:** Embedded databases seem simple ("just open a file") but connection lifecycle, concurrency, schema management, and cleanup are subtle. Graphiti's KuzuDriver abstraction handles these complexities correctly. Don't bypass it to save a few lines of code.

## Common Pitfalls

### Pitfall 1: Concurrent Write Transactions
**What goes wrong:** Multiple threads attempt to write to the same Kuzu database simultaneously, causing transaction conflicts or deadlocks.

**Why it happens:** Kuzu allows only one write transaction at a time (though multiple concurrent reads are fine). Python's async/await can mask this if not careful.

**How to avoid:**
- Use a single `GraphManager` instance with singleton database instances per scope
- Graphiti's async API queues operations properly, but if mixing raw Kuzu queries, use a write lock
- All connections must come from the same `Database` object (Graphiti's KuzuDriver handles this)

**Warning signs:** Timeouts on write operations, "transaction conflict" errors, operations that succeed individually but fail when concurrent.

### Pitfall 2: Database Migration Without Rollback
**What goes wrong:** IMPORT DATABASE or schema changes fail partway through, leaving database in inconsistent state with no automatic rollback.

**Why it happens:** Kuzu's IMPORT DATABASE command has no automatic rollback on failure. If import fails, database is left in partially-imported state.

**How to avoid:**
- Always backup database directory before migration
- Use empty database for IMPORT DATABASE (it only works on empty databases)
- Test migration on copy of production data first
- For schema changes, create new database and migrate data rather than altering existing schema

**Warning signs:** Import fails with cryptic errors, database can't be opened after failed migration, missing indexes after import.

### Pitfall 3: In-Memory Mode Data Loss
**What goes wrong:** Database initialized with `:memory:` or empty string loses all data when process ends or connection closes.

**Why it happens:** In-memory mode is intended for testing - no WAL, no disk persistence.

**How to avoid:**
- Always specify explicit database path for production: `KuzuDriver(db="/path/to/graphiti.kuzu")`
- Never use `:memory:` outside of unit tests
- Validate paths at startup - create directories if they don't exist

**Warning signs:** Data disappears after restart, "fresh" database on every launch, mysteriously empty query results after known adds.

### Pitfall 4: Path Resolution in Cross-Platform Code
**What goes wrong:** Hardcoded paths like `~/.graphiti/global/` work on Linux/Mac but fail on Windows, or tilde expansion doesn't happen.

**Why it happens:** Path conventions differ across platforms. Python's `~` expansion only works with `os.path.expanduser()` or `Path.home()`.

**How to avoid:**
- Use `pathlib.Path.home()` for user directory: `Path.home() / ".graphiti" / "global"`
- Use `Path.cwd()` for current directory
- Use `Path.mkdir(parents=True, exist_ok=True)` to create directories safely
- Store paths as Path objects, convert to str only when passing to Kuzu

**Warning signs:** "File not found" errors on Windows, paths containing literal `~` character, backslash/forward slash issues.

### Pitfall 5: Stale Connection After Project Switch
**What goes wrong:** User changes directories from one project to another, but GraphManager still holds connection to old project's database, resulting in knowledge being saved to wrong graph.

**Why it happens:** GraphManager singleton maintains project database connection based on first project detected. Doesn't detect when user changes directories.

**How to avoid:**
- Detect project root on every operation (it's cheap - just stat calls up directory tree)
- Compare current project root to cached project root; if different, close old connection and create new one
- Implement `GraphManager.reset_project()` method called when project context changes

**Warning signs:** Knowledge appearing in wrong project's graph, "I told you this already" but graph is empty, cross-project knowledge contamination.

### Pitfall 6: Not Handling Missing Project Root
**What goes wrong:** Code tries to create project-scope database but user is not in a git repository (no `.git` directory found), causing path errors or fallback to global incorrectly.

**Why it happens:** Not all operations happen inside a project. User might be in home directory, /tmp, or a non-git directory.

**How to avoid:**
- GraphSelector.find_project_root() should return None if no project found
- Caller must handle None case explicitly - decide whether to fall back to global or error
- For project-specific operations (like commit hooks), error if no project found
- For general knowledge, fall back to global scope gracefully

**Warning signs:** Crash with "NoneType has no attribute 'mkdir'", knowledge saved to weird locations, inability to use tool outside of projects.

## Code Examples

Verified patterns from official sources:

### Initialize KuzuDriver and Graphiti
```python
# Source: Graphiti PyPI documentation
# https://pypi.org/project/graphiti-core/
from graphiti_core import Graphiti
from graphiti_core.driver.kuzu_driver import KuzuDriver
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from pathlib import Path

# Initialize database driver
db_path = Path.home() / ".graphiti" / "global" / "graphiti.kuzu"
db_path.parent.mkdir(parents=True, exist_ok=True)
driver = KuzuDriver(db=str(db_path))

# Initialize LLM client (using Ollama with OpenAI-compatible API)
llm_config = LLMConfig(
    api_key="ollama",
    model="gemma2:9b",
    base_url="http://localhost:11434/v1"
)
llm_client = OpenAIClient(config=llm_config)

# Initialize embedder
embedder_config = OpenAIEmbedderConfig(
    api_key="ollama",
    embedding_model="nomic-embed-text",
    embedding_dim=768,
    base_url="http://localhost:11434/v1"
)
embedder = OpenAIEmbedder(config=embedder_config)

# Create Graphiti instance
graphiti = Graphiti(
    graph_driver=driver,
    llm_client=llm_client,
    embedder=embedder
)
```

### Add Knowledge Episode
```python
# Source: Graphiti usage pattern
# Episodes are the primary way to add knowledge to the graph
from datetime import datetime

# Add a knowledge episode - Graphiti extracts entities and relationships
await graphiti.add_episode(
    name="project_tech_stack",
    content="The graphiti-knowledge-graph project uses Python 3.12, Kuzu 0.11.3 for graph storage, and Graphiti 0.26.3 for knowledge graph management. The database is stored at ~/.graphiti/global/ for user preferences and .graphiti/ for project-specific knowledge.",
    reference_time=datetime.now()
)

# Graphiti automatically:
# 1. Extracts entities (Python, Kuzu, Graphiti, etc.)
# 2. Identifies relationships (project "uses" Python, etc.)
# 3. Creates/updates Entity nodes
# 4. Creates RELATES_TO edges with temporal metadata
# 5. Generates embeddings for entities and facts
# 6. Creates Episodic node with MENTIONS edges to entities
```

### Search Knowledge Graph
```python
# Source: Graphiti search API
# Semantic search using embeddings

# Search for relevant context
results = await graphiti.search(
    query="What database does this project use?",
    num_results=5
)

# Results include entities and edges ranked by relevance
for entity_edge in results:
    if hasattr(entity_edge, 'name'):  # Entity
        print(f"Entity: {entity_edge.name} - {entity_edge.summary}")
    else:  # Edge
        print(f"Relationship: {entity_edge.fact}")
```

### Project Root Detection
```python
# Source: Synthesized from requirements
from pathlib import Path
from typing import Optional

def find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find project root by looking for .git directory

    Args:
        start_path: Starting directory (defaults to current working directory)

    Returns:
        Path to project root if found, None otherwise
    """
    current = start_path or Path.cwd()

    # Walk up directory tree
    for parent in [current, *current.parents]:
        git_dir = parent / ".git"
        if git_dir.exists() and git_dir.is_dir():
            return parent

    return None

# Usage
project_root = find_project_root()
if project_root:
    print(f"Project root: {project_root}")
    # Use project-scope database
else:
    print("Not in a project, using global scope")
    # Use global-scope database
```

### Kuzu Connection Lifecycle
```python
# Source: Kuzu documentation (concurrency page)
# https://docs.kuzudb.com/concurrency/
import kuzu

# Create database object (singleton per database path)
db = kuzu.Database("/path/to/graphiti.kuzu")

# Create multiple connections from same Database object (thread-safe)
conn1 = kuzu.Connection(db)
conn2 = kuzu.Connection(db)

# Multiple connections can read concurrently
result1 = conn1.execute("MATCH (n:Entity) RETURN count(n)")
result2 = conn2.execute("MATCH (n:Community) RETURN count(n)")

# Only one write at a time (others will wait)
conn1.execute("CREATE (n:Entity {uuid: 'test'})")  # Acquires write lock
# conn2 write would wait here until conn1 commit/rollback

# CRITICAL: All connections must come from SAME Database object
# This is WRONG and unsafe:
# db1 = kuzu.Database("/path/to/db")
# db2 = kuzu.Database("/path/to/db")  # Different object to same path - BAD!
```

### Async Usage with KuzuDriver
```python
# Source: Graphiti KuzuDriver uses AsyncConnection
# All Graphiti operations are async

import asyncio
from graphiti_core import Graphiti
from graphiti_core.driver.kuzu_driver import KuzuDriver

async def main():
    # KuzuDriver creates AsyncConnection internally
    driver = KuzuDriver(db="./graphiti.kuzu")
    graphiti = Graphiti(graph_driver=driver)

    # All operations are async
    await graphiti.add_episode(
        name="async_example",
        content="This is an async operation",
    )

    results = await graphiti.search("async operation")

    # Close driver when done (relies on GC but explicit is better)
    driver.close()

# Run async function
asyncio.run(main())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| In-memory dictionary storage | Persistent Kuzu embedded database | Phase 1 (current) | Data persists across restarts, supports graph queries and traversal, vector similarity search for embeddings |
| Single global knowledge store | Dual-scope (global + per-project) | Phase 1 (current) | Preferences separated from project knowledge, project knowledge is git-committable, no cross-project interference |
| Manual entity/relationship extraction | Graphiti LLM-based extraction | Using Graphiti from start | Natural language input instead of structured data, automatic entity recognition, relationship inference |
| Synchronous operations | Async/await with AsyncConnection | Using Graphiti from start | Non-blocking operations, better for long-running graph updates |

**Deprecated/outdated:**
- **Kuzu documentation site (docs.kuzudb.com):** Domain is down. Use GitHub Pages documentation at kuzudb.github.io/docs/ or PyPI package documentation.
- **Kuzu extension server:** Project archived October 2025, official extension server no longer available. v0.11.3 includes four common extensions (algo, fts, json, vector) built-in. If you need additional extensions, must set up local extension server.
- **Neo4j as primary backend:** While Graphiti still supports Neo4j, Kuzu is now the recommended embedded option for local-first applications. Neo4j requires separate server process.

## Open Questions

Things that couldn't be fully resolved:

1. **Kuzu concurrency with AsyncConnection**
   - What we know: Kuzu allows one write transaction, multiple reads. KuzuDriver uses AsyncConnection with max_concurrent_queries parameter.
   - What's unclear: How AsyncConnection handles write queueing internally. Does it queue async writes or raise errors on conflict?
   - Recommendation: Test concurrent writes in implementation. May need application-level write queue if AsyncConnection doesn't handle it.

2. **Graph switching performance overhead**
   - What we know: Creating new Database object requires opening files, loading metadata. Connection creation is lightweight.
   - What's unclear: Actual latency cost when user switches projects. Is lazy-loading sufficient or do we need connection pool/keep-alive?
   - Recommendation: Measure in implementation. If switching is slow (>100ms), implement connection pool with LRU eviction. If fast (<50ms), simple singleton per scope is fine.

3. **Project root detection edge cases**
   - What we know: Looking for .git directory works for most cases. Git submodules have .git file (not directory) pointing to parent.
   - What's unclear: Should we detect submodules and use parent repository root, or treat submodule as separate project?
   - Recommendation: Start with simple .git directory detection. Add submodule support in Phase 2 if users request it. Can check if .git is file vs directory.

4. **Kuzu database file format stability**
   - What we know: Kuzu project is archived (October 2025), v0.11.3 is last release. IMPORT/EXPORT DATABASE available for migration between versions.
   - What's unclear: Will v0.11.3 database format remain readable indefinitely, or could Python/OS updates break compatibility?
   - Recommendation: Implement backup/export functionality early. Consider periodic export to human-readable format (JSON/Cypher) for long-term archival.

5. **Embedding dimension mismatch handling**
   - What we know: Graphiti stores embeddings in Entity.name_embedding and RelatesToNode_.fact_embedding. Embedding dimension must be consistent (nomic-embed-text uses 768).
   - What's unclear: What happens if user switches embedding models with different dimensions? Will queries fail or silently return wrong results?
   - Recommendation: Store embedding model name and dimension in database metadata. Validate on startup. If mismatch, either re-embed all entities or error and require migration.

## Sources

### Primary (HIGH confidence)
- [Kuzu PyPI package](https://pypi.org/project/kuzu/) - Installation, version, Python support (v0.11.3, archived October 2025)
- [Graphiti-core PyPI package](https://pypi.org/project/graphiti-core/) - Installation with Kuzu extras, version 0.26.3, configuration examples
- [Graphiti KuzuDriver implementation](https://github.com/getzep/graphiti/blob/main/graphiti_core/driver/kuzu_driver.py) - Schema setup, connection lifecycle, AsyncConnection usage
- [Kuzu concurrency documentation](https://docs.kuzudb.com/concurrency/) - Thread safety, connection handling, transaction limitations
- [Kuzu transaction documentation](https://docs.kuzudb.com/cypher/transaction/) - ACID compliance, transaction statements
- [Kuzu migration documentation](https://docs.kuzudb.com/migrate/) - IMPORT DATABASE, rollback limitations, empty database requirement

### Secondary (MEDIUM confidence)
- [The Data Quarry: Kuzu embedded database analysis](https://thedataquarry.com/blog/embedded-db-2/) - Performance benchmarks (5-188x faster than Neo4j), CPU optimization details (SIMD, morsel-driven parallelism)
- [Graphiti temporal model documentation](https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types) - Bi-temporal fields (created_at, expired_at, valid_at, invalid_at)
- [Graphiti knowledge graph model](https://deepwiki.com/getzep/graphiti/3.1-knowledge-graph-model) - Node types (Episodic, Entity, Community), relationship types
- [Zep: Temporal Knowledge Graph Architecture (arXiv)](https://arxiv.org/html/2501.13956v1) - Graphiti architecture paper, bi-temporal data model formalization

### Tertiary (LOW confidence)
- [GitHub: kuzudb/kuzu repository](https://github.com/kuzudb/kuzu) - General overview, archived status (WebSearch + WebFetch, project is read-only)
- [Kuzu vector search](https://docs.kuzudb.com/extensions/vector/) - Vector index creation, HNSW index syntax (documentation site unreachable, information from search results)
- Community blog posts and tutorials - WebSearch results for patterns and pitfalls (not directly verified)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PyPI package documentation and official repository confirm versions, features, and installation
- Architecture: MEDIUM - Synthesized from Graphiti's KuzuDriver implementation and project requirements. Core patterns verified from source code, but dual-instance manager is custom design (not pre-existing pattern in Graphiti)
- Pitfalls: MEDIUM - Concurrency and migration issues documented in official Kuzu docs. Connection lifecycle and path resolution pitfalls are general best practices not specific to Kuzu.

**Research date:** 2026-02-02
**Valid until:** 30 days (March 4, 2026) - Kuzu is archived so no new releases expected. Graphiti is actively developed but breaking changes unlikely in patch versions. Re-verify if Graphiti releases major version update.
