"""Codebase indexer for semantic search."""

import asyncio
import time
from pathlib import Path
from typing import Any

from kage.config.settings import settings
from kage.knowledge.embeddings import EmbeddingManager


class CodebaseIndexer:
    """Indexes codebase for semantic search using ChromaDB."""

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path or Path.cwd()
        self.embeddings = EmbeddingManager()
        self._collection = None

    @property
    def collection(self):
        """Get or create ChromaDB collection."""
        if self._collection is None:
            try:
                import chromadb
                from chromadb.config import Settings as ChromaSettings

                client = chromadb.PersistentClient(
                    path=str(settings.knowledge.chroma_path),
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                    ),
                )

                # Collection name based on project
                collection_name = self.project_path.name.lower().replace(" ", "_")[:50]

                self._collection = client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            except ImportError:
                raise RuntimeError(
                    "chromadb not installed. "
                    "Run: pip install chromadb"
                )
        return self._collection

    async def index(self) -> dict[str, Any]:
        """Index the entire codebase."""
        start_time = time.time()

        # Find all indexable files
        files = self._find_files()

        if not files:
            return {
                "files": 0,
                "chunks": 0,
                "time": 0,
            }

        # Process files
        all_chunks = []
        all_ids = []
        all_metadata = []

        for file_path in files:
            try:
                chunks = self._chunk_file(file_path)
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{file_path.relative_to(self.project_path)}:{i}"
                    all_chunks.append(chunk["text"])
                    all_ids.append(chunk_id)
                    all_metadata.append({
                        "file_path": str(file_path.relative_to(self.project_path)),
                        "start_line": chunk["start_line"],
                        "end_line": chunk["end_line"],
                        "language": chunk["language"],
                    })
            except Exception:
                continue

        if not all_chunks:
            return {
                "files": len(files),
                "chunks": 0,
                "time": time.time() - start_time,
            }

        # Generate embeddings in batches
        embeddings = self.embeddings.embed_batch(all_chunks)

        # Store in ChromaDB
        self.collection.add(
            ids=all_ids,
            embeddings=embeddings,
            documents=all_chunks,
            metadatas=all_metadata,
        )

        return {
            "files": len(files),
            "chunks": len(all_chunks),
            "time": time.time() - start_time,
        }

    def _find_files(self) -> list[Path]:
        """Find all indexable files."""
        files = []
        ignore = set(settings.knowledge.ignore_patterns)
        extensions = set(settings.knowledge.index_extensions)

        for ext in extensions:
            for file_path in self.project_path.rglob(f"*{ext}"):
                # Check ignore patterns
                if any(p in file_path.parts for p in ignore):
                    continue
                if file_path.is_file():
                    files.append(file_path)

        return files

    def _chunk_file(
        self,
        file_path: Path,
        chunk_size: int = 1000,
        overlap: int = 100,
    ) -> list[dict[str, Any]]:
        """Split file into overlapping chunks."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, IOError):
            return []

        lines = content.split("\n")
        chunks = []
        language = self._detect_language(file_path)

        current_chunk = []
        current_start = 0
        current_size = 0

        for i, line in enumerate(lines):
            line_size = len(line)

            if current_size + line_size > chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    "text": "\n".join(current_chunk),
                    "start_line": current_start + 1,
                    "end_line": i,
                    "language": language,
                })

                # Start new chunk with overlap
                overlap_lines = current_chunk[-5:]  # Keep last 5 lines
                current_chunk = overlap_lines
                current_start = i - len(overlap_lines)
                current_size = sum(len(l) for l in current_chunk)

            current_chunk.append(line)
            current_size += line_size

        # Add final chunk
        if current_chunk:
            chunks.append({
                "text": "\n".join(current_chunk),
                "start_line": current_start + 1,
                "end_line": len(lines),
                "language": language,
            })

        return chunks

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".md": "markdown",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".toml": "toml",
        }
        return ext_to_lang.get(file_path.suffix.lower(), "text")

    def search(
        self,
        query: str,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Search the indexed codebase."""
        query_embedding = self.embeddings.embed(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        formatted = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0

                formatted.append({
                    "content": doc,
                    "file_path": metadata.get("file_path", ""),
                    "start_line": metadata.get("start_line", 0),
                    "end_line": metadata.get("end_line", 0),
                    "language": metadata.get("language", ""),
                    "score": 1 - distance,  # Convert distance to similarity
                })

        return formatted

    def clear(self) -> None:
        """Clear all indexed data."""
        try:
            import chromadb
            client = chromadb.PersistentClient(
                path=str(settings.knowledge.chroma_path),
            )
            collection_name = self.project_path.name.lower().replace(" ", "_")[:50]
            client.delete_collection(collection_name)
            self._collection = None
        except Exception:
            pass
