"""Documentation cache management."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from kage.config.settings import settings


class DocsCache:
    """Manages cached documentation.

    Features:
    - TTL-based expiration
    - Simple text search
    - Metadata tracking
    """

    # Cache expiration in seconds (7 days)
    DEFAULT_TTL = 7 * 24 * 60 * 60

    def __init__(self):
        self.cache_path = settings.knowledge.docs_cache_path
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.cache_path / "_index.json"
        self._index: dict[str, Any] = self._load_index()

    def _load_index(self) -> dict[str, Any]:
        """Load cache index."""
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save_index(self) -> None:
        """Save cache index."""
        self.index_path.write_text(json.dumps(self._index, indent=2))

    def _make_key(self, identifier: str) -> str:
        """Generate cache key from identifier."""
        return hashlib.md5(identifier.encode()).hexdigest()[:16]

    def get(self, identifier: str) -> dict[str, Any] | None:
        """Get cached documentation by identifier.

        Args:
            identifier: Library name, URL, or custom key

        Returns:
            Cached data or None if not found/expired
        """
        key = self._make_key(identifier)

        if key not in self._index:
            return None

        entry = self._index[key]

        # Check expiration
        if time.time() > entry.get("expires_at", 0):
            self.delete(identifier)
            return None

        # Read content file
        content_path = self.cache_path / f"{key}.txt"
        if not content_path.exists():
            return None

        return {
            "content": content_path.read_text(encoding="utf-8"),
            "title": entry.get("title", identifier),
            "url": entry.get("url", ""),
            "cached_at": entry.get("cached_at", 0),
            "identifier": identifier,
        }

    def set(
        self,
        identifier: str,
        content: str,
        title: str = "",
        url: str = "",
        ttl: int | None = None,
    ) -> str:
        """Cache documentation.

        Args:
            identifier: Library name, URL, or custom key
            content: Documentation content
            title: Human-readable title
            url: Source URL
            ttl: Time-to-live in seconds

        Returns:
            Cache key
        """
        key = self._make_key(identifier)
        ttl = ttl or self.DEFAULT_TTL

        # Update index
        self._index[key] = {
            "identifier": identifier,
            "title": title or identifier,
            "url": url,
            "cached_at": time.time(),
            "expires_at": time.time() + ttl,
            "size": len(content),
        }
        self._save_index()

        # Write content
        content_path = self.cache_path / f"{key}.txt"
        content_path.write_text(content, encoding="utf-8")

        return key

    def delete(self, identifier: str) -> bool:
        """Delete cached documentation."""
        key = self._make_key(identifier)

        if key not in self._index:
            return False

        del self._index[key]
        self._save_index()

        content_path = self.cache_path / f"{key}.txt"
        if content_path.exists():
            content_path.unlink()

        return True

    def search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Search cached documentation.

        Simple keyword search in titles and content.
        """
        query_lower = query.lower()
        keywords = query_lower.split()
        results = []

        for key, entry in self._index.items():
            # Check expiration
            if time.time() > entry.get("expires_at", 0):
                continue

            score = 0

            # Check title
            title_lower = entry.get("title", "").lower()
            for keyword in keywords:
                if keyword in title_lower:
                    score += 2

            # Check identifier
            id_lower = entry.get("identifier", "").lower()
            for keyword in keywords:
                if keyword in id_lower:
                    score += 1

            if score > 0:
                # Read content for snippet
                content_path = self.cache_path / f"{key}.txt"
                content = ""
                if content_path.exists():
                    try:
                        content = content_path.read_text(encoding="utf-8")[:500]
                    except IOError:
                        pass

                results.append({
                    "title": entry.get("title", ""),
                    "url": entry.get("url", ""),
                    "content": content,
                    "identifier": entry.get("identifier", ""),
                    "score": score,
                })

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max_results]

    def list_all(self) -> list[dict[str, Any]]:
        """List all cached documentation."""
        items = []
        current_time = time.time()

        for key, entry in self._index.items():
            is_expired = current_time > entry.get("expires_at", 0)
            items.append({
                "identifier": entry.get("identifier", ""),
                "title": entry.get("title", ""),
                "url": entry.get("url", ""),
                "size": entry.get("size", 0),
                "cached_at": entry.get("cached_at", 0),
                "expired": is_expired,
            })

        return items

    def clear_expired(self) -> int:
        """Remove all expired entries."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._index.items()
            if current_time > entry.get("expires_at", 0)
        ]

        for key in expired_keys:
            identifier = self._index[key].get("identifier", "")
            if identifier:
                self.delete(identifier)

        return len(expired_keys)

    def clear_all(self) -> int:
        """Clear entire cache."""
        count = len(self._index)

        # Remove all content files
        for key in self._index:
            content_path = self.cache_path / f"{key}.txt"
            if content_path.exists():
                content_path.unlink()

        # Clear index
        self._index = {}
        self._save_index()

        return count

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_size = sum(e.get("size", 0) for e in self._index.values())
        current_time = time.time()
        expired_count = sum(
            1 for e in self._index.values()
            if current_time > e.get("expires_at", 0)
        )

        return {
            "total_entries": len(self._index),
            "expired_entries": expired_count,
            "total_size_bytes": total_size,
            "cache_path": str(self.cache_path),
        }
