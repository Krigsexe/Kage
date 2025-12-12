"""Documentation fetching tool."""

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from kage.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from kage.config.settings import settings


# Common documentation URLs for popular libraries
DOC_SOURCES = {
    "python": "https://docs.python.org/3/library/{module}.html",
    "fastapi": "https://fastapi.tiangolo.com/",
    "pydantic": "https://docs.pydantic.dev/latest/",
    "typer": "https://typer.tiangolo.com/",
    "rich": "https://rich.readthedocs.io/en/latest/",
    "httpx": "https://www.python-httpx.org/",
    "pytest": "https://docs.pytest.org/en/latest/",
    "ollama": "https://ollama.com/library",
    "chromadb": "https://docs.trychroma.com/",
}


class DocsFetchTool(BaseTool):
    """Fetch documentation from official sources."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="doc_fetch",
            description="Fetch documentation for a library or module. Always use this before using an unfamiliar API.",
            category=ToolCategory.DOCUMENTATION,
            parameters=[
                ToolParameter(
                    name="library",
                    type="string",
                    description="Library name (e.g., 'fastapi', 'pydantic', 'httpx')",
                ),
                ToolParameter(
                    name="topic",
                    type="string",
                    description="Specific topic or function to look up (optional)",
                    required=False,
                ),
                ToolParameter(
                    name="url",
                    type="string",
                    description="Direct URL to fetch (overrides library/topic)",
                    required=False,
                ),
            ],
        )

    async def execute(
        self,
        library: str = "",
        topic: str = "",
        url: str = "",
    ) -> ToolResult:
        # Check cache first
        cache_key = f"{library}_{topic}" if not url else urlparse(url).netloc
        cached = self._get_cached(cache_key)
        if cached:
            return ToolResult(
                success=True,
                output=f"[Cached]\n{cached}",
                metadata={"source": "cache", "key": cache_key},
            )

        # Determine URL to fetch
        if url:
            fetch_url = url
        elif library.lower() in DOC_SOURCES:
            fetch_url = DOC_SOURCES[library.lower()]
        else:
            # Try PyPI for package info
            fetch_url = f"https://pypi.org/pypi/{library}/json"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    fetch_url,
                    headers={
                        "User-Agent": "KAGE/0.1 Documentation Fetcher"
                    },
                    follow_redirects=True,
                )
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")

                if "application/json" in content_type:
                    # PyPI JSON response
                    data = response.json()
                    output = self._format_pypi(data)
                else:
                    # HTML documentation
                    output = self._extract_text(response.text, topic)

                # Cache the result
                self._cache_result(cache_key, output)

                return ToolResult(
                    success=True,
                    output=output[:10000],  # Limit output size
                    metadata={
                        "url": fetch_url,
                        "library": library,
                        "topic": topic,
                    },
                )

        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                output="",
                error="Documentation fetch timed out",
            )
        except httpx.HTTPError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to fetch documentation: {str(e)}",
            )

    def _extract_text(self, html: str, topic: str = "") -> str:
        """Extract readable text from HTML documentation."""
        # Remove scripts and styles
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)

        # Remove HTML tags but keep structure
        text = re.sub(r'<h[1-6][^>]*>', '\n## ', html)
        text = re.sub(r'</h[1-6]>', '\n', text)
        text = re.sub(r'<p[^>]*>', '\n', text)
        text = re.sub(r'<li[^>]*>', '\n- ', text)
        text = re.sub(r'<br[^>]*/?>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)

        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'  +', ' ', text)

        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')

        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # If topic specified, try to find relevant section
        if topic:
            topic_lower = topic.lower()
            relevant_start = -1
            for i, line in enumerate(lines):
                if topic_lower in line.lower():
                    relevant_start = max(0, i - 2)
                    break

            if relevant_start >= 0:
                lines = lines[relevant_start:relevant_start + 50]

        return '\n'.join(lines[:100])  # Limit to 100 lines

    def _format_pypi(self, data: dict) -> str:
        """Format PyPI JSON response."""
        info = data.get("info", {})
        lines = [
            f"# {info.get('name', 'Unknown')}",
            f"Version: {info.get('version', 'Unknown')}",
            f"Summary: {info.get('summary', 'No summary')}",
            "",
            f"Author: {info.get('author', 'Unknown')}",
            f"License: {info.get('license', 'Unknown')}",
            f"Home: {info.get('home_page', 'N/A')}",
            f"Docs: {info.get('project_urls', {}).get('Documentation', 'N/A')}",
            "",
            "## Description",
            info.get('description', 'No description')[:2000],
        ]
        return '\n'.join(lines)

    def _get_cached(self, key: str) -> str | None:
        """Get cached documentation."""
        cache_path = settings.knowledge.docs_cache_path / f"{key}.txt"
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8")
        return None

    def _cache_result(self, key: str, content: str) -> None:
        """Cache documentation result."""
        settings.knowledge.docs_cache_path.mkdir(parents=True, exist_ok=True)
        cache_path = settings.knowledge.docs_cache_path / f"{key}.txt"
        cache_path.write_text(content, encoding="utf-8")
