"""LLM client base interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    """A conversation message."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    metadata: dict[str, Any] | None = None


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def complete(self, prompt: str) -> str:
        """Generate a completion for a single prompt."""
        ...
    
    @abstractmethod
    async def chat(self, messages: list[Message]) -> str:
        """Generate a response for a chat conversation."""
        ...
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        ...
