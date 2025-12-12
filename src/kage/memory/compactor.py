"""Context compaction - YGGDRASIL-inspired memory management."""

from dataclasses import dataclass

import tiktoken

from kage.llm.base import LLMClient, Message
from kage.config.settings import settings


@dataclass
class CompactionResult:
    """Result of context compaction."""
    
    messages: list[Message]
    summary: str
    archived_count: int
    tokens_before: int
    tokens_after: int


SUMMARIZER_PROMPT = """You are a context summarizer. Compress conversation history while preserving critical information.

Given the conversation below, create a concise summary capturing:
1. Key decisions made
2. Files modified or created
3. Errors encountered and their resolutions
4. Current task state
5. Any pending actions

Be factual. No interpretation. Use bullet points.

CONVERSATION:
{conversation}

OUTPUT FORMAT:
## Context Summary
- [key point 1]
- [key point 2]

## Files Touched
- path/to/file.py: [what was done]

## Current State
[brief description]

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
        return sum(len(self.encoding.encode(m.content)) for m in messages)
    
    def needs_compaction(self, messages: list[Message]) -> bool:
        """Check if compaction is needed."""
        return self.count_tokens(messages) >= self.threshold
    
    async def compact(self, messages: list[Message]) -> CompactionResult:
        """Compact messages while preserving critical context."""
        
        tokens_before = self.count_tokens(messages)
        
        preserve_last = 6  # Keep last 3 exchanges
        
        system_msg = messages[0] if messages and messages[0].role == "system" else None
        recent_msgs = messages[-preserve_last:] if len(messages) > preserve_last else messages
        
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
        
        conversation_text = "\n\n".join(
            f"[{m.role.upper()}]: {m.content[:500]}..."
            if len(m.content) > 500 else f"[{m.role.upper()}]: {m.content}"
            for m in to_summarize
        )
        
        prompt = SUMMARIZER_PROMPT.format(conversation=conversation_text)
        
        summary = await self.llm.complete(prompt)
        
        compacted: list[Message] = []
        
        if system_msg:
            compacted.append(system_msg)
        
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
