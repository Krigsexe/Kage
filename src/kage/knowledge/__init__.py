"""Knowledge Base - Codebase indexing and RAG retrieval."""

from kage.knowledge.indexer import CodebaseIndexer
from kage.knowledge.embeddings import EmbeddingManager
from kage.knowledge.retriever import KnowledgeRetriever
from kage.knowledge.docs_cache import DocsCache

__all__ = [
    "CodebaseIndexer",
    "EmbeddingManager",
    "KnowledgeRetriever",
    "DocsCache",
]
