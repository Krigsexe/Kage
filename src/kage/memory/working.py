"""Working memory - Context window management."""

from dataclasses import dataclass, field
from typing import Any

import tiktoken

from kage.llm.base import Message
from kage.config.settings import settings


@dataclass
class WorkingMemory:
    """Manages the LLM's context window (working memory).

    Responsible for:
    - Message history management
    - Token counting
    - Context window tracking
    - Auto-compaction trigger detection
    """

    system_prompt: str = ""
    messages: list[Message] = field(default_factory=list)
    _encoding: Any = field(default=None, repr=False)
    _token_cache: dict[int, int] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        """Initialize tokenizer."""
        self._encoding = tiktoken.get_encoding("cl100k_base")

    @property
    def context_window(self) -> int:
        """Get configured context window size."""
        return settings.llm.context_window

    @property
    def compaction_threshold(self) -> int:
        """Get token count threshold for compaction."""
        return int(self.context_window * settings.memory.compaction_threshold)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self._encoding.encode(text))

    def count_message_tokens(self, message: Message) -> int:
        """Count tokens in a message (with caching)."""
        msg_hash = hash((message.role, message.content))
        if msg_hash not in self._token_cache:
            # Add overhead for role markers
            overhead = 4  # ~4 tokens for role markers
            self._token_cache[msg_hash] = self.count_tokens(message.content) + overhead
        return self._token_cache[msg_hash]

    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        system_tokens = self.count_tokens(self.system_prompt) if self.system_prompt else 0
        message_tokens = sum(self.count_message_tokens(m) for m in self.messages)
        return system_tokens + message_tokens

    @property
    def usage_percent(self) -> float:
        """Get context window usage percentage."""
        return (self.total_tokens / self.context_window) * 100

    @property
    def needs_compaction(self) -> bool:
        """Check if compaction is needed."""
        return self.total_tokens >= self.compaction_threshold

    @property
    def available_tokens(self) -> int:
        """Get available token space."""
        return max(0, self.context_window - self.total_tokens)

    def add_message(self, message: Message) -> None:
        """Add a message to history."""
        self.messages.append(message)
        # Clear cache for memory management
        if len(self._token_cache) > 1000:
            self._token_cache.clear()

    def add_user_message(self, content: str) -> None:
        """Add a user message."""
        self.add_message(Message(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message."""
        self.add_message(Message(role="assistant", content=content))

    def add_tool_result(self, tool_name: str, result: str, success: bool = True) -> None:
        """Add a tool result message."""
        self.add_message(Message(
            role="tool",
            content=result,
            metadata={"tool": tool_name, "success": success},
        ))

    def get_messages_for_llm(self) -> list[Message]:
        """Get messages formatted for LLM API."""
        result = []

        if self.system_prompt:
            result.append(Message(role="system", content=self.system_prompt))

        result.extend(self.messages)
        return result

    def get_last_n_messages(self, n: int) -> list[Message]:
        """Get the last n messages."""
        return self.messages[-n:] if n < len(self.messages) else self.messages[:]

    def get_last_user_message(self) -> Message | None:
        """Get the most recent user message."""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg
        return None

    def get_last_assistant_message(self) -> Message | None:
        """Get the most recent assistant message."""
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                return msg
        return None

    def clear(self) -> None:
        """Clear all messages (keep system prompt)."""
        self.messages.clear()
        self._token_cache.clear()

    def truncate_to_tokens(self, max_tokens: int) -> list[Message]:
        """Truncate messages to fit within token limit.

        Keeps system prompt and removes oldest messages first.
        """
        system_tokens = self.count_tokens(self.system_prompt) if self.system_prompt else 0
        available = max_tokens - system_tokens

        result = []
        current_tokens = 0

        # Work backwards to keep recent messages
        for msg in reversed(self.messages):
            msg_tokens = self.count_message_tokens(msg)
            if current_tokens + msg_tokens <= available:
                result.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break

        return result

    def replace_messages(self, new_messages: list[Message]) -> None:
        """Replace all messages (used after compaction)."""
        self.messages = new_messages
        self._token_cache.clear()

    def get_status(self) -> dict[str, Any]:
        """Get memory status information."""
        return {
            "total_tokens": self.total_tokens,
            "context_window": self.context_window,
            "usage_percent": round(self.usage_percent, 1),
            "available_tokens": self.available_tokens,
            "needs_compaction": self.needs_compaction,
            "message_count": len(self.messages),
        }

    def __len__(self) -> int:
        """Get message count."""
        return len(self.messages)

    def __repr__(self) -> str:
        return (
            f"WorkingMemory(messages={len(self.messages)}, "
            f"tokens={self.total_tokens}/{self.context_window}, "
            f"usage={self.usage_percent:.1f}%)"
        )
