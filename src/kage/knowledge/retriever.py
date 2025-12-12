"""RAG Retrieval - Retrieve relevant context for queries."""

from pathlib import Path
from typing import Any

from kage.config.settings import settings
from kage.knowledge.indexer import CodebaseIndexer
from kage.knowledge.docs_cache import DocsCache


class KnowledgeRetriever:
    """Retrieves relevant knowledge for LLM context.

    Combines:
    - Codebase search (ChromaDB)
    - Documentation cache
    - File content
    """

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path or Path.cwd()
        self.indexer = CodebaseIndexer(self.project_path)
        self.docs_cache = DocsCache()

    def retrieve(
        self,
        query: str,
        max_results: int = 5,
        include_docs: bool = True,
    ) -> dict[str, Any]:
        """Retrieve relevant context for a query.

        Returns a structured context with:
        - Code snippets
        - Documentation
        - Related files
        """
        context = {
            "code_snippets": [],
            "documentation": [],
            "related_files": set(),
        }

        # Search codebase
        try:
            code_results = self.indexer.search(query, n_results=max_results)
            for result in code_results:
                context["code_snippets"].append({
                    "content": result["content"],
                    "file": result["file_path"],
                    "lines": f"{result['start_line']}-{result['end_line']}",
                    "language": result["language"],
                    "score": result["score"],
                })
                context["related_files"].add(result["file_path"])
        except Exception:
            pass  # ChromaDB not available or not indexed

        # Get cached documentation if requested
        if include_docs:
            doc_results = self.docs_cache.search(query, max_results=3)
            context["documentation"] = doc_results

        context["related_files"] = list(context["related_files"])
        return context

    def get_file_context(
        self,
        file_path: str,
        include_related: bool = True,
        max_related: int = 3,
    ) -> dict[str, Any]:
        """Get context for a specific file.

        Includes:
        - File content summary
        - Related files (imports, references)
        - Relevant documentation
        """
        full_path = self.project_path / file_path

        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            content = full_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, IOError):
            return {"error": f"Cannot read file: {file_path}"}

        context = {
            "file_path": file_path,
            "content": content[:5000],  # First 5000 chars
            "lines": len(content.split("\n")),
            "size": len(content),
            "related_files": [],
            "imports": [],
        }

        # Extract imports (Python)
        if file_path.endswith(".py"):
            imports = self._extract_python_imports(content)
            context["imports"] = imports

            # Find related files based on imports
            if include_related:
                for imp in imports[:max_related]:
                    related_path = self._resolve_import(imp)
                    if related_path:
                        context["related_files"].append(related_path)

        return context

    def _extract_python_imports(self, content: str) -> list[str]:
        """Extract import statements from Python code."""
        imports = []
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("import "):
                parts = line[7:].split(",")
                imports.extend(p.strip().split()[0] for p in parts)
            elif line.startswith("from "):
                parts = line.split()
                if len(parts) >= 2:
                    imports.append(parts[1])
        return imports

    def _resolve_import(self, import_name: str) -> str | None:
        """Try to resolve an import to a local file."""
        # Convert module path to file path
        parts = import_name.split(".")
        potential_paths = [
            self.project_path / "/".join(parts) / "__init__.py",
            self.project_path / ("/".join(parts) + ".py"),
            self.project_path / "src" / "/".join(parts) / "__init__.py",
            self.project_path / "src" / ("/".join(parts) + ".py"),
        ]

        for path in potential_paths:
            if path.exists():
                try:
                    return str(path.relative_to(self.project_path))
                except ValueError:
                    return str(path)

        return None

    def format_for_llm(self, context: dict[str, Any]) -> str:
        """Format retrieved context for LLM consumption."""
        lines = []

        # Code snippets
        if context.get("code_snippets"):
            lines.append("## Relevant Code\n")
            for snippet in context["code_snippets"][:3]:
                lines.append(f"### {snippet['file']} ({snippet['lines']})")
                lines.append(f"```{snippet['language']}")
                lines.append(snippet["content"][:1000])
                lines.append("```\n")

        # Documentation
        if context.get("documentation"):
            lines.append("## Documentation\n")
            for doc in context["documentation"][:2]:
                lines.append(f"### {doc.get('title', 'Doc')}")
                lines.append(doc.get("content", "")[:500])
                lines.append("")

        # Related files
        if context.get("related_files"):
            lines.append("## Related Files")
            for f in context["related_files"][:5]:
                lines.append(f"- {f}")

        return "\n".join(lines)
