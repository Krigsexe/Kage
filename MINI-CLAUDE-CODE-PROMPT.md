# PROMPT CLAUDE CODE — Mini Claude Code Agent

## Contexte projet

Tu vas m'aider à créer **KAGE** (Krigsexe Agentic Generative Engine), un agent de développement CLI open source inspiré de Claude Code, tournant sur des LLMs locaux (Ollama + Qwen2.5-Coder ou DeepSeek-Coder).

**Objectif** : Un assistant de développement fiable, sans hallucination, avec mémoire persistante, MCP intégré, et documentation automatique.

**Ma config locale** :
- GPU : RTX 5070 (~12GB VRAM)
- CPU : i7-12700KF
- RAM : 32GB DDR5 6000MHz
- OS : Linux (Ubuntu/Debian) ou Windows avec WSL2

**Timeline** : Week-end (2 jours)

---

## Architecture cible

```
┌─────────────────────────────────────────────────────────────────┐
│                           KAGE                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │    CLI      │───▶│  Agent Core  │───▶│   Tool Router    │   │
│  │ (Typer/Rich)│    │  (ReAct Loop)│    │                  │   │
│  └─────────────┘    └──────────────┘    └────────┬─────────┘   │
│         │                   │                     │             │
│         ▼                   ▼                     ▼             │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  Session    │    │   Memory     │    │     Tools        │   │
│  │  Manager    │    │   System     │    │  (MCP Protocol)  │   │
│  └─────────────┘    │  (YGGDRASIL) │    ├──────────────────┤   │
│                     └──────────────┘    │ • bash_exec      │   │
│                            │            │ • file_read      │   │
│                            ▼            │ • file_write     │   │
│                     ┌──────────────┐    │ • file_edit      │   │
│                     │   Context    │    │ • code_exec      │   │
│                     │   Manager    │    │ • web_search     │   │
│                     │ (Compaction) │    │ • doc_fetch      │   │
│                     └──────────────┘    │ • git_ops        │   │
│                                         │ • test_runner    │   │
│  ┌─────────────────────────────────┐    │ • cve_monitor    │   │
│  │         LLM Backend             │    └──────────────────┘   │
│  │  ┌───────────┐  ┌───────────┐  │              │             │
│  │  │  Ollama   │  │  OpenAI   │  │              ▼             │
│  │  │  (local)  │  │ (fallback)│  │    ┌──────────────────┐   │
│  │  └───────────┘  └───────────┘  │    │   MCP Server     │   │
│  └─────────────────────────────────┘    │  (JSON-RPC/STDIO)│   │
│                                         └──────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Knowledge Base                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │   │
│  │  │  Codebase   │  │    Docs     │  │   Embeddings    │  │   │
│  │  │   Index     │  │   Cache     │  │   (ChromaDB)    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Principes fondamentaux

### 1. Zéro hallucination

- **JAMAIS** supposer qu'un fichier existe → toujours `file_read` d'abord
- **JAMAIS** supposer une version de package → toujours vérifier `package.json`, `pyproject.toml`, etc.
- **JAMAIS** inventer une API → toujours consulter la doc officielle via `doc_fetch`
- Si incertitude → **DEMANDER** à l'utilisateur, ne pas deviner

### 2. Mémoire YGGDRASIL

Le système de mémoire est structuré en 3 niveaux :

```
┌─────────────────────────────────────────┐
│           MÉMOIRE PERSISTANTE           │
│  (survit entre sessions)                │
│  • Profil projet (stack, conventions)   │
│  • Décisions architecturales            │
│  • Erreurs passées et solutions         │
└─────────────────────────────────────────┘
                    ▲
                    │
┌─────────────────────────────────────────┐
│           MÉMOIRE DE SESSION            │
│  (durée de la session CLI)              │
│  • Contexte conversation                │
│  • Fichiers modifiés                    │
│  • État des tâches en cours             │
└─────────────────────────────────────────┘
                    ▲
                    │
┌─────────────────────────────────────────┐
│           MÉMOIRE DE TRAVAIL            │
│  (context window LLM)                   │
│  • Messages récents                     │
│  • Résultats tools actuels              │
│  • Auto-compactée si > 80% limite       │
└─────────────────────────────────────────┘
```

### 3. Auto-compaction

Quand le contexte atteint 80% de la limite du modèle :

1. **Summarize** les échanges anciens en bullet points
2. **Archive** le détail dans la mémoire de session
3. **Conserve** intégralement :
   - Le system prompt
   - Les 3 derniers échanges
   - Les fichiers actuellement ouverts/modifiés
   - Les erreurs non résolues

### 4. Documentation-first

Avant d'utiliser une lib/framework :
1. Détecter la stack du projet (package.json, pyproject.toml, etc.)
2. Identifier les dépendances concernées par la tâche
3. Fetch la doc officielle (uniquement les sections pertinentes)
4. Mettre en cache pour la session

---

## Structure du projet

```
kage/
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Tests, lint, type-check
│       ├── release.yml            # Build Docker, tag version
│       └── cve-scan.yml           # Scan vulnérabilités quotidien
├── docker/
│   ├── Dockerfile                 # Image principale
│   ├── Dockerfile.dev             # Dev avec hot-reload
│   └── docker-compose.yml         # Stack complète (Ollama + Kage + ChromaDB)
├── docs/
│   ├── ARCHITECTURE.md            # Ce document
│   ├── INSTALLATION.md            # Guide installation
│   ├── USAGE.md                   # Guide utilisateur
│   ├── TOOLS.md                   # Documentation des tools
│   ├── MCP.md                     # Spécification MCP
│   ├── CONTRIBUTING.md            # Guide contribution
│   └── PROMPTS.md                 # Versioning des prompts système
├── src/
│   └── kage/
│       ├── __init__.py
│       ├── __main__.py            # Entry point
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── app.py             # Typer app principale
│       │   ├── commands/
│       │   │   ├── __init__.py
│       │   │   ├── chat.py        # Mode conversation
│       │   │   ├── init.py        # Initialiser un projet
│       │   │   ├── index.py       # Indexer codebase
│       │   │   ├── config.py      # Configuration
│       │   │   └── doctor.py      # Diagnostics
│       │   └── ui/
│       │       ├── __init__.py
│       │       ├── prompt.py      # Prompt interactif Rich
│       │       ├── spinner.py     # Indicateurs de chargement
│       │       └── panels.py      # Affichage structuré
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── core.py            # ReAct loop principal
│       │   ├── planner.py         # Décomposition tâches
│       │   ├── executor.py        # Exécution tools
│       │   └── validator.py       # Validation outputs
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── persistent.py      # SQLite/JSON storage
│       │   ├── session.py         # Mémoire de session
│       │   ├── working.py         # Context window management
│       │   └── compactor.py       # Auto-summarization
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py            # Interface abstraite
│       │   ├── ollama.py          # Client Ollama
│       │   ├── openai.py          # Fallback OpenAI
│       │   └── router.py          # Routing intelligent
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── base.py            # Tool interface (MCP-compatible)
│       │   ├── registry.py        # Tool discovery & registration
│       │   ├── builtin/
│       │   │   ├── __init__.py
│       │   │   ├── bash.py        # Exécution shell
│       │   │   ├── files.py       # CRUD fichiers
│       │   │   ├── edit.py        # Édition str_replace style
│       │   │   ├── code_exec.py   # Sandbox Python/Node
│       │   │   ├── git.py         # Opérations Git
│       │   │   ├── test.py        # Test runner
│       │   │   ├── search.py      # Recherche web (DuckDuckGo)
│       │   │   ├── docs.py        # Fetch documentation
│       │   │   └── cve.py         # CVE monitoring
│       │   └── sandbox/
│       │       ├── __init__.py
│       │       ├── docker.py      # Exec dans container isolé
│       │       └── firejail.py    # Sandbox léger Linux
│       ├── mcp/
│       │   ├── __init__.py
│       │   ├── server.py          # MCP server (JSON-RPC)
│       │   ├── protocol.py        # Types et parsing
│       │   └── handlers.py        # Request handlers
│       ├── knowledge/
│       │   ├── __init__.py
│       │   ├── indexer.py         # Indexation codebase
│       │   ├── embeddings.py      # Vectorisation (sentence-transformers)
│       │   ├── retriever.py       # RAG retrieval
│       │   └── docs_cache.py      # Cache documentation
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py        # Pydantic settings
│       │   └── defaults.py        # Valeurs par défaut
│       └── utils/
│           ├── __init__.py
│           ├── logging.py         # Structured logging (JSON)
│           ├── errors.py          # Exception hierarchy
│           ├── retry.py           # Retry avec backoff
│           └── metrics.py         # Métriques Prometheus (optionnel)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Fixtures pytest
│   ├── unit/
│   │   ├── test_agent.py
│   │   ├── test_memory.py
│   │   ├── test_tools.py
│   │   └── test_compactor.py
│   ├── integration/
│   │   ├── test_ollama.py
│   │   ├── test_mcp.py
│   │   └── test_e2e_flow.py
│   └── fixtures/
│       ├── sample_project/
│       └── mock_responses/
├── prompts/
│   ├── v1/
│   │   ├── system.md              # System prompt principal
│   │   ├── planner.md             # Prompt planification
│   │   ├── validator.md           # Prompt validation
│   │   └── summarizer.md          # Prompt compaction
│   └── CHANGELOG.md               # Historique des changements prompts
├── scripts/
│   ├── install.sh                 # Installation one-liner
│   ├── setup-ollama.sh            # Setup Ollama + modèles
│   └── dev.sh                     # Lancement dev mode
├── pyproject.toml
├── README.md
├── LICENSE                        # MIT ou Apache 2.0
├── CHANGELOG.md
└── Makefile                       # Commandes utilitaires
```

---

## Fichiers à créer — Phase 1 : Foundation

### pyproject.toml

```toml
[project]
name = "kage"
version = "0.1.0"
description = "Krigsexe Agentic Generative Engine - Local AI coding assistant"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [
    { name = "Julien GELEE", email = "krigsexe@example.com" }
]
keywords = ["ai", "agent", "llm", "coding-assistant", "mcp"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Code Generators",
]

dependencies = [
    # CLI
    "typer[all]>=0.12.0",
    "rich>=13.7.0",
    "prompt-toolkit>=3.0.0",
    
    # LLM
    "ollama>=0.3.0",
    "openai>=1.40.0",  # Fallback
    "tiktoken>=0.7.0",  # Token counting
    
    # Memory & Storage
    "chromadb>=0.5.0",
    "sentence-transformers>=3.0.0",
    "sqlalchemy>=2.0.0",
    "aiosqlite>=0.20.0",
    
    # Tools
    "httpx>=0.27.0",
    "aiofiles>=24.1.0",
    "gitpython>=3.1.0",
    "pyyaml>=6.0.0",
    "toml>=0.10.0",
    
    # Validation & Config
    "pydantic>=2.8.0",
    "pydantic-settings>=2.4.0",
    
    # Utils
    "structlog>=24.4.0",
    "tenacity>=8.5.0",
    "watchfiles>=0.23.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.5.0",
    "mypy>=1.11.0",
    "pre-commit>=3.8.0",
]
docs = [
    "mkdocs>=1.6.0",
    "mkdocs-material>=9.5.0",
]

[project.scripts]
kage = "kage.cli.app:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/kage"]

[tool.ruff]
target-version = "py311"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "PT", "RUF"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --cov=src/kage --cov-report=term-missing"
```

### src/kage/config/settings.py

```python
"""Configuration settings with Pydantic."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM backend configuration."""
    
    model_config = SettingsConfigDict(env_prefix="KAGE_LLM_")
    
    provider: Literal["ollama", "openai"] = "ollama"
    model: str = "qwen2.5-coder:7b-instruct-q4_K_M"
    ollama_host: str = "http://localhost:11434"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"  # Fallback
    temperature: float = 0.1
    max_tokens: int = 4096
    context_window: int = 32768  # Qwen2.5-Coder context


class MemorySettings(BaseSettings):
    """Memory system configuration."""
    
    model_config = SettingsConfigDict(env_prefix="KAGE_MEMORY_")
    
    persistent_path: Path = Path.home() / ".kage" / "memory"
    compaction_threshold: float = 0.8  # 80% of context window
    max_history_messages: int = 50
    embedding_model: str = "all-MiniLM-L6-v2"


class ToolSettings(BaseSettings):
    """Tool execution configuration."""
    
    model_config = SettingsConfigDict(env_prefix="KAGE_TOOL_")
    
    sandbox_enabled: bool = True
    sandbox_type: Literal["docker", "firejail", "none"] = "firejail"
    bash_timeout: int = 30  # seconds
    code_exec_timeout: int = 60  # seconds
    max_file_size: int = 10 * 1024 * 1024  # 10MB


class KnowledgeSettings(BaseSettings):
    """Knowledge base configuration."""
    
    model_config = SettingsConfigDict(env_prefix="KAGE_KNOWLEDGE_")
    
    chroma_path: Path = Path.home() / ".kage" / "chroma"
    docs_cache_path: Path = Path.home() / ".kage" / "docs_cache"
    index_extensions: list[str] = Field(
        default=[".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".md", ".yaml", ".yml", ".json", ".toml"]
    )
    ignore_patterns: list[str] = Field(
        default=["node_modules", ".git", "__pycache__", ".venv", "dist", "build", ".next"]
    )


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="KAGE_",
        env_nested_delimiter="__",
    )
    
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["json", "console"] = "console"
    
    llm: LLMSettings = Field(default_factory=LLMSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    tools: ToolSettings = Field(default_factory=ToolSettings)
    knowledge: KnowledgeSettings = Field(default_factory=KnowledgeSettings)
    
    def ensure_directories(self) -> None:
        """Create necessary directories."""
        self.memory.persistent_path.mkdir(parents=True, exist_ok=True)
        self.knowledge.chroma_path.mkdir(parents=True, exist_ok=True)
        self.knowledge.docs_cache_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
```

### src/kage/tools/base.py

```python
"""Base tool interface - MCP compatible."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

from pydantic import BaseModel


class ToolCategory(str, Enum):
    """Tool categories for organization."""
    
    FILESYSTEM = "filesystem"
    CODE_EXECUTION = "code_execution"
    GIT = "git"
    SEARCH = "search"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    SECURITY = "security"


class ToolParameter(BaseModel):
    """Tool parameter definition (MCP-compatible)."""
    
    name: str
    type: str  # "string", "integer", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any | None = None
    enum: list[str] | None = None


class ToolDefinition(BaseModel):
    """Tool definition for LLM function calling (MCP-compatible)."""
    
    name: str
    description: str
    category: ToolCategory
    parameters: list[ToolParameter]
    dangerous: bool = False  # Requires confirmation
    requires_sandbox: bool = False


@dataclass
class ToolResult:
    """Result of tool execution."""
    
    success: bool
    output: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_llm_message(self) -> str:
        """Format for LLM consumption."""
        if self.success:
            return f"✓ Tool executed successfully:\n{self.output}"
        else:
            return f"✗ Tool execution failed:\nError: {self.error}\nOutput: {self.output}"


class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return tool definition for LLM."""
        ...
    
    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given parameters."""
        ...
    
    def validate_params(self, kwargs: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate parameters against definition."""
        for param in self.definition.parameters:
            if param.required and param.name not in kwargs:
                return False, f"Missing required parameter: {param.name}"
        return True, None
    
    async def safe_execute(self, **kwargs: Any) -> ToolResult:
        """Execute with validation and error handling."""
        valid, error = self.validate_params(kwargs)
        if not valid:
            return ToolResult(success=False, output="", error=error)
        
        try:
            return await self.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"{type(e).__name__}: {str(e)}"
            )


# Type for tool factory functions
ToolFactory = Callable[[], BaseTool]
T = TypeVar("T", bound=BaseTool)


def tool(
    name: str,
    description: str,
    category: ToolCategory,
    dangerous: bool = False,
    requires_sandbox: bool = False,
) -> Callable[[type[T]], type[T]]:
    """Decorator to register a tool class."""
    def decorator(cls: type[T]) -> type[T]:
        cls._tool_meta = {
            "name": name,
            "description": description,
            "category": category,
            "dangerous": dangerous,
            "requires_sandbox": requires_sandbox,
        }
        return cls
    return decorator
```

### src/kage/tools/builtin/files.py

```python
"""File system tools - read, write, list, edit."""

import os
from pathlib import Path
from typing import Any

import aiofiles

from kage.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from kage.config.settings import settings


class FileReadTool(BaseTool):
    """Read file contents."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_read",
            description="Read the contents of a file. Use this BEFORE assuming file contents.",
            category=ToolCategory.FILESYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Absolute or relative path to the file",
                ),
                ToolParameter(
                    name="start_line",
                    type="integer",
                    description="Start line (1-indexed, optional)",
                    required=False,
                ),
                ToolParameter(
                    name="end_line",
                    type="integer",
                    description="End line (inclusive, optional)",
                    required=False,
                ),
            ],
        )
    
    async def execute(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> ToolResult:
        file_path = Path(path).resolve()
        
        # Security check
        if not file_path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"File not found: {path}",
            )
        
        if file_path.stat().st_size > settings.tools.max_file_size:
            return ToolResult(
                success=False,
                output="",
                error=f"File too large (>{settings.tools.max_file_size} bytes)",
            )
        
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                lines = await f.readlines()
            
            # Handle line range
            if start_line is not None or end_line is not None:
                start = (start_line or 1) - 1  # 0-indexed
                end = end_line or len(lines)
                lines = lines[start:end]
                
                # Add line numbers
                numbered = [
                    f"{i + start + 1:4d} | {line.rstrip()}"
                    for i, line in enumerate(lines)
                ]
                content = "\n".join(numbered)
            else:
                content = "".join(lines)
            
            return ToolResult(
                success=True,
                output=content,
                metadata={"path": str(file_path), "lines": len(lines)},
            )
        
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                output="",
                error="File is not valid UTF-8 text",
            )


class FileWriteTool(BaseTool):
    """Write content to a file."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_write",
            description="Create or overwrite a file with new content.",
            category=ToolCategory.FILESYSTEM,
            dangerous=True,  # Destructive operation
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to create/overwrite",
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write to the file",
                ),
            ],
        )
    
    async def execute(self, path: str, content: str) -> ToolResult:
        file_path = Path(path).resolve()
        
        try:
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)
            
            return ToolResult(
                success=True,
                output=f"File written: {file_path} ({len(content)} bytes)",
                metadata={"path": str(file_path), "bytes": len(content)},
            )
        
        except PermissionError:
            return ToolResult(
                success=False,
                output="",
                error=f"Permission denied: {path}",
            )


class FileEditTool(BaseTool):
    """Edit file using str_replace pattern (like Claude Code)."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_edit",
            description="Edit a file by replacing a unique string. The old_str must appear EXACTLY ONCE.",
            category=ToolCategory.FILESYSTEM,
            dangerous=True,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to edit",
                ),
                ToolParameter(
                    name="old_str",
                    type="string",
                    description="Exact string to replace (must be unique in file)",
                ),
                ToolParameter(
                    name="new_str",
                    type="string",
                    description="Replacement string (empty to delete)",
                    required=False,
                    default="",
                ),
            ],
        )
    
    async def execute(
        self,
        path: str,
        old_str: str,
        new_str: str = "",
    ) -> ToolResult:
        file_path = Path(path).resolve()
        
        if not file_path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"File not found: {path}",
            )
        
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
            
            # Check uniqueness
            count = content.count(old_str)
            if count == 0:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"String not found in file. Searched for:\n{old_str[:200]}...",
                )
            if count > 1:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"String appears {count} times (must be unique). Be more specific.",
                )
            
            # Perform replacement
            new_content = content.replace(old_str, new_str, 1)
            
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(new_content)
            
            return ToolResult(
                success=True,
                output=f"Edited {file_path}: replaced {len(old_str)} chars with {len(new_str)} chars",
                metadata={
                    "path": str(file_path),
                    "old_len": len(old_str),
                    "new_len": len(new_str),
                },
            )
        
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                output="",
                error="File is not valid UTF-8 text",
            )


class DirectoryListTool(BaseTool):
    """List directory contents."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="dir_list",
            description="List files and directories in a path.",
            category=ToolCategory.FILESYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Directory path to list",
                ),
                ToolParameter(
                    name="depth",
                    type="integer",
                    description="Max depth to recurse (default 2)",
                    required=False,
                    default=2,
                ),
            ],
        )
    
    async def execute(self, path: str, depth: int = 2) -> ToolResult:
        dir_path = Path(path).resolve()
        
        if not dir_path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"Directory not found: {path}",
            )
        
        if not dir_path.is_dir():
            return ToolResult(
                success=False,
                output="",
                error=f"Not a directory: {path}",
            )
        
        ignore = set(settings.knowledge.ignore_patterns)
        
        def list_recursive(p: Path, current_depth: int, prefix: str = "") -> list[str]:
            if current_depth > depth:
                return []
            
            lines = []
            try:
                entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                return [f"{prefix}[permission denied]"]
            
            for entry in entries:
                if entry.name in ignore or entry.name.startswith("."):
                    continue
                
                if entry.is_dir():
                    lines.append(f"{prefix}📁 {entry.name}/")
                    lines.extend(list_recursive(entry, current_depth + 1, prefix + "  "))
                else:
                    size = entry.stat().st_size
                    size_str = f"{size:,}" if size < 1024 else f"{size // 1024}KB"
                    lines.append(f"{prefix}📄 {entry.name} ({size_str})")
            
            return lines
        
        tree = list_recursive(dir_path, 1)
        output = f"{dir_path}/\n" + "\n".join(tree)
        
        return ToolResult(
            success=True,
            output=output,
            metadata={"path": str(dir_path), "entries": len(tree)},
        )
```

### src/kage/tools/builtin/bash.py

```python
"""Bash execution tool with sandbox support."""

import asyncio
import os
import shlex
from pathlib import Path
from typing import Any

from kage.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from kage.config.settings import settings


# Commands that are NEVER allowed
FORBIDDEN_COMMANDS = {
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };:",  # Fork bomb
    "> /dev/sda",
    "chmod -R 777 /",
    "chown -R",
}

# Commands that require confirmation
DANGEROUS_PATTERNS = [
    "rm -rf",
    "rm -r",
    "sudo",
    "chmod",
    "chown",
    "systemctl",
    "service",
    "kill",
    "pkill",
    "reboot",
    "shutdown",
    "curl | bash",
    "wget | bash",
]


class BashTool(BaseTool):
    """Execute bash commands with safety checks."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="bash",
            description="Execute a bash command. Use for running scripts, installing packages, etc.",
            category=ToolCategory.CODE_EXECUTION,
            dangerous=True,
            requires_sandbox=True,
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="The bash command to execute",
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="Working directory (optional)",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout in seconds (default: 30)",
                    required=False,
                    default=30,
                ),
            ],
        )
    
    def _is_forbidden(self, command: str) -> bool:
        """Check if command is in forbidden list."""
        cmd_lower = command.lower().strip()
        return any(forbidden in cmd_lower for forbidden in FORBIDDEN_COMMANDS)
    
    def _is_dangerous(self, command: str) -> list[str]:
        """Return list of dangerous patterns found."""
        cmd_lower = command.lower()
        return [p for p in DANGEROUS_PATTERNS if p in cmd_lower]
    
    async def execute(
        self,
        command: str,
        cwd: str | None = None,
        timeout: int | None = None,
    ) -> ToolResult:
        # Security check - forbidden commands
        if self._is_forbidden(command):
            return ToolResult(
                success=False,
                output="",
                error="🚫 Command is forbidden for safety reasons.",
            )
        
        # Note dangerous patterns (caller should confirm)
        dangerous = self._is_dangerous(command)
        
        # Resolve working directory
        work_dir = Path(cwd).resolve() if cwd else Path.cwd()
        if not work_dir.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"Working directory not found: {cwd}",
            )
        
        # Determine timeout
        exec_timeout = timeout or settings.tools.bash_timeout
        
        try:
            # Build command based on sandbox settings
            if settings.tools.sandbox_enabled and settings.tools.sandbox_type == "firejail":
                # Firejail sandbox (Linux only)
                full_command = f"firejail --quiet --private-tmp --net=none -- bash -c {shlex.quote(command)}"
            else:
                full_command = command
            
            # Execute
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env={**os.environ, "TERM": "dumb"},  # Disable colors
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=exec_timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {exec_timeout}s",
                )
            
            # Format output
            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()
            
            output_parts = []
            if stdout_str:
                output_parts.append(stdout_str)
            if stderr_str:
                output_parts.append(f"[stderr]\n{stderr_str}")
            
            output = "\n".join(output_parts) or "(no output)"
            
            return ToolResult(
                success=process.returncode == 0,
                output=output,
                error=f"Exit code: {process.returncode}" if process.returncode != 0 else None,
                metadata={
                    "exit_code": process.returncode,
                    "cwd": str(work_dir),
                    "dangerous_patterns": dangerous,
                },
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution error: {type(e).__name__}: {str(e)}",
            )
```

### src/kage/memory/compactor.py

```python
"""Context compaction - YGGDRASIL-inspired memory management."""

import json
from dataclasses import dataclass
from typing import Any

import tiktoken

from kage.llm.base import LLMClient
from kage.config.settings import settings


@dataclass
class Message:
    """A conversation message."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    metadata: dict[str, Any] | None = None
    
    def token_count(self, encoding: tiktoken.Encoding) -> int:
        """Estimate token count."""
        return len(encoding.encode(self.content))


@dataclass
class CompactionResult:
    """Result of context compaction."""
    
    messages: list[Message]
    summary: str
    archived_count: int
    tokens_before: int
    tokens_after: int


SUMMARIZER_PROMPT = """You are a context summarizer. Your job is to compress conversation history while preserving all critical information.

Given the following conversation history, create a concise summary that captures:
1. Key decisions made
2. Files modified or created
3. Errors encountered and their resolutions
4. Current task state
5. Any pending actions

Be factual. Do not add interpretation. Use bullet points.

CONVERSATION TO SUMMARIZE:
{conversation}

OUTPUT FORMAT:
## Context Summary
- [key point 1]
- [key point 2]
...

## Files Touched
- path/to/file.py: [what was done]
...

## Current State
[brief description of where we are]

## Pending
- [any unfinished tasks]
"""


class ContextCompactor:
    """Manages context window compression."""
    
    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.threshold = int(
            settings.llm.context_window * settings.memory.compaction_threshold
        )
    
    def count_tokens(self, messages: list[Message]) -> int:
        """Count total tokens in messages."""
        return sum(m.token_count(self.encoding) for m in messages)
    
    def needs_compaction(self, messages: list[Message]) -> bool:
        """Check if compaction is needed."""
        return self.count_tokens(messages) >= self.threshold
    
    async def compact(self, messages: list[Message]) -> CompactionResult:
        """Compact messages while preserving critical context."""
        
        tokens_before = self.count_tokens(messages)
        
        # Always preserve:
        # 1. System prompt (index 0)
        # 2. Last N messages
        # 3. Any messages with errors/pending tasks
        
        preserve_last = 6  # Keep last 3 exchanges (user + assistant)
        
        system_msg = messages[0] if messages[0].role == "system" else None
        recent_msgs = messages[-preserve_last:] if len(messages) > preserve_last else messages
        
        # Messages to summarize
        if system_msg:
            to_summarize = messages[1:-preserve_last] if len(messages) > preserve_last + 1 else []
        else:
            to_summarize = messages[:-preserve_last] if len(messages) > preserve_last else []
        
        if not to_summarize:
            return CompactionResult(
                messages=messages,
                summary="",
                archived_count=0,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
            )
        
        # Generate summary
        conversation_text = "\n\n".join(
            f"[{m.role.upper()}]: {m.content[:500]}..."
            if len(m.content) > 500 else f"[{m.role.upper()}]: {m.content}"
            for m in to_summarize
        )
        
        prompt = SUMMARIZER_PROMPT.format(conversation=conversation_text)
        
        summary = await self.llm.complete(prompt)
        
        # Build compacted messages
        compacted: list[Message] = []
        
        if system_msg:
            compacted.append(system_msg)
        
        # Add summary as a system message
        compacted.append(Message(
            role="system",
            content=f"[COMPACTED CONTEXT]\n{summary}",
            metadata={"compacted": True, "archived_count": len(to_summarize)},
        ))
        
        compacted.extend(recent_msgs)
        
        tokens_after = self.count_tokens(compacted)
        
        return CompactionResult(
            messages=compacted,
            summary=summary,
            archived_count=len(to_summarize),
            tokens_before=tokens_before,
            tokens_after=tokens_after,
        )
```

### src/kage/agent/core.py

```python
"""Core agent - ReAct loop implementation."""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

from kage.llm.base import LLMClient
from kage.memory.compactor import ContextCompactor, Message
from kage.memory.session import SessionMemory
from kage.tools.registry import ToolRegistry
from kage.tools.base import ToolResult
from kage.config.settings import settings
from kage.utils.logging import get_logger

logger = get_logger(__name__)


class AgentState(str, Enum):
    """Agent execution state."""
    
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    WAITING_CONFIRMATION = "waiting_confirmation"
    RESPONDING = "responding"
    ERROR = "error"
    DONE = "done"


@dataclass
class AgentStep:
    """A single step in agent execution."""
    
    state: AgentState
    thought: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: ToolResult | None = None
    response: str | None = None
    error: str | None = None


SYSTEM_PROMPT = """You are KAGE, a local AI coding assistant. You help developers write, debug, and understand code.

## Core Principles

1. **NEVER ASSUME** - Always verify before acting:
   - Use `file_read` before assuming file contents
   - Use `dir_list` before assuming project structure
   - Use `doc_fetch` before assuming API syntax

2. **VERIFY THEN ACT** - Follow this pattern:
   - Read relevant files first
   - Understand the context
   - Plan your changes
   - Execute one change at a time
   - Verify the result

3. **NO HALLUCINATION** - If you don't know:
   - Search documentation
   - Ask the user
   - Say "I don't know" rather than guess

4. **INCREMENTAL CHANGES** - Make small, testable changes:
   - One logical change per edit
   - Test after each change
   - Rollback if something breaks

## Available Tools

{tools_description}

## Response Format

For each task, think step by step:

1. **Understand**: What is the user asking?
2. **Investigate**: What information do I need?
3. **Plan**: What steps will I take?
4. **Execute**: Perform each step, verify results
5. **Confirm**: Did it work? What's next?

When you need to use a tool, respond with:
```json
{{"tool": "tool_name", "args": {{"param": "value"}}}}
```

When you have the final answer, respond naturally without JSON.

## Current Session Context

Project: {project_path}
Working Directory: {cwd}
"""


class Agent:
    """Main agent orchestrator."""
    
    def __init__(
        self,
        llm: LLMClient,
        tool_registry: ToolRegistry,
        session_memory: SessionMemory,
    ):
        self.llm = llm
        self.tools = tool_registry
        self.memory = session_memory
        self.compactor = ContextCompactor(llm)
        self.messages: list[Message] = []
        self._init_system_prompt()
    
    def _init_system_prompt(self) -> None:
        """Initialize system prompt with tools."""
        tools_desc = self.tools.get_tools_description()
        
        system = SYSTEM_PROMPT.format(
            tools_description=tools_desc,
            project_path=self.memory.project_path or "Not initialized",
            cwd=self.memory.cwd,
        )
        
        self.messages.append(Message(role="system", content=system))
    
    async def _check_compaction(self) -> None:
        """Check and perform compaction if needed."""
        if self.compactor.needs_compaction(self.messages):
            logger.info("Context threshold reached, compacting...")
            result = await self.compactor.compact(self.messages)
            self.messages = result.messages
            logger.info(
                f"Compacted {result.archived_count} messages: "
                f"{result.tokens_before} -> {result.tokens_after} tokens"
            )
    
    def _parse_tool_call(self, content: str) -> tuple[str, dict[str, Any]] | None:
        """Extract tool call from LLM response."""
        # Look for JSON block
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if "tool" in data:
                    return data["tool"], data.get("args", {})
            except json.JSONDecodeError:
                pass
        
        # Look for inline JSON
        try:
            # Find first { and last }
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(content[start:end])
                if "tool" in data:
                    return data["tool"], data.get("args", {})
        except json.JSONDecodeError:
            pass
        
        return None
    
    async def run(self, user_input: str) -> AsyncIterator[AgentStep]:
        """Execute agent loop for user input."""
        
        # Add user message
        self.messages.append(Message(role="user", content=user_input))
        
        # Check compaction
        await self._check_compaction()
        
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Get LLM response
            yield AgentStep(state=AgentState.THINKING)
            
            try:
                response = await self.llm.chat(self.messages)
            except Exception as e:
                yield AgentStep(
                    state=AgentState.ERROR,
                    error=f"LLM error: {str(e)}",
                )
                return
            
            # Parse for tool call
            tool_call = self._parse_tool_call(response)
            
            if tool_call:
                tool_name, tool_args = tool_call
                
                yield AgentStep(
                    state=AgentState.TOOL_CALL,
                    thought=response,
                    tool_name=tool_name,
                    tool_args=tool_args,
                )
                
                # Check if tool exists
                tool = self.tools.get(tool_name)
                if not tool:
                    error_msg = f"Unknown tool: {tool_name}"
                    self.messages.append(Message(
                        role="tool",
                        content=error_msg,
                        metadata={"tool": tool_name, "error": True},
                    ))
                    continue
                
                # Check if dangerous (needs confirmation)
                if tool.definition.dangerous:
                    yield AgentStep(
                        state=AgentState.WAITING_CONFIRMATION,
                        tool_name=tool_name,
                        tool_args=tool_args,
                    )
                    # Caller should handle confirmation and call confirm_tool()
                    return
                
                # Execute tool
                result = await tool.safe_execute(**tool_args)
                
                yield AgentStep(
                    state=AgentState.TOOL_CALL,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    tool_result=result,
                )
                
                # Add tool result to messages
                self.messages.append(Message(
                    role="assistant",
                    content=response,
                ))
                self.messages.append(Message(
                    role="tool",
                    content=result.to_llm_message(),
                    metadata={
                        "tool": tool_name,
                        "success": result.success,
                    },
                ))
            
            else:
                # No tool call - this is the final response
                self.messages.append(Message(
                    role="assistant",
                    content=response,
                ))
                
                yield AgentStep(
                    state=AgentState.DONE,
                    response=response,
                )
                return
        
        # Max iterations reached
        yield AgentStep(
            state=AgentState.ERROR,
            error=f"Max iterations ({max_iterations}) reached",
        )
    
    async def confirm_tool(self, confirmed: bool) -> AsyncIterator[AgentStep]:
        """Continue after dangerous tool confirmation."""
        if not confirmed:
            self.messages.append(Message(
                role="tool",
                content="User declined to execute the tool.",
            ))
            yield AgentStep(
                state=AgentState.DONE,
                response="Operation cancelled by user.",
            )
            return
        
        # Re-parse last assistant message for tool call
        last_assistant = next(
            (m for m in reversed(self.messages) if m.role == "assistant"),
            None,
        )
        
        if not last_assistant:
            yield AgentStep(
                state=AgentState.ERROR,
                error="No pending tool call found",
            )
            return
        
        tool_call = self._parse_tool_call(last_assistant.content)
        if not tool_call:
            yield AgentStep(
                state=AgentState.ERROR,
                error="Could not parse tool call",
            )
            return
        
        tool_name, tool_args = tool_call
        tool = self.tools.get(tool_name)
        
        if not tool:
            yield AgentStep(
                state=AgentState.ERROR,
                error=f"Tool not found: {tool_name}",
            )
            return
        
        # Execute
        result = await tool.safe_execute(**tool_args)
        
        yield AgentStep(
            state=AgentState.TOOL_CALL,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=result,
        )
        
        self.messages.append(Message(
            role="tool",
            content=result.to_llm_message(),
            metadata={"tool": tool_name, "success": result.success},
        ))
        
        # Continue agent loop
        async for step in self.run(""):
            yield step
```

### src/kage/cli/app.py

```python
"""Main CLI application."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table

from kage.agent.core import Agent, AgentState, AgentStep
from kage.llm.ollama import OllamaClient
from kage.memory.session import SessionMemory
from kage.tools.registry import ToolRegistry
from kage.config.settings import settings

app = typer.Typer(
    name="kage",
    help="KAGE - Krigsexe Agentic Generative Engine",
    no_args_is_help=True,
)
console = Console()


def print_banner() -> None:
    """Print welcome banner."""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║   _  __    _    ____ _____                                ║
║  | |/ /   / \  / ___| ____|                               ║
║  | ' /   / _ \| |  _|  _|                                 ║
║  | . \  / ___ \ |_| | |___                                ║
║  |_|\_\/_/   \_\____|_____|                               ║
║                                                           ║
║  Krigsexe Agentic Generative Engine                       ║
║  Local AI Coding Assistant                                ║
╚═══════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def format_step(step: AgentStep) -> Panel | None:
    """Format an agent step for display."""
    
    if step.state == AgentState.THINKING:
        return Panel(
            Spinner("dots", text="Thinking..."),
            title="[yellow]Processing[/yellow]",
            border_style="yellow",
        )
    
    elif step.state == AgentState.TOOL_CALL:
        if step.tool_result:
            status = "✓" if step.tool_result.success else "✗"
            style = "green" if step.tool_result.success else "red"
            
            content = f"[bold]{status} {step.tool_name}[/bold]\n\n"
            if step.tool_args:
                content += f"Args: {step.tool_args}\n\n"
            content += step.tool_result.output[:1000]
            if len(step.tool_result.output) > 1000:
                content += "\n... (truncated)"
            
            return Panel(
                content,
                title=f"[{style}]Tool Result[/{style}]",
                border_style=style,
            )
        else:
            return Panel(
                f"Calling: [bold]{step.tool_name}[/bold]\nArgs: {step.tool_args}",
                title="[blue]Tool Call[/blue]",
                border_style="blue",
            )
    
    elif step.state == AgentState.WAITING_CONFIRMATION:
        return Panel(
            f"⚠️ Dangerous operation requested:\n\n"
            f"Tool: [bold]{step.tool_name}[/bold]\n"
            f"Args: {step.tool_args}",
            title="[yellow]Confirmation Required[/yellow]",
            border_style="yellow",
        )
    
    elif step.state == AgentState.DONE:
        return Panel(
            Markdown(step.response or ""),
            title="[green]Response[/green]",
            border_style="green",
        )
    
    elif step.state == AgentState.ERROR:
        return Panel(
            f"[red]{step.error}[/red]",
            title="[red]Error[/red]",
            border_style="red",
        )
    
    return None


@app.command()
def chat(
    project_path: Optional[Path] = typer.Option(
        None, "--project", "-p",
        help="Path to project directory",
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m",
        help="Override default model",
    ),
) -> None:
    """Start interactive chat session."""
    
    print_banner()
    
    # Initialize components
    project = project_path or Path.cwd()
    console.print(f"📁 Project: [cyan]{project}[/cyan]")
    
    settings.ensure_directories()
    
    if model:
        settings.llm.model = model
    
    console.print(f"🤖 Model: [cyan]{settings.llm.model}[/cyan]")
    console.print()
    
    # Create clients
    llm = OllamaClient()
    tools = ToolRegistry()
    tools.register_builtin()
    memory = SessionMemory(project_path=project)
    
    agent = Agent(llm, tools, memory)
    
    console.print("[dim]Type 'exit' or 'quit' to end session[/dim]")
    console.print("[dim]Type '/help' for commands[/dim]")
    console.print()
    
    async def run_chat() -> None:
        while True:
            try:
                user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Goodbye![/yellow]")
                break
            
            if user_input.lower() in ("exit", "quit", "/exit", "/quit"):
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if user_input.lower() == "/help":
                show_help()
                continue
            
            if user_input.lower() == "/clear":
                console.clear()
                print_banner()
                continue
            
            if not user_input.strip():
                continue
            
            # Run agent
            async for step in agent.run(user_input):
                panel = format_step(step)
                if panel:
                    console.print(panel)
                
                # Handle confirmation
                if step.state == AgentState.WAITING_CONFIRMATION:
                    confirmed = Confirm.ask("Execute this operation?")
                    async for confirm_step in agent.confirm_tool(confirmed):
                        confirm_panel = format_step(confirm_step)
                        if confirm_panel:
                            console.print(confirm_panel)
            
            console.print()
    
    asyncio.run(run_chat())


@app.command()
def init(
    path: Optional[Path] = typer.Argument(
        None,
        help="Project path (default: current directory)",
    ),
) -> None:
    """Initialize KAGE in a project directory."""
    
    project_path = path or Path.cwd()
    kage_dir = project_path / ".kage"
    
    if kage_dir.exists():
        console.print(f"[yellow]KAGE already initialized in {project_path}[/yellow]")
        return
    
    # Create .kage directory
    kage_dir.mkdir(parents=True)
    
    # Create config file
    config = {
        "project_name": project_path.name,
        "created_at": str(asyncio.get_event_loop().time()),
        "conventions": [],
        "ignore_patterns": list(settings.knowledge.ignore_patterns),
    }
    
    import json
    (kage_dir / "config.json").write_text(json.dumps(config, indent=2))
    
    # Create memory directory
    (kage_dir / "memory").mkdir()
    
    console.print(f"[green]✓ Initialized KAGE in {project_path}[/green]")
    console.print(f"  Created: {kage_dir}")


@app.command()
def index(
    path: Optional[Path] = typer.Argument(
        None,
        help="Project path to index",
    ),
) -> None:
    """Index project codebase for semantic search."""
    
    from kage.knowledge.indexer import CodebaseIndexer
    
    project_path = path or Path.cwd()
    
    console.print(f"📊 Indexing [cyan]{project_path}[/cyan]...")
    
    async def run_index() -> None:
        indexer = CodebaseIndexer(project_path)
        
        with console.status("Indexing files..."):
            stats = await indexer.index()
        
        table = Table(title="Indexing Complete")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Files indexed", str(stats["files"]))
        table.add_row("Chunks created", str(stats["chunks"]))
        table.add_row("Time taken", f"{stats['time']:.2f}s")
        
        console.print(table)
    
    asyncio.run(run_index())


@app.command()
def doctor() -> None:
    """Check system configuration and dependencies."""
    
    console.print("[bold]KAGE System Check[/bold]\n")
    
    checks = []
    
    # Check Ollama
    import httpx
    try:
        response = httpx.get(f"{settings.llm.ollama_host}/api/tags", timeout=5)
        models = response.json().get("models", [])
        model_names = [m["name"] for m in models]
        
        if settings.llm.model in model_names:
            checks.append(("Ollama", "✓ Running", "green", f"Model '{settings.llm.model}' available"))
        else:
            checks.append(("Ollama", "⚠ Running", "yellow", f"Model '{settings.llm.model}' not found"))
    except Exception as e:
        checks.append(("Ollama", "✗ Not running", "red", str(e)))
    
    # Check directories
    for name, path in [
        ("Memory storage", settings.memory.persistent_path),
        ("ChromaDB", settings.knowledge.chroma_path),
        ("Docs cache", settings.knowledge.docs_cache_path),
    ]:
        if path.exists():
            checks.append((name, "✓ Exists", "green", str(path)))
        else:
            checks.append((name, "✗ Missing", "yellow", f"Will be created: {path}"))
    
    # Check sandbox
    if settings.tools.sandbox_enabled:
        import shutil
        if settings.tools.sandbox_type == "firejail":
            if shutil.which("firejail"):
                checks.append(("Sandbox (firejail)", "✓ Available", "green", ""))
            else:
                checks.append(("Sandbox (firejail)", "✗ Not installed", "red", "Run: sudo apt install firejail"))
        elif settings.tools.sandbox_type == "docker":
            if shutil.which("docker"):
                checks.append(("Sandbox (docker)", "✓ Available", "green", ""))
            else:
                checks.append(("Sandbox (docker)", "✗ Not installed", "red", "Install Docker"))
    
    # Display results
    table = Table()
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Details", style="dim")
    
    for name, status, color, details in checks:
        table.add_row(name, f"[{color}]{status}[/{color}]", details)
    
    console.print(table)


def show_help() -> None:
    """Show help for chat commands."""
    help_text = """
## Chat Commands

| Command | Description |
|---------|-------------|
| `/help` | Show this help |
| `/clear` | Clear screen |
| `/exit` | Exit chat |
| `exit` | Exit chat |

## Tips

- Be specific about what you want
- Reference files by their full path
- Ask KAGE to verify before making changes
"""
    console.print(Markdown(help_text))


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
```

### docker/Dockerfile

```dockerfile
# KAGE - Multi-stage build

# === Builder ===
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir build && \
    pip wheel --no-cache-dir --wheel-dir=/wheels .

# === Runtime ===
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    firejail \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash kage

# Copy wheels and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

# Copy source
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY README.md ./

# Set ownership
RUN chown -R kage:kage /app

# Switch to non-root user
USER kage

# Create data directories
RUN mkdir -p /home/kage/.kage/memory \
    /home/kage/.kage/chroma \
    /home/kage/.kage/docs_cache

# Environment
ENV KAGE_LOG_FORMAT=json
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from kage.config.settings import settings; print('OK')"

ENTRYPOINT ["kage"]
CMD ["--help"]
```

### docker/docker-compose.yml

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: kage-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  kage:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: kage-app
    depends_on:
      - ollama
    environment:
      - KAGE_LLM_OLLAMA_HOST=http://ollama:11434
      - KAGE_LLM_MODEL=qwen2.5-coder:7b-instruct-q4_K_M
    volumes:
      - kage-data:/home/kage/.kage
      - ./workspace:/workspace  # Mount project directory
    working_dir: /workspace
    stdin_open: true
    tty: true
    command: ["chat"]

  chromadb:
    image: chromadb/chroma:latest
    container_name: kage-chroma
    ports:
      - "8000:8000"
    volumes:
      - chroma-data:/chroma/chroma
    restart: unless-stopped

volumes:
  ollama-data:
  kage-data:
  chroma-data:
```

### .github/workflows/ci.yml

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install ruff mypy
          pip install -e ".[dev]"
      
      - name: Lint with ruff
        run: ruff check src/ tests/
      
      - name: Type check with mypy
        run: mypy src/

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -e ".[dev]"
      
      - name: Run tests
        run: pytest --cov=src/kage --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: coverage.xml

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Build Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/Dockerfile
          push: false
          tags: kage:test
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### .github/workflows/cve-scan.yml

```yaml
name: CVE Scan

on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install pip-audit
        run: pip install pip-audit
      
      - name: Install dependencies
        run: pip install -e .
      
      - name: Run pip-audit
        run: pip-audit --strict --desc on
        continue-on-error: true
      
      - name: Run Trivy on Docker image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'kage:latest'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
        continue-on-error: true
      
      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
        if: always()
```

### scripts/install.sh

```bash
#!/bin/bash
set -e

echo "🚀 Installing KAGE..."

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python $required_version or higher required (found $python_version)"
    exit 1
fi

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "📦 Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Start Ollama if not running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "🔄 Starting Ollama..."
    ollama serve &
    sleep 5
fi

# Pull default model
echo "📥 Pulling Qwen2.5-Coder model..."
ollama pull qwen2.5-coder:7b-instruct-q4_K_M

# Install KAGE
echo "📦 Installing KAGE..."
pip install -e .

# Create directories
mkdir -p ~/.kage/{memory,chroma,docs_cache}

# Install firejail for sandboxing (optional)
if command -v apt-get &> /dev/null; then
    echo "📦 Installing firejail..."
    sudo apt-get update && sudo apt-get install -y firejail
fi

echo ""
echo "✅ KAGE installed successfully!"
echo ""
echo "Quick start:"
echo "  kage chat          # Start interactive chat"
echo "  kage init          # Initialize in current project"
echo "  kage doctor        # Check system status"
echo ""
```

### README.md

```markdown
# KAGE - Krigsexe Agentic Generative Engine

[![CI](https://github.com/krigsexe/kage/actions/workflows/ci.yml/badge.svg)](https://github.com/krigsexe/kage/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🤖 A local, open-source AI coding assistant inspired by Claude Code

KAGE is a privacy-first, local AI coding assistant that runs on your machine using open-source LLMs. Built with a focus on reliability, no hallucinations, and developer productivity.

## ✨ Features

- **100% Local** - Runs on Ollama with Qwen2.5-Coder or DeepSeek-Coder
- **No Hallucinations** - Always verifies before acting, never assumes
- **Memory System** - YGGDRASIL-inspired persistent context management
- **MCP Compatible** - Extensible tool system following Model Context Protocol
- **Sandboxed Execution** - Safe code execution with firejail/Docker
- **Documentation-First** - Auto-fetches relevant docs before using any library
- **CVE Monitoring** - Daily vulnerability scans of your dependencies

## 🚀 Quick Start

### One-liner install

```bash
curl -fsSL https://raw.githubusercontent.com/krigsexe/kage/main/scripts/install.sh | bash
```

### Manual install

```bash
# Prerequisites
# - Python 3.11+
# - Ollama

# Install Ollama and pull model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b-instruct-q4_K_M

# Install KAGE
pip install kage

# Start chatting
kage chat
```

### Docker

```bash
git clone https://github.com/krigsexe/kage.git
cd kage
docker-compose -f docker/docker-compose.yml up -d
docker exec -it kage-app kage chat
```

## 📖 Usage

```bash
# Interactive chat in current directory
kage chat

# Initialize KAGE in a project
kage init

# Index codebase for semantic search
kage index

# Check system status
kage doctor
```

### Chat Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/clear` | Clear screen |
| `/exit` | Exit chat |

## 🛠️ Configuration

KAGE can be configured via environment variables:

```bash
# LLM settings
export KAGE_LLM_MODEL="qwen2.5-coder:14b-instruct-q4_K_M"
export KAGE_LLM_TEMPERATURE=0.1

# Memory settings
export KAGE_MEMORY_COMPACTION_THRESHOLD=0.8

# Tool settings
export KAGE_TOOL_SANDBOX_ENABLED=true
export KAGE_TOOL_SANDBOX_TYPE=firejail
```

Or create a `.kage/config.json` in your project.

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
│                      │ docs  │          │
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
| `git` | Git operations |
| `test` | Run tests |
| `doc_fetch` | Fetch documentation |
| `web_search` | Search the web |
| `cve_check` | Check for vulnerabilities |

## 🧠 Memory System

KAGE uses a 3-tier memory system inspired by YGGDRASIL:

1. **Persistent Memory** - Survives across sessions (decisions, errors, conventions)
2. **Session Memory** - Active during chat session
3. **Working Memory** - Context window with auto-compaction

When context reaches 80%, older messages are summarized and archived automatically.

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Installation Guide](docs/INSTALLATION.md)
- [Usage Guide](docs/USAGE.md)
- [Tool Reference](docs/TOOLS.md)
- [MCP Protocol](docs/MCP.md)
- [Contributing](CONTRIBUTING.md)

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## 📄 License

MIT License - see [LICENSE](LICENSE)

## 🙏 Acknowledgments

- [Ollama](https://ollama.com) - Local LLM runtime
- [Qwen](https://github.com/QwenLM/Qwen2.5-Coder) - Excellent code-focused LLM
- [Claude Code](https://claude.ai) - Inspiration for the UX
- [Model Context Protocol](https://modelcontextprotocol.io) - Tool protocol specification

---

Made with ❤️ by [Julien GELEE](https://github.com/krigsexe)
```

---

## Workflow de développement

### Ordre d'implémentation

```
JOUR 1 (Samedi)
├── 09:00-10:00  Setup environnement, Ollama, modèle
├── 10:00-12:00  Phase 1: Config + Settings + Logging
├── 12:00-13:00  Pause
├── 13:00-15:00  Phase 2: Tools de base (files, bash)
├── 15:00-17:00  Phase 3: Agent core (ReAct loop basique)
├── 17:00-19:00  Phase 4: CLI interactive
└── 19:00-20:00  Tests manuels, debug

JOUR 2 (Dimanche)
├── 09:00-11:00  Phase 5: Memory system + Compaction
├── 11:00-13:00  Phase 6: Tools avancés (git, docs, search)
├── 13:00-14:00  Pause
├── 14:00-16:00  Phase 7: Docker + CI/CD
├── 16:00-18:00  Phase 8: Documentation complète
└── 18:00-20:00  Tests E2E, polish, README final
```

### Checkpoints de validation

Après chaque phase, valider avec ces tests :

```bash
# Phase 1: Config
python -c "from kage.config.settings import settings; print(settings.model_dump())"

# Phase 2: Tools
python -c "from kage.tools.builtin.files import FileReadTool; import asyncio; asyncio.run(FileReadTool().execute(path='README.md'))"

# Phase 3: Agent
kage doctor

# Phase 4: CLI
kage chat --help

# Phase 5: Memory
# Faire une longue conversation et vérifier la compaction

# Phase 6: Tools avancés
# Tester git, docs fetch

# Phase 7: Docker
docker-compose up -d
docker exec kage-app kage doctor

# Phase 8: E2E
kage chat  # Test complet interactif
```

---

## Commandes de démarrage

```bash
# 1. Créer le repo
mkdir kage && cd kage
git init

# 2. Créer la structure
mkdir -p src/kage/{cli,agent,memory,llm,tools/builtin,mcp,knowledge,config,utils}
mkdir -p docker docs tests/{unit,integration} prompts/v1 scripts .github/workflows

# 3. Créer les fichiers __init__.py
find src -type d -exec touch {}/__init__.py \;

# 4. Installer les dépendances de dev
pip install typer rich ollama pydantic pydantic-settings httpx aiofiles tiktoken structlog

# 5. Lancer le dev
python -m kage.cli.app --help
```

---

## Questions à me poser pendant le développement

Avant chaque feature, pose ces questions :

1. **Existe-t-il déjà ?** → Vérifie dans le code existant
2. **Quelle est l'interface ?** → Définis les types d'entrée/sortie
3. **Quels edge cases ?** → Gère les erreurs explicitement
4. **Comment tester ?** → Écris le test avant l'implémentation
5. **Documentation ?** → Docstring + README update

---

## Points critiques à ne pas oublier

### Sécurité
- [ ] Sandbox pour bash/code execution
- [ ] Validation des paths (pas de path traversal)
- [ ] Pas d'exécution de commandes dangereuses
- [ ] Secrets jamais en clair dans les logs

### Fiabilité
- [ ] Retry avec backoff sur les appels LLM
- [ ] Graceful degradation si Ollama down
- [ ] State recovery après crash
- [ ] Validation des outputs LLM

### UX
- [ ] Messages d'erreur clairs
- [ ] Progress indicators
- [ ] Confirmation avant opérations dangereuses
- [ ] Help contextuel

---

*Fin du prompt - Bonne chance pour le week-end de dev ! 🚀*
