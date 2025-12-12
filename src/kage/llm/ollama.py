"""Ollama LLM client implementation."""

import tiktoken
from ollama import AsyncClient

from kage.llm.base import LLMClient, Message
from kage.config.settings import settings


class OllamaClient(LLMClient):
    """Ollama LLM client."""
    
    def __init__(self) -> None:
        self.client = AsyncClient(host=settings.llm.ollama_host)
        self.model = settings.llm.model
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    async def complete(self, prompt: str) -> str:
        """Generate a completion for a single prompt."""
        response = await self.client.generate(
            model=self.model,
            prompt=prompt,
            options={
                "temperature": settings.llm.temperature,
                "num_predict": settings.llm.max_tokens,
            },
        )
        return response["response"]
    
    async def chat(self, messages: list[Message]) -> str:
        """Generate a response for a chat conversation."""
        ollama_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        
        response = await self.client.chat(
            model=self.model,
            messages=ollama_messages,
            options={
                "temperature": settings.llm.temperature,
                "num_predict": settings.llm.max_tokens,
            },
        )
        return response["message"]["content"]
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text (approximation using tiktoken)."""
        return len(self.encoding.encode(text))
    
    async def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            await self.client.list()
            return True
        except Exception:
            return False
    
    async def list_models(self) -> list[str]:
        """List available models."""
        response = await self.client.list()
        return [m["name"] for m in response.get("models", [])]
