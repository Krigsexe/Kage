# KAGE Architecture

## Overview

KAGE (Krigsexe Agentic Generative Engine) is a local AI coding assistant built with a modular architecture focused on reliability, memory persistence, and extensibility.

## System Architecture

```
+------------------------------------------------------------------+
|                           KAGE                                    |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------+    +--------------+    +------------------+      |
|  |    CLI      |--->|  Agent Core  |--->|   Tool Router    |      |
|  | (Typer/Rich)|    |  (ReAct Loop)|    |                  |      |
|  +-------------+    +--------------+    +--------+---------+      |
|         |                  |                     |                |
|         v                  v                     v                |
|  +-------------+    +--------------+    +------------------+      |
|  |  Session    |    |   Memory     |    |     Tools        |      |
|  |  Manager    |    |   System     |    |  (MCP Protocol)  |      |
|  +-------------+    |  (YGGDRASIL) |    +------------------+      |
|                     +--------------+    | file_read        |      |
|                            |            | file_write       |      |
|                            v            | file_edit        |      |
|                     +--------------+    | dir_list         |      |
|                     |   Context    |    | bash             |      |
|                     |   Manager    |    | git              |      |
|                     | (Compaction) |    | web_search       |      |
|                     +--------------+    | doc_fetch        |      |
|                                         | test_run         |      |
|  +------------------------------------------+ cve_check    |      |
|  |         LLM Backend                      | code_exec    |      |
|  |  +------------+  +------------+          +------+-------+      |
|  |  |   Ollama   |  |   OpenAI   |                 |              |
|  |  |   (local)  |  |  (fallback)|                 v              |
|  |  +------------+  +------------+        +------------------+    |
|  +------------------------------------------+   MCP Server   |    |
|                                             | (JSON-RPC/STDIO)|    |
|  +------------------------------------------+------------------+    |
|  |                    Knowledge Base                           |    |
|  |  +-------------+  +-------------+  +-----------------+      |    |
|  |  |  Codebase   |  |    Docs     |  |   Embeddings    |      |    |
|  |  |   Index     |  |   Cache     |  |   (ChromaDB)    |      |    |
|  |  +-------------+  +-------------+  +-----------------+      |    |
|  +-------------------------------------------------------------+    |
+------------------------------------------------------------------+
```

## Memory System (YGGDRASIL)

The memory system is structured in 3 tiers:

### 1. Persistent Memory (SQLite)
- Survives across sessions
- Stores: project profile, architectural decisions, error history
- Location: `.kage/memory.db`

### 2. Session Memory
- Active during chat session
- Tracks: modified files, current errors, context
- Cleared on session end

### 3. Working Memory
- Manages LLM context window
- Auto-compaction at 80% threshold
- Token counting and management

## ReAct Loop

The agent follows the ReAct (Reasoning + Acting) pattern:

```
User Input
    |
    v
+-------------------+
|   Parse Intent    |
+-------------------+
    |
    v
+-------------------+
|  Check Knowledge  |<----+
+-------------------+     |
    |                     |
    v                     |
+-------------------+     |
|   LLM Reasoning   |     |
+-------------------+     |
    |                     |
    v                     |
+-------------------+     |
| Tool Call or      |-----+
| Final Response?   |
+-------------------+
    |
    v
+-------------------+
|   Execute Tool    |
+-------------------+
    |
    v
+-------------------+
|  Process Result   |
+-------------------+
    |
    +---> Loop back to LLM
```

## Tool System (MCP Compatible)

Tools follow the Model Context Protocol specification:

```python
class BaseTool:
    @property
    def definition(self) -> ToolDefinition:
        """Tool metadata for LLM."""
        ...

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        ...
```

### Built-in Tools
| Tool | Category | Description |
|------|----------|-------------|
| file_read | filesystem | Read file contents |
| file_write | filesystem | Create/overwrite files |
| file_edit | filesystem | Edit with str_replace |
| dir_list | filesystem | List directory |
| bash | execution | Shell commands |
| git | vcs | Git operations |
| web_search | search | Web search |
| doc_fetch | docs | Fetch documentation |
| test_run | testing | Run tests |
| cve_check | security | CVE scanning |
| code_exec | execution | Sandboxed code |

## Knowledge Base

### Components
- **CodebaseIndexer**: Indexes project files into ChromaDB
- **EmbeddingManager**: Generates embeddings (sentence-transformers)
- **KnowledgeRetriever**: RAG retrieval for context
- **DocsCache**: Caches external documentation

## Configuration

Settings are managed via Pydantic with environment variable support:

```python
# Environment variables
KAGE_LLM_MODEL=qwen2.5-coder:7b
KAGE_LLM_OLLAMA_HOST=http://localhost:11434
KAGE_MEMORY_COMPACTION_THRESHOLD=0.8
KAGE_TOOL_SANDBOX_ENABLED=true
```

## Docker Deployment

```yaml
services:
  ollama:    # LLM backend
  chromadb:  # Vector database
  kage:      # Main application
```

One-click deployment:
```bash
docker-compose -f docker/docker-compose.yml up -d
```
