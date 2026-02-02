# Feature Research

**Domain:** Knowledge Graph Developer Tools (CLI + Hooks + MCP)
**Researched:** 2026-02-02
**Confidence:** MEDIUM-HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Add/Store Knowledge** | Core CRUD - users must be able to put data in | LOW | Already exists. Enhanced version: entity + observation model |
| **Search/Retrieve** | Useless without retrieval - users need to find what they stored | MEDIUM | Already exists. Needs semantic search upgrade |
| **List/Browse** | Users want to see what's stored without searching | LOW | Basic listing exists. Needs filtering by type/category |
| **Delete/Forget** | Users must be able to remove incorrect or stale knowledge | LOW | Marked as needed (KG-14). Single entity and bulk delete |
| **Entity + Relations** | Knowledge graphs are about connections, not just documents | MEDIUM | Graphiti supports this. Need better API exposure |
| **Persistence** | Memory must survive restarts | MEDIUM | Current: in-memory. Moving to Kuzu (KG-02) |
| **Configuration** | Users need to customize behavior (models, paths, rules) | LOW | Basic config exists. Needs file-based config system |
| **Status/Health Check** | CLI tools need "is it working?" diagnostics | LOW | Missing. Should show Ollama connection, storage status |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Automatic Capture** | Zero manual effort - knowledge captured from conversations and commits | HIGH | KG-06, KG-07: Major differentiator. Most tools require manual add |
| **Dual-Scope Storage** | Global preferences + per-project knowledge keeps personal/team separate | MEDIUM | KG-01: Unique approach. Enables git-safe sharing |
| **Git-Safe by Design** | Project graphs committable without security risk | HIGH | KG-09, KG-10, KG-16, KG-17: Critical for dev tools, rarely done well |
| **Claude Code Hooks** | Seamless context injection on session start | MEDIUM | KG-12: Tight integration with Claude Code workflow |
| **Smart Retention** | Knowledge expires after 90 days unless reinforced | MEDIUM | KG-11: Prevents stale data buildup. RL-based importance scoring |
| **Semantic Context Injection** | Auto-inject relevant knowledge based on current file/commit | HIGH | KG-13: Goes beyond search - proactive context |
| **Background Processing** | Never blocks dev work - async queue with local processing | MEDIUM | KG-08: Essential UX, but technically complex |
| **Hybrid Cloud/Local LLM** | Cloud Ollama with local fallback - free tier with availability guarantee | MEDIUM | KG-03, KG-04: Balances cost and reliability |
| **Decisions-Only Mode** | Capture high-level decisions without code/data leakage | LOW | KG-15: Safer default for git commits |
| **Compact/Summarize** | Reduce graph size by consolidating redundant knowledge | MEDIUM | KG-14: Keeps graph manageable over time |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time Sync** | Users want instant collaboration | Adds distributed system complexity, conflicts, requires server infrastructure | Git-based async sharing - simpler, uses existing workflow |
| **Web UI Dashboard** | Graphical interfaces feel modern | Maintenance burden, scope creep, doesn't align with CLI-first | CLI with good formatting + MCP for Claude Desktop UI |
| **Full Code Storage** | "Store everything for perfect context" | Massive storage growth, git conflicts, leaks secrets, slow queries | Store decisions/patterns only, reference code by location |
| **Unlimited History** | "Never forget anything" | Unbounded growth, stale data pollution, slower searches | Smart retention with reinforcement - quality over quantity |
| **Multi-User Auth** | "Need permissions and roles" | Auth complexity, not needed for personal tool shared via git | Git permissions handle access, no auth layer needed |
| **Real-time Capture** | "Capture every keystroke" | Performance impact, noise pollution, privacy concerns | Batch capture every 5-10 turns or on commit - better signal |
| **Natural Language CLI** | "Just type what you want" | Unpredictable parsing, slow, magic behavior | Explicit commands with flags - clear, fast, scriptable |
| **Graph Visualization UI** | "See the knowledge graph visually" | Scope bloat, unreadable beyond 50 nodes, maintenance cost | Text-based queries with filtered views - more useful |

## Feature Dependencies

```
[Persistence Layer]
    └──requires──> [Kuzu Integration] (KG-02)
                       └──enables──> [Better Search Performance]

[Automatic Capture] (KG-06, KG-07)
    └──requires──> [Background Processing] (KG-08)
    └──requires──> [Security Filtering] (KG-09, KG-16, KG-17)
                       └──requires──> [Git-Safe Storage] (KG-10)

[Smart Retention] (KG-11)
    └──requires──> [Entity Importance Scoring]
    └──requires──> [Delete/Forget Operations] (KG-14)

[Claude Code Hooks] (KG-12)
    └──requires──> [Semantic Search] (KG-13)
    └──requires──> [Dual-Scope Storage] (KG-01)

[Dual-Scope Storage] (KG-01)
    └──requires──> [Separate Graph Instances]
    └──enables──> [Git-Safe Sharing]

[Compact/Summarize] (KG-14)
    └──requires──> [Entity Merging Logic]
    └──requires──> [Redundancy Detection]
```

### Dependency Notes

- **Persistence is foundational**: Kuzu migration (KG-02) must happen early - many features depend on it
- **Security before capture**: Filtering (KG-09, KG-16, KG-17) must be solid before automatic capture (KG-06, KG-07) goes live
- **Background processing enables automation**: Async queue (KG-08) is critical path for automatic capture features
- **Dual-scope enables sharing**: Separate global/project graphs (KG-01) must exist before git-safe sharing works
- **Semantic search powers hooks**: Claude Code hooks (KG-12) need semantic context injection (KG-13) to be valuable

## MVP Definition

### Launch With (v1.0 - Current Milestone)

Minimum viable product - what's needed to validate the concept.

- [x] **Basic MCP Server** - stdio + HTTP transports (already exists)
- [x] **Add/Search Operations** - Core CRUD via MCP (already exists)
- [x] **Ollama Integration** - Local LLM + embeddings (already exists)
- [ ] **Kuzu Persistence** (KG-02) - Replace in-memory storage (foundational upgrade)
- [ ] **Dual-Scope Storage** (KG-01) - Global + per-project graphs (core architecture)
- [ ] **CLI Commands** (KG-05) - add, search, delete, list, status (CLI-first design)
- [ ] **Git Post-Commit Hook** (KG-07) - Automatic capture on commits (automation baseline)
- [ ] **Security Filtering** (KG-09, KG-16, KG-17) - File exclusions + entity sanitization (required for safety)
- [ ] **Background Processing** (KG-08) - Non-blocking async queue (UX requirement)

**Why essential**: These features establish the core value proposition (automatic context capture + git-safe sharing) with minimal complexity. Without these, the tool is just another manual knowledge base.

### Add After Validation (v1.x)

Features to add once core is working and users validate the concept.

- [ ] **Claude Code Hooks** (KG-12) - Auto-inject context on session start (trigger: users ask for it)
- [ ] **Semantic Context Injection** (KG-13) - Smart context based on current work (trigger: hooks are working)
- [ ] **Cloud Ollama Fallback** (KG-03, KG-04) - Free tier with local backup (trigger: quota concerns)
- [ ] **Conversation Capture** (KG-06) - Background capture every 5-10 turns (trigger: post-commit hook validated)
- [ ] **Smart Retention** (KG-11) - 90-day expiration with reinforcement (trigger: graph size issues)
- [ ] **Compact/Summarize** (KG-14) - Reduce graph redundancy (trigger: retention is working)
- [ ] **Configurable Capture Modes** (KG-15) - decisions-only vs full (trigger: user feedback on what to capture)

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Enhanced MCP Tools** - Advanced graph operations beyond basic CRUD (defer: wait for MCP protocol evolution)
- [ ] **Multi-Model Support** - Support GPT, Claude API, other providers (defer: Ollama is sufficient for v1)
- [ ] **Team Collaboration Features** - Shared graphs, merge strategies (defer: git-based sharing validates first)
- [ ] **Advanced Graph Queries** - Complex traversals, pattern matching (defer: simple search is enough initially)
- [ ] **Import/Export** - Migrate knowledge between instances (defer: nice-to-have, not critical)
- [ ] **Visualization Tools** - Graph rendering, relationship maps (defer: anti-feature until proven needed)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Kuzu Persistence (KG-02) | HIGH | MEDIUM | P1 |
| Dual-Scope Storage (KG-01) | HIGH | MEDIUM | P1 |
| CLI Commands (KG-05) | HIGH | LOW | P1 |
| Security Filtering (KG-09, KG-16, KG-17) | HIGH | MEDIUM | P1 |
| Background Processing (KG-08) | HIGH | MEDIUM | P1 |
| Git Post-Commit Hook (KG-07) | HIGH | LOW | P1 |
| Delete/Forget (KG-14 partial) | HIGH | LOW | P1 |
| Status/Health Check | MEDIUM | LOW | P1 |
| Claude Code Hooks (KG-12) | HIGH | MEDIUM | P2 |
| Semantic Context Injection (KG-13) | HIGH | HIGH | P2 |
| Conversation Capture (KG-06) | MEDIUM | MEDIUM | P2 |
| Smart Retention (KG-11) | MEDIUM | MEDIUM | P2 |
| Cloud Ollama Fallback (KG-03, KG-04) | LOW | MEDIUM | P2 |
| Compact/Summarize (KG-14 full) | MEDIUM | HIGH | P2 |
| Configurable Modes (KG-15) | LOW | LOW | P2 |
| Advanced Graph Queries | LOW | HIGH | P3 |
| Multi-Model Support | LOW | HIGH | P3 |
| Import/Export | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch - core value proposition
- P2: Should have after validation - enhances core value
- P3: Nice to have - future consideration

## Competitor Feature Analysis

### Comparison with Similar Tools

| Feature | MCP Knowledge Graph (Anthropic) | kb CLI | Obsidian MCP | Our Approach |
|---------|--------------------------------|--------|--------------|--------------|
| **Storage Model** | Entity + Relations + Observations | Flat files with metadata | Markdown files | Entity + Relations (Graphiti) |
| **Persistence** | File-based (JSON) | File-based (markdown) | Obsidian vault | Kuzu graph database |
| **Scope Management** | Multiple named databases | Single knowledge base | Per-vault | Global + per-project |
| **Automatic Capture** | Manual only | Manual only | Manual only | **Auto from commits + conversations** |
| **Security Filtering** | Basic (file markers) | None | None | **File exclusions + entity sanitization** |
| **Git Integration** | Safety markers only | Git sync (experimental) | None | **Git post-commit hook + safe-by-design** |
| **CLI Interface** | Via MCP tools only | Full CLI | Via MCP tools | **CLI-first (hooks/MCP wrap CLI)** |
| **Search Type** | Keyword + relations | Regex grep | Full-text | **Semantic + graph traversal** |
| **Retention Policy** | Manual deletion | Manual deletion | Manual deletion | **Smart expiration with reinforcement** |
| **Context Injection** | None | None | None | **Auto-inject via Claude Code hooks** |
| **LLM Integration** | None (storage only) | None | None | **Ollama local + cloud** |
| **Background Processing** | N/A | N/A | N/A | **Async queue, non-blocking** |

### Key Differentiators

1. **Automatic capture** - Only tool that captures from commits and conversations without manual effort
2. **Git-safe by design** - Security filtering ensures project graphs are safe to commit
3. **Dual-scope storage** - Separates personal preferences from team knowledge
4. **Smart retention** - Prevents stale data buildup with reinforcement learning
5. **Context-aware injection** - Claude Code hooks provide relevant knowledge automatically

### What We're NOT Competing On

- **Full-featured PKM** - Not trying to replace Obsidian/Logseq/Notion
- **Team collaboration platform** - Git-based sharing is intentionally async and simple
- **General-purpose database** - Focused on developer knowledge, not arbitrary data
- **Visual graph exploration** - CLI-first means text queries, not graph visualizations

## Research Sources

### MCP Knowledge Graph Ecosystem

- [MCP Knowledge Graph by shaneholloman](https://github.com/shaneholloman/mcp-knowledge-graph) - Anthropic's persistent memory implementation
- [Knowledge & Memory MCP Servers on Glama](https://glama.ai/mcp/servers/categories/knowledge-and-memory) - Directory of 15+ memory/knowledge MCP servers
- [MCP Server Best Practices for 2026](https://www.cdata.com/blog/mcp-server-best-practices-2026) - OAuth 2.1 security standards
- [Knowledge Graph Memory MCP Server on PulseMCP](https://www.pulsemcp.com/servers/modelcontextprotocol-knowledge-graph-memory) - Feature comparison

### CLI Knowledge Management Tools

- [kb CLI by gnebbia](https://github.com/gnebbia/kb) - Minimalist CLI knowledge base with grep/filtering
- [SARA CLI Tool](https://dev.to/tumf/sara-a-cli-tool-for-managing-markdown-requirements-with-knowledge-graphs-nco) - Rust-based requirements management with knowledge graphs (Jan 2026)
- [GitLab Knowledge Graph](https://gitlab-org.gitlab.io/rust/knowledge-graph/) - CLI tool (gkg) for repository parsing and MCP integration

### Developer Context Management

- [GitHub Copilot CLI Enhanced Context](https://github.blog/changelog/2026-01-14-github-copilot-cli-enhanced-agents-context-management-and-new-ways-to-install/) - Jan 2026 context management features
- [Google Conductor for Gemini CLI](https://developers.googleblog.com/conductor-introducing-context-driven-development-for-gemini-cli/) - Context-driven development patterns
- [Gemini CLI Hooks](https://developers.googleblog.com/tailor-gemini-cli-to-your-workflow-with-hooks/) - Hook lifecycle and context injection patterns
- [Cursor CLI January 2026 Updates](https://cursor.com/changelog/cli-jan-08-2026) - Hook performance and MCP management

### Automatic Capture & Session Management

- [Gemini CLI Session Management](https://developers.googleblog.com/pick-up-exactly-where-you-left-off-with-session-management-in-gemini-cli/) - Auto-save sessions with context preservation
- [Agentic CLI Tools Compared](https://research.aimultiple.com/agentic-cli/) - Claude Code vs Cline vs Aider feature comparison
- [Top 5 CLI Coding Agents in 2026](https://dev.to/lightningdev123/top-5-cli-coding-agents-in-2026-3pia) - Deep context handling patterns

### Knowledge Graph Security & Filtering

- [Cybersecurity Knowledge Graphs](https://link.springer.com/article/10.1007/s10115-023-01860-3) - Filtering and data quality patterns
- [Security Knowledge Graph by Cyscale](https://cyscale.com/products/security-knowledge-graph/) - Filtering by network, protocol, threat level

### Retention Policies & Data Management

- [Data Retention Policy Guide 2026](https://concentric.ai/a-technical-guide-to-data-retention/) - Smart retention strategies
- [Mastra Retention Policy Feature Request](https://github.com/mastra-ai/mastra/issues/11664) - Framework-level retention design (Jan 2026)
- [Best Tools for Automating Retention](https://dialzara.com/blog/top-7-tools-for-automating-data-retention) - Automated expiration patterns

### Knowledge Graph Best Practices

- [Common Knowledge Graph Mistakes](https://www.cognee.ai/blog/fundamentals/knowledge-graph-myths) - Over-reliance on automation, poor entity resolution
- [Developer's Guide to Knowledge Graphs](https://medium.com/@satanialish/the-developers-guide-how-to-build-a-knowledge-graph-that-actually-makes-sense-%EF%B8%8F-ab91f5740d65) - Quality over size, iterative modeling
- [GraphRAG Design Patterns](https://gradientflow.substack.com/p/graphrag-design-patterns-challenges) - Architecture anti-patterns

### Reinforcement Learning for Knowledge Graphs

- [RKGnet: Deep RL for Knowledge Graphs](https://www.nature.com/articles/s41598-025-31109-8) - Entity importance scoring with RL (2026)
- [RAKCR: Sentiment-Aware Knowledge Graphs](https://www.sciencedirect.com/science/article/abs/pii/S0957417424002689) - Attention-enhanced entity selection
- [Awesome Knowledge Graph Reasoning](https://github.com/LIANGKE23/Awesome-Knowledge-Graph-Reasoning) - RL-based graph reasoning collection

---
*Feature research for: Knowledge Graph Developer Tools*
*Researched: 2026-02-02*
*Confidence: MEDIUM-HIGH (verified with multiple 2026 sources)*
