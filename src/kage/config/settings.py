"""Configuration settings with Pydantic."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM backend configuration."""
    
    model_config = SettingsConfigDict(env_prefix="KAGE_LLM_")
    
    provider: Literal["ollama", "openai"] = "ollama"
    model: str = "qwen2.5-coder:1.5b"  # Use the model you have installed
    ollama_host: str = "http://localhost:11434"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    temperature: float = 0.1
    max_tokens: int = 4096
    context_window: int = 32768


class MemorySettings(BaseSettings):
    """Memory system configuration."""
    
    model_config = SettingsConfigDict(env_prefix="KAGE_MEMORY_")
    
    persistent_path: Path = Path.home() / ".kage" / "memory"
    compaction_threshold: float = 0.8
    max_history_messages: int = 50
    embedding_model: str = "all-MiniLM-L6-v2"


class ToolSettings(BaseSettings):
    """Tool execution configuration."""
    
    model_config = SettingsConfigDict(env_prefix="KAGE_TOOL_")
    
    sandbox_enabled: bool = False  # Disabled by default (firejail is Linux-only)
    sandbox_type: Literal["docker", "firejail", "none"] = "none"
    bash_timeout: int = 30
    code_exec_timeout: int = 60
    max_file_size: int = 10 * 1024 * 1024


class KnowledgeSettings(BaseSettings):
    """Knowledge base configuration."""
    
    model_config = SettingsConfigDict(env_prefix="KAGE_KNOWLEDGE_")
    
    chroma_path: Path = Path.home() / ".kage" / "chroma"
    docs_cache_path: Path = Path.home() / ".kage" / "docs_cache"
    index_extensions: list[str] = Field(
        default=[".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".md", ".yaml", ".yml", ".json", ".toml"]
    )
    ignore_patterns: list[str] = Field(
        default=["node_modules", ".git", "__pycache__", ".venv", "dist", "build", ".next", "target"]
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


settings = Settings()
