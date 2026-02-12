# 🧠 Graphiti Knowledge Graph

> **Never repeat context again.** A personal knowledge graph system that automatically captures and provides development context—eliminating the need to re-explain preferences, decisions, and project architecture across Claude Code sessions.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with Kuzu](https://img.shields.io/badge/Database-Kuzu-orange.svg)](https://kuzudb.com/)

---

## 🎯 The Problem

You're working in Claude Code. You explain your tech stack, coding style, and project architecture. Next session? You explain it again. And again. Context is lost between sessions.

**Graphiti solves this:**
- 📝 Automatically captures **decisions** and **architecture**
- 🔍 Provides context when you start a new Claude Code session
- 🔐 Keeps sensitive data (secrets, PII) completely out of the graph
- 📦 Project knowledge stays in your git repo—shareable with your team
- ⚡ Runs locally, never blocks your workflow

---

## ✨ What It Does

### Core Features (Implemented ✓)

| Feature | Status | Details |
|---------|--------|---------|
| **CLI Interface** | ✓ Complete | 9 commands for full knowledge graph management |
| **Dual-Scope Storage** | ✓ Complete | Global preferences + per-project knowledge graphs |
| **Kuzu Database** | ✓ Complete | Persistent graph storage with semantic relationships |
| **Security Filtering** | ✓ Complete | Strips secrets, API keys, credentials automatically |
| **LLM Integration** | ✓ Complete | Cloud Ollama + local fallback for embeddings |
| **Semantic Search** | ✓ Complete | Find relevant knowledge via natural language |
| **Entity Management** | ✓ Complete | Add, list, show, delete, summarize, compact operations |

### Planned Features (Roadmap)

- 🎯 **Phase 5**: Background async queue for non-blocking capture
- 🪝 **Phase 6**: Git hooks for automatic commit-based capture
- 📚 **Phase 7**: Git-safe knowledge graphs (committable to GitHub)
- 🔌 **Phase 8**: MCP server integration with Claude Code hooks
- 🧹 **Phase 9**: Smart retention (90-day cleanup) and performance optimization

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repo
git clone git@github.com:TasosTilsi/Graphiti-Knowledge-Graph.git
cd Graphiti-Knowledge-Graph

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"
```

### Basic Usage

```bash
# Add knowledge to your global graph
graphiti add "We use pytest for testing and follow pytest-bdd patterns"

# Search for relevant knowledge
graphiti search "testing framework"

# List all stored knowledge
graphiti list

# Get details about a specific entity
graphiti show "pytest"

# Generate a summary of your knowledge graph
graphiti summarize

# Delete an entity
graphiti delete "old-decision"

# Deduplicate and optimize the graph
graphiti compact

# View health and statistics
graphiti health
graphiti config --show
```

### Scope: Global vs Project

```bash
# Global scope (stored in ~/.graphiti/global/)
graphiti add --scope global "My preferred Python version is 3.12+"

# Project scope (stored in .graphiti/ in current project)
graphiti add --scope project "We use FastAPI for this project's backend"
graphiti add  # Default: project scope if .git detected
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Claude Code                        │
│              (MCP Server - Future: Phase 8)             │
└────────────────────────┬────────────────────────────────┘
                         │ Context Injection
┌────────────────────────▼────────────────────────────────┐
│                    CLI Interface                        │
│    add | search | list | show | delete | summarize    │
│              compact | config | health                  │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌────────────┐  ┌──────────┐  ┌──────────────┐
   │ GraphService  │ LLM Client   │ Security Filter
   │ (Semantic    │ (Ollama)     │ (Secrets)
   │  Search)     │              │
   └────────────┘  └──────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                    ┌────▼─────┐
                    │   Kuzu   │
                    │ Database │
                    └──────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
    ~/.graphiti/               .graphiti/ (git-safe)
    (Global Preferences)       (Project Knowledge)
```

**Key Components:**

- **CLI Layer** (`src/cli/`): User-facing commands built with Typer
- **Graph Service** (`src/graph/`): Graphiti-core adapters + query API
- **LLM Integration** (`src/llm/`): Cloud Ollama + local fallback
- **Security** (`src/security/`): Secret detection and sanitization
- **Storage** (`src/storage/`): Kuzu database management

---

## 🔐 Security

Graphiti takes security seriously:

### What Gets Captured ✓
- Decisions and rationale
- Architecture patterns
- Technology choices
- Testing frameworks
- Coding conventions

### What Gets Filtered ✗
- API keys, tokens, credentials
- Database passwords
- Private keys
- Environment secrets (.env files)
- Sensitive configuration
- PII and personally identifiable information

**Mechanism:** The sanitizer runs on all content before storage, using:
- Pattern detection (regex for common formats)
- Entropy analysis (identifies high-entropy credential-like strings)
- detect-secrets integration (industry-standard scanning)
- Allowlist management (safe patterns to skip)

---

## 📊 Current Status

**Phase 4 Complete** (4 of 9 phases) ✓

| Phase | Goal | Status |
|-------|------|--------|
| 1 | Storage Foundation | ✓ Complete |
| 2 | Security Filtering | ✓ Complete |
| 3 | LLM Integration | ✓ Complete |
| 4 | CLI Interface | ✓ Complete |
| 5 | Background Queue | 🔄 Planned |
| 6 | Automatic Capture | 🔄 Planned |
| 7 | Git Integration | 🔄 Planned |
| 8 | MCP Server | 🔄 Planned |
| 9 | Advanced Features | 🔄 Planned |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_cli_commands.py

# Run with coverage
pytest --cov=src
```

**Test Suite:** 56 tests covering CLI commands, security filtering, LLM integration, and storage operations.

---

## 📦 Dependencies

### Core
- **graphiti-core** (0.26.3) — Knowledge graph operations
- **kuzu** (0.11.3) — Persistent graph database
- **ollama** (0.6.1) — LLM and embedding client
- **typer** — CLI framework

### Security
- **detect-secrets** (1.5.0+) — Secret scanning and detection

### Infrastructure
- **httpx** — Async HTTP client
- **persist-queue** — Local job queue
- **structlog** — Structured logging
- **tenacity** — Retry logic

See `pyproject.toml` for full dependency list.

---

## 🛠️ Development

### Project Structure

```
src/
├── cli/                 # CLI commands and utilities
│   ├── commands/       # Individual command implementations
│   ├── output.py       # Rich terminal formatting
│   └── utils.py        # CLI helpers
├── graph/              # GraphService and adapters
├── llm/                # Ollama client and LLM operations
├── security/           # Secret detection and sanitization
├── storage/            # Kuzu database management
├── models/             # Data models and types
└── config/             # Configuration management

tests/
├── test_cli_*.py       # CLI command tests
├── test_security_*.py  # Security filtering tests
├── test_llm_*.py       # LLM integration tests
└── test_storage_*.py   # Database tests

pyproject.toml          # Project metadata and dependencies
```

### Running Locally

```bash
# Install in development mode
pip install -e ".[dev]"

# Test a command
graphiti add "Test knowledge"
graphiti search "test"
graphiti list

# Check health
graphiti health

# View configuration
graphiti config --show
```

---

## 🚦 Next Steps

1. **Install & Try**: Follow Quick Start above
2. **Add Knowledge**: Use `graphiti add` to capture your preferences
3. **Search**: Test `graphiti search` with natural language queries
4. **Watch Roadmap**: Background queue and auto-capture coming next

---

## 📝 License

MIT License — See LICENSE file for details.

---

## 🤝 Contributing

This is a personal project, but contributions welcome!

- Report bugs and suggest features via GitHub Issues
- Submit PRs with improvements
- Extend security patterns or LLM integrations

---

## 📚 Resources

- **Graphiti Core**: [github.com/getzep/graphiti](https://github.com/getzep/graphiti)
- **Kuzu Database**: [kuzudb.com](https://kuzudb.com/)
- **Ollama**: [ollama.ai](https://ollama.ai/)
- **Claude Code**: [claude.com/claude-code](https://claude.com/claude-code)

---

**Built with ❤️ to remember what matters.**
