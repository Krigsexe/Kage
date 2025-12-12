# KAGE Development Workflow

## Project Status

**ALL PHASES: VALIDATED**

### Tools (11 total)
- [x] file_read, file_write, file_edit, dir_list (Core FS)
- [x] bash, code_exec (Execution)
- [x] git (Version control)
- [x] web_search, doc_fetch (Search & Docs)
- [x] test_run, cve_check (Testing & Security)

### Memory (YGGDRASIL 3-tier)
- [x] PersistentMemory - SQLite cross-session storage
- [x] SessionMemory - Active session state
- [x] WorkingMemory - Context window management
- [x] ContextCompactor - Auto-summarization

### Knowledge Base
- [x] EmbeddingManager - Sentence-transformers
- [x] CodebaseIndexer - ChromaDB storage
- [x] KnowledgeRetriever - RAG retrieval
- [x] DocsCache - Documentation caching

### Core
- [x] Config (settings.py with LLM, Memory, Tools, Knowledge)
- [x] Agent (ReAct loop, OllamaClient, ToolRegistry)
- [x] CLI (doctor, version, init, chat commands)

---

## Principes Fondamentaux

### 1. Zero Hallucination
- **JAMAIS** supposer qu'un fichier existe -> toujours `file_read` d'abord
- **JAMAIS** supposer une version de package -> toujours verifier
- **JAMAIS** inventer une API -> toujours consulter la doc officielle via `doc_fetch`
- Si incertitude -> **DEMANDER** a l'utilisateur

### 2. Memoire YGGDRASIL (3 niveaux)
```
PERSISTANTE: profil projet, decisions, erreurs passees (survit entre sessions)
SESSION: contexte conversation, fichiers modifies, taches en cours
TRAVAIL: context window LLM, auto-compactee si > 80% limite
```

### 3. Documentation-first
Avant d'utiliser une lib/framework:
1. Detecter la stack du projet
2. Identifier les dependances concernees
3. Fetch la doc officielle
4. Mettre en cache pour la session

---

## Checkpoints de Validation

```bash
# Phase 1: Config
python -c "from kage.config.settings import settings; print(f'Model: {settings.llm.model}')"

# Phase 2: Tools
python -c "from kage.tools.registry import ToolRegistry; r = ToolRegistry(); r.register_builtin(); print(f'Tools: {[t.name for t in r.list_all()]}')"

# Phase 3: Memory
python -c "from kage.memory.session import SessionMemory; m = SessionMemory(); print('Session memory OK')"

# Phase 4: Agent + CLI
kage doctor
kage version
kage init
```

---

## Components Implemented

### Tools (ALL DONE)
- [x] `code_exec.py` - Sandbox Python/Node execution
- [x] `search.py` - Web search (DuckDuckGo)
- [x] `docs.py` - Documentation fetching
- [x] `test.py` - Test runner
- [x] `cve.py` - CVE monitoring

### Memory (ALL DONE)
- [x] `persistent.py` - SQLite cross-session storage
- [x] `working.py` - Context window management
- [x] `compactor.py` - Auto-summarization

### Knowledge Base (ALL DONE)
- [x] `indexer.py` - Codebase indexation (ChromaDB)
- [x] `embeddings.py` - Vectorisation (sentence-transformers)
- [x] `retriever.py` - RAG retrieval
- [x] `docs_cache.py` - Documentation cache

## Components Pending (Future)

### MCP (Model Context Protocol)
- [ ] `server.py` - JSON-RPC server
- [ ] `protocol.py` - Types et parsing
- [ ] `handlers.py` - Request handlers

### Agent Extensions
- [ ] `planner.py` - Decomposition taches
- [ ] `executor.py` - Execution tools
- [ ] `validator.py` - Validation outputs

### LLM Fallback
- [ ] `openai.py` - OpenAI fallback client
- [ ] `router.py` - Routing intelligent (local vs cloud)

---

## Points Critiques

### Securite
- [x] Sandbox disabled for Windows (firejail is Linux-only)
- [ ] Sandbox Docker support for Windows
- [x] Path validation (no traversal)
- [x] Forbidden commands list
- [x] Dangerous patterns require confirmation

### Fiabilite
- [ ] Retry avec backoff sur appels LLM
- [ ] Graceful degradation si Ollama down
- [ ] State recovery apres crash
- [ ] Validation outputs LLM

### UX
- [x] Messages d'erreur clairs (ASCII for Windows)
- [x] Progress indicators (spinner, status)
- [x] Confirmation avant operations dangereuses
- [x] Help contextuel (/help command)

---

## Questions a Poser Avant Chaque Feature

1. **Existe-t-il deja?** -> Verifier le code existant
2. **Quelle est l'interface?** -> Definir input/output types
3. **Quels edge cases?** -> Gerer les erreurs explicitement
4. **Comment tester?** -> Ecrire le test avant implementation
5. **Documentation?** -> Docstring + README update

---

## Quick Commands

```bash
# Development
pip install -e .
kage --help

# Test LLM connection
kage doctor

# Start chat
kage chat

# Initialize project
kage init .

# Run tests
pytest tests/
```

---

## Architecture Cible

```
kage/
├── cli/           # Typer/Rich CLI
├── agent/         # ReAct loop + planner/executor
├── memory/        # YGGDRASIL 3-tier system
├── llm/           # Ollama + OpenAI fallback
├── tools/         # MCP-compatible tools
├── mcp/           # MCP server
├── knowledge/     # ChromaDB + embeddings
└── config/        # Pydantic settings
```

---

*KAGE v0.1.0 - Krigsexe Agentic Generative Engine*
