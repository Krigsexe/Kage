"""Web search tool using DuckDuckGo."""

import re
from typing import Any
from urllib.parse import quote_plus

import httpx

from kage.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo."""

    DDG_URL = "https://html.duckduckgo.com/html/"

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="Search the web using DuckDuckGo. Use for finding documentation, solutions, or current information.",
            category=ToolCategory.SEARCH,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="Maximum number of results (default: 5)",
                    required=False,
                    default=5,
                ),
            ],
        )

    async def execute(
        self,
        query: str,
        max_results: int = 5,
    ) -> ToolResult:
        if not query.strip():
            return ToolResult(
                success=False,
                output="",
                error="Empty search query",
            )

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    self.DDG_URL,
                    data={"q": query},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                )
                response.raise_for_status()

                # Parse results from HTML
                results = self._parse_results(response.text, max_results)

                if not results:
                    return ToolResult(
                        success=True,
                        output="No results found.",
                        metadata={"query": query, "count": 0},
                    )

                # Format output
                lines = [f"Search results for: {query}\n"]
                for i, result in enumerate(results, 1):
                    lines.append(f"{i}. {result['title']}")
                    lines.append(f"   URL: {result['url']}")
                    if result['snippet']:
                        lines.append(f"   {result['snippet'][:200]}")
                    lines.append("")

                return ToolResult(
                    success=True,
                    output="\n".join(lines),
                    metadata={"query": query, "count": len(results)},
                )

        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                output="",
                error="Search request timed out",
            )
        except httpx.HTTPError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"HTTP error: {str(e)}",
            )

    def _parse_results(self, html: str, max_results: int) -> list[dict[str, str]]:
        """Parse DuckDuckGo HTML results."""
        results = []

        # Simple regex parsing for result blocks
        # DuckDuckGo HTML format: <a class="result__a" href="URL">Title</a>
        pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
        snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>([^<]*)</a>'

        matches = re.findall(pattern, html)
        snippets = re.findall(snippet_pattern, html)

        for i, (url, title) in enumerate(matches[:max_results]):
            snippet = snippets[i] if i < len(snippets) else ""
            results.append({
                "url": url,
                "title": self._clean_text(title),
                "snippet": self._clean_text(snippet),
            })

        return results

    def _clean_text(self, text: str) -> str:
        """Clean HTML entities and whitespace."""
        text = re.sub(r'&[^;]+;', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
