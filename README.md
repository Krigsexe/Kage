# KAGE - Krigsexe Agentic Generative Engine

[![CI](https://github.com/Krigsexe/Kage/actions/workflows/ci.yml/badge.svg)](https://github.com/Krigsexe/Kage/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> 🤖 A local, open-source AI coding assistant inspired by Claude Code

KAGE is a privacy-first, local AI coding assistant that runs on your machine using open-source LLMs. Built with a focus on **reliability**, **no hallucinations**, and **developer productivity**.

## ✨ Features

- **100% Local** - Runs on Ollama with Qwen2.5-Coder or DeepSeek-Coder
- **No Hallucinations** - Always verifies before acting, never assumes
- **Memory System** - YGGDRASIL-inspired persistent context management
- **MCP Compatible** - Extensible tool system following Model Context Protocol
- **Sandboxed Execution** - Safe code execution with firejail/Docker
- **Auto-Compaction** - Intelligent context window management

## 🚀 Quick Start

### One-liner install

```bash
curl -fsSL https://raw.githubusercontent.com/Krigsexe/Kage/main/scripts/install.sh | bash
```

### Manual install

```bash
# Prerequisites: Python 3.11+

# 1. Install Ollama and pull model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b-instruct-q4_K_M

# 2. Clone and install KAGE
git clone https://github.com/Krigsexe/Kage.git
cd Kage
pip install -e .

# 3. Start chatting
kage chat
```

### Docker

```bash
git clone https://github.com/Krigsexe/Kage.git
cd Kage
docker-compose -f docker/docker-compose.yml up -d
docker exec -it kage-app kage chat
```

## 📖 Usage

```bash
# Interactive chat in current directory
kage chat

# Chat with specific project
kage chat --project /path/to/project

# Initialize KAGE in a project
kage init

# Check system status
kage doctor
```

### Chat Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/clear` | Clear screen |
| `/status` | Show session status |
| `/exit` | Exit chat |

## 🛠️ Configuration

KAGE can be configured via environment variables:

```bash
# LLM settings
export KAGE_LLM_MODEL="qwen2.5-coder:14b-instruct-q4_K_M"
export KAGE_LLM_TEMPERATURE=0.1
export KAGE_LLM_OLLAMA_HOST="http://localhost:11434"

# Memory settings
export KAGE_MEMORY_COMPACTION_THRESHOLD=0.8

# Tool settings
export KAGE_TOOL_SANDBOX_ENABLED=true
export KAGE_TOOL_SANDBOX_TYPE=firejail  # or "docker" or "none"
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│              KAGE Agent                  │
├─────────────────────────────────────────┤
│  CLI (Typer/Rich) → Agent (ReAct Loop)  │
│           ↓              ↓              │
│      Session Memory   Tool Router       │
│           ↓              ↓              │
│   Context Compactor   MCP Tools         │
│           ↓              │              │
│     Persistent DB    ┌───┴───┐          │
│                      │ bash  │          │
│                      │ files │          │
│                      │ git   │          │
│                      └───────┘          │
└─────────────────────────────────────────┘
```

## 🔧 Built-in Tools

| Tool | Description |
|------|-------------|
| `file_read` | Read file contents |
| `file_write` | Create/overwrite files |
| `file_edit` | Edit files (str_replace pattern) |
| `dir_list` | List directory contents |
| `bash` | Execute shell commands (sandboxed) |
| `git` | Git operations (status, diff, commit...) |

## 🧠 Memory System

KAGE uses a 3-tier memory system inspired by YGGDRASIL:

1. **Persistent Memory** - Survives across sessions (decisions, errors, conventions)
2. **Session Memory** - Active during chat session
3. **Working Memory** - Context window with auto-compaction

When context reaches 80%, older messages are summarized and archived automatically.

## 📋 Requirements

- Python 3.11+
- Ollama
- 12GB+ VRAM for 7B models (RTX 3060/4060 or better)
- Linux recommended (for firejail sandbox)

### Recommended Models

| Model | VRAM | Quality |
|-------|------|---------|
| `qwen2.5-coder:7b-instruct-q4_K_M` | ~5GB | ⭐⭐⭐⭐ |
| `qwen2.5-coder:14b-instruct-q4_K_M` | ~9GB | ⭐⭐⭐⭐⭐ |
| `deepseek-coder-v2:16b` | ~10GB | ⭐⭐⭐⭐⭐ |

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

```bash
# Setup dev environment
git clone https://github.com/Krigsexe/Kage.git
cd Kage
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
```

## 📄 License

MIT License - see [LICENSE](LICENSE)

## 🙏 Acknowledgments

- [Ollama](https://ollama.com) - Local LLM runtime
- [Qwen](https://github.com/QwenLM/Qwen2.5-Coder) - Excellent code-focused LLM
- [Claude Code](https://claude.ai) - Inspiration for the UX
- [Model Context Protocol](https://modelcontextprotocol.io) - Tool protocol specification

---

Made with ❤️ by [Julien GELEE](https://github.com/Krigsexe)
