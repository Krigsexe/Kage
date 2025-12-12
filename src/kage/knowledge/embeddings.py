"""Embedding management for semantic search."""

import hashlib
from pathlib import Path
from typing import Any

from kage.config.settings import settings


class EmbeddingManager:
    """Manages embeddings for semantic search.

    Uses sentence-transformers for local embeddings
    or can optionally use OpenAI embeddings.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.memory.embedding_model
        self._model = None
        self._dimension: int | None = None

    @property
    def model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Run: pip install sentence-transformers"
                )
        return self._model

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            _ = self.model  # Force load
        return self._dimension or 384  # Default for MiniLM

    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def text_hash(self, text: str) -> str:
        """Generate hash for text (for caching)."""
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        import numpy as np
        a = np.array(embedding1)
        b = np.array(embedding2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
