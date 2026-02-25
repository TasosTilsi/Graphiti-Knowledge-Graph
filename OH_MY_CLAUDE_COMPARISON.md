# Comparison: oh-my-claude vs oh-my-claudecode

**Analysis Date**: 2026-02-24
**Repo 1**: https://github.com/TechDufus/oh-my-claude
**Repo 2**: https://github.com/Yeachan-Heo/oh-my-claudecode

---

## Executive Summary

| Aspect | oh-my-claude | oh-my-claudecode |
|--------|-------------|-----------------|
| **Focus** | Quality gates + context protection | Multi-agent orchestration |
| **Scope** | Single-session enhancement | Cross-model coordination |
| **Philosophy** | "Enhance, don't replace" | "Zero learning curve" |
| **Agents** | 5 specialized subagents | 32+ specialized agents |
| **Complexity** | Moderate (hooks + subagents) | High (full orchestration) |
| **Best For** | Single project, GSD-like workflows | Large teams, multi-model work |

---

## Detailed Comparison

### 1. Core Purpose & Philosophy

#### **oh-my-claude (TechDufus)**
- **Philosophy**: "Enhance, don't replace" Claude Code's existing intelligence
- **Focus**: Add oversight layers and context protection around Claude Code
- **Scope**: Single Claude Code session
- **Target**: Individual developers who want guardrails and quality gates
- **Approach**: Lightweight addition to existing workflow

#### **oh-my-claudecode (Yeachan-Heo)**
- **Philosophy**: "Zero learning curve" for multi-agent orchestration
- **Focus**: Coordinate multiple AI models and agents for complex tasks
- **Scope**: Multi-agent, cross-model coordination
- **Target**: Teams that need parallelized execution and agent specialization
- **Approach**: Framework for agent-based task decomposition

---

### 2. Architecture & Components

#### **oh-my-claude Architecture**

**Layers**:
1. **Hooks (Automatic, Passive)**
   - `context-guardian` — Injects protection rules at startup
   - `ultrawork-detector` — Identifies keywords, injects directives
   - `safe-permissions` — Auto-approves safe commands
   - `todo-enforcer` — Prevents incomplete task stops
   - `context-monitor` — Warns at high usage
   - `subagent-quality-validator` — Validates outputs
   - `precompact-context` — Preserves state

2. **Subagent Team (5 Workers)**
   - **advisor** — Pre-planning gap analysis
   - **critic** — Plan review before execution
   - **librarian** — File/diff summarization
   - **validator** — Test/lint/type checks
   - **worker** — Implementation execution

3. **Commands & Skills (User-Triggered)**
   - `/prime` — Context recovery
   - `/worktree` — Git automation
   - `/ralph-plan` — PRD generation with interview/research

**Strengths**:
- ✅ Clean separation of concerns (hooks, subagents, commands)
- ✅ Lightweight (5 focused agents)
- ✅ Automatic background protection (hooks)
- ✅ Integrates with OpenKanban for status tracking

**Weaknesses**:
- ❌ Limited to Claude models
- ❌ Single-session focus
- ❌ No cross-model coordination

---

#### **oh-my-claudecode Architecture**

**Orchestration Modes**:
1. **Team Mode (Canonical)** — 5-stage pipeline
   - team-plan → team-prd → team-exec → team-verify → team-fix

2. **tmux CLI Workers** — Real processes in terminal split-panes
   - Spawns Claude/Codex/Gemini instances simultaneously

3. **Autopilot** — Single-agent autonomous execution

4. **Ralph Mode** — Persistent with verify/fix loops

5. **Legacy Modes** — swarm, ultrapilot (now route to Team)

**Components**:
- **agents/** — 32+ specialized agents (architecture, testing, design, data science)
- **src/** — Core runtime and orchestration logic
- **bridge/** — Claude Code CLI integration layer
- **skills/** — Reusable skill extraction system
- **hooks/** — Claude Code integration points
- **.claude-plugin/** — Plugin marketplace config

**Intelligence**:
- Smart model routing (Haiku for simple, Opus for complex)
- Automatic task delegation
- Real-time HUD statusline with metrics
- Token usage analytics

**Strengths**:
- ✅ Multi-model support (Claude, Codex, Gemini)
- ✅ Large agent library (32+ specialists)
- ✅ Advanced orchestration strategies (Team, Ralph, Autopilot)
- ✅ Real-time visibility (HUD)
- ✅ Cross-model coordination (ccg mode pairs Codex + Gemini)

**Weaknesses**:
- ❌ Higher complexity (steeper learning curve despite "zero learning curve" claim)
- ❌ More overhead (orchestration, model switching)
- ❌ Requires more configuration
- ❌ Heavier resource usage

---

### 3. Magic Keywords (Execution Modes)

#### **oh-my-claude Keywords**

| Keyword | Alias | Purpose | Mode |
|---------|-------|---------|------|
| `ultrawork` | `ulw` | Parallel execution + relentless tracking | Execution |
| `ultraresearch` | `ulr` | Exhaustive parallel research + cross-referencing | Research |
| `ultradebug` | `uld` | Systematic 7-step debugging methodology | Debugging |

**Implementation**: Keywords activate specialized subagent directives

---

#### **oh-my-claudecode Keywords**

| Keyword | Purpose | Effect |
|---------|---------|--------|
| `team` | Multi-agent orchestration | Triggers 5-stage pipeline |
| `autopilot` | Autonomous execution | Single agent, end-to-end |
| `ralph` | Persistent execution | Verify/fix loops until complete |
| `ulw` / `swarm` / `ultrapilot` | Power user shortcuts | Route to Team mode |
| `plan` | Planning mode | Triggers structured planning |

**Implementation**: Keywords trigger different orchestration pipelines

---

### 4. Agent Capabilities

#### **oh-my-claude (5 Agents)**

| Agent | Role | Responsibilities |
|-------|------|------------------|
| **advisor** | Pre-planning analyst | Gap analysis, hidden requirements |
| **critic** | Quality reviewer | Reviews plans before execution |
| **librarian** | Summarizer | File/diff summarization, context compression |
| **validator** | QA specialist | Tests, linting, type checking |
| **worker** | Implementer | Focused implementation tasks |

**Design Philosophy**: Minimal, specialized agents for specific tasks
**Execution**: Sequential with context passing
**Focus**: Quality gates and validation

---

#### **oh-my-claudecode (32+ Agents)**

Organized into domains:
- **Architecture** agents (design patterns, modularity)
- **Research** agents (data gathering, synthesis)
- **Design** agents (UX, system design)
- **Testing** agents (QA, test coverage)
- **Data Science** agents (analytics, modeling)
- **Engineering** agents (implementation, optimization)

**Design Philosophy**: Comprehensive coverage across specializations
**Execution**: Parallel with smart coordination
**Focus**: Throughput and specialization

---

### 5. Integration Points

#### **oh-my-claude**
- Claude Code hooks system
- OpenKanban (kanban board status)
- `OPENKANBAN_SESSION` environment variable
- Git worktree automation
- Context recovery mechanisms

**Integration Level**: **Tight** — deeply integrated with Claude Code

---

#### **oh-my-claudecode**
- Claude Code CLI bridge
- Multi-model APIs (Claude, Codex, Gemini)
- tmux terminal integration
- Telegram, Discord, Slack notifications
- Rate-limit auto-resume
- Session analytics

**Integration Level**: **Broad** — integrates with many external systems

---

### 6. Use Cases & Fit

#### **oh-my-claude is Best For:**

✅ Individual developers on **single focused projects**
✅ Projects using **GSD methodology** (phases, verification)
✅ Teams wanting **quality gates without complexity**
✅ Workflows needing **context protection** (avoiding context bloat)
✅ Scenarios where **one AI model is sufficient**
✅ Deep **Claude Code integration** workflows

**Example**: You're building graphiti-knowledge-graph with GSD phases → oh-my-claude fits perfectly

---

#### **oh-my-claudecode is Best For:**

✅ **Large teams** coordinating multiple engineers
✅ **Complex projects** requiring agent specialization
✅ **Multi-model workflows** (Claude + Codex + Gemini)
✅ **Autonomous execution** with minimal human intervention
✅ **Parallel task decomposition** (multiple agents working in parallel)
✅ **Enterprise environments** with notification/integration needs

**Example**: A data science team building ML pipelines with multiple tools → oh-my-claudecode fits

---

### 7. Key Differences Table

| Feature | oh-my-claude | oh-my-claudecode |
|---------|-------------|-----------------|
| **Agents** | 5 focused | 32+ specialized |
| **Models** | Claude only | Claude, Codex, Gemini |
| **Scope** | Single session | Cross-agent, cross-model |
| **Parallel Execution** | Limited | Full parallelization |
| **Orchestration** | Linear (hooks + workers) | Pipeline-based (Team, Ralph, etc.) |
| **Complexity** | Low-medium | High |
| **Learning Curve** | Gentle | Steep (despite "zero learning curve" claim) |
| **Integration** | Deep/Claude Code | Broad/external systems |
| **Best Deployment** | Individual/small teams | Large teams/enterprises |
| **Context Protection** | Excellent | Good (via orchestration) |
| **Quality Gates** | Built-in (validators) | Can be added via agents |
| **Execution Speed** | Sequential | Parallel (faster for large tasks) |
| **File Size** | Lightweight | Medium-heavy |
| **Dependencies** | Minimal | More (tmux, multiple API keys) |

---

## Recommended Use

### For graphiti-knowledge-graph Project (Your Current Setup)

**Recommendation**: **oh-my-claude fits better**

**Reasoning**:
1. ✅ You already use GSD (phases, verification, atomic commits)
2. ✅ Single-model workflow (Ollama/Claude)
3. ✅ Single-project focus (not multi-team)
4. ✅ Need for context protection (graphiti auto-capture + knowledge graph)
5. ✅ Quality gates fit perfectly (validator agent for tests)
6. ✅ Your 15-hook setup already provides what oh-my-claude hooks do

**Synergies**:
- oh-my-claude's 5 agents + your GSD phases = powerful combination
- oh-my-claude's context-guardian + smart-file-filter = redundancy (could optimize)
- oh-my-claude's validator agent = complements your test suite
- oh-my-claude's librarian agent = reduces graphiti burden

---

### If You Were Building Multi-Model Systems

**oh-my-claudecode would be better** if:
- Multiple team members working in parallel
- Need Codex (code generation) + Claude (reasoning) + Gemini (data)
- Heavy automation requirements
- Enterprise-scale orchestration

---

## Installation & Setup

### oh-my-claude
```bash
# Requirements: uv (Python package manager)
# Installation: Via Claude Code plugin system
/plugin install oh-my-claude@oh-my-claude
```

**Setup Time**: ~5 minutes
**Configuration**: Minimal
**Learning Time**: ~30 minutes

---

### oh-my-claudecode
```bash
# More complex setup
# Requires: Claude Code, tmux, multiple API keys
# Multiple agents need configuration

/plugin install oh-my-claudecode
# Then configure: agents, models, integrations
```

**Setup Time**: ~30 minutes
**Configuration**: Extensive
**Learning Time**: ~2-3 hours

---

## Conclusion

### oh-my-claude
- **Lean, focused enhancement** for Claude Code
- **Perfect for individuals/small teams** using single AI model
- **Fits seamlessly with GSD methodology**
- **Low overhead, high quality gates**
- **Best for your graphiti project**

### oh-my-claudecode
- **Comprehensive orchestration framework**
- **Perfect for enterprises** needing multi-agent/multi-model coordination
- **High complexity, high capability**
- **Better for large teams and complex decomposition**
- **Overkill for single-project, single-model work**

---

## Recommendations for You

### Current Setup (graphiti-knowledge-graph)
- Your existing hooks + GSD methodology = close to what oh-my-claude provides
- **Suggestion**: Adopt oh-my-claude if you want:
  - Formal subagent structure (advisor, critic, validator)
  - Built-in quality gates beyond your current hooks
  - Integrated context protection
  - Better separation of concerns

### Future Multi-Project / Multi-Team Setup
- **Consider oh-my-claudecode** if you scale to:
  - Multiple concurrent projects
  - Team collaboration (not solo)
  - Multiple AI models (Codex for code, Claude for design, Gemini for data)
  - Autonomous agent-driven workflows

---

## Quick Decision Matrix

```
Question: Should you use one of these?

1. Are you solo or small team on single project?
   YES → oh-my-claude is a good fit
   NO → oh-my-claudecode if enterprise scale

2. Do you use multiple AI models (Claude + Codex + Gemini)?
   YES → oh-my-claudecode required
   NO → oh-my-claude sufficient

3. Do you need parallel agent execution?
   YES → oh-my-claudecode
   NO → oh-my-claude

4. Is your project GSD-based (phases, verification)?
   YES → oh-my-claude integrates perfectly
   NO → either could work

5. Do you want light overhead with strong quality gates?
   YES → oh-my-claude
   NO → oh-my-claudecode for full orchestration
```
