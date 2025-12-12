"""Persistent memory - Cross-session storage using SQLite."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from kage.config.settings import settings


class PersistentMemory:
    """Cross-session persistent memory using SQLite.

    Stores:
    - Project profile (stack, conventions)
    - Architectural decisions
    - Past errors and solutions
    - User preferences
    """

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path or Path.cwd()
        self.db_path = self._get_db_path()
        self._ensure_tables()

    def _get_db_path(self) -> Path:
        """Get database path for this project."""
        kage_dir = self.project_path / ".kage"
        kage_dir.mkdir(parents=True, exist_ok=True)
        return kage_dir / "memory.db"

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _ensure_tables(self) -> None:
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            conn.executescript("""
                -- Project profile
                CREATE TABLE IF NOT EXISTS project_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Architectural decisions
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision TEXT NOT NULL,
                    context TEXT,
                    created_at TEXT NOT NULL
                );

                -- Past errors and solutions
                CREATE TABLE IF NOT EXISTS error_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error TEXT NOT NULL,
                    solution TEXT,
                    file_path TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL
                );

                -- Key-value store for misc data
                CREATE TABLE IF NOT EXISTS store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Session summaries
                CREATE TABLE IF NOT EXISTS session_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    summary TEXT NOT NULL,
                    files_modified TEXT,
                    created_at TEXT NOT NULL
                );
            """)

    # Profile management
    def set_profile(self, key: str, value: Any) -> None:
        """Set a project profile value."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO project_profile (key, value, updated_at)
                   VALUES (?, ?, ?)""",
                (key, json.dumps(value), datetime.now().isoformat()),
            )

    def get_profile(self, key: str, default: Any = None) -> Any:
        """Get a project profile value."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM project_profile WHERE key = ?", (key,)
            ).fetchone()
            if row:
                return json.loads(row["value"])
            return default

    def get_all_profile(self) -> dict[str, Any]:
        """Get all profile values."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM project_profile").fetchall()
            return {row["key"]: json.loads(row["value"]) for row in rows}

    # Decision tracking
    def record_decision(self, decision: str, context: str = "") -> int:
        """Record an architectural decision."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO decisions (decision, context, created_at)
                   VALUES (?, ?, ?)""",
                (decision, context, datetime.now().isoformat()),
            )
            return cursor.lastrowid or 0

    def get_decisions(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent decisions."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT decision, context, created_at FROM decisions
                   ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    # Error tracking
    def record_error(
        self,
        error: str,
        solution: str | None = None,
        file_path: str | None = None,
    ) -> int:
        """Record an error and optional solution."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO error_history (error, solution, file_path, resolved, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    error,
                    solution,
                    file_path,
                    solution is not None,
                    datetime.now().isoformat(),
                ),
            )
            return cursor.lastrowid or 0

    def resolve_error(self, error_id: int, solution: str) -> None:
        """Mark an error as resolved with solution."""
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE error_history SET solution = ?, resolved = TRUE
                   WHERE id = ?""",
                (solution, error_id),
            )

    def get_similar_errors(self, error: str, limit: int = 5) -> list[dict[str, Any]]:
        """Find similar past errors (simple keyword matching)."""
        keywords = error.lower().split()[:5]  # First 5 words
        with self._get_connection() as conn:
            results = []
            for keyword in keywords:
                if len(keyword) > 3:
                    rows = conn.execute(
                        """SELECT error, solution, file_path, resolved, created_at
                           FROM error_history
                           WHERE error LIKE ? AND resolved = TRUE
                           LIMIT ?""",
                        (f"%{keyword}%", limit),
                    ).fetchall()
                    results.extend(dict(row) for row in rows)
            # Deduplicate
            seen = set()
            unique = []
            for r in results:
                if r["error"] not in seen:
                    seen.add(r["error"])
                    unique.append(r)
            return unique[:limit]

    # Key-value store
    def set(self, key: str, value: Any) -> None:
        """Set a value in the store."""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO store (key, value, updated_at)
                   VALUES (?, ?, ?)""",
                (key, json.dumps(value), datetime.now().isoformat()),
            )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the store."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM store WHERE key = ?", (key,)
            ).fetchone()
            if row:
                return json.loads(row["value"])
            return default

    # Session summaries
    def save_session_summary(
        self,
        summary: str,
        files_modified: list[str] | None = None,
    ) -> int:
        """Save a session summary."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO session_summaries (summary, files_modified, created_at)
                   VALUES (?, ?, ?)""",
                (
                    summary,
                    json.dumps(files_modified or []),
                    datetime.now().isoformat(),
                ),
            )
            return cursor.lastrowid or 0

    def get_recent_summaries(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent session summaries."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT summary, files_modified, created_at FROM session_summaries
                   ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [
                {
                    "summary": row["summary"],
                    "files_modified": json.loads(row["files_modified"]),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def get_context_for_llm(self) -> str:
        """Get formatted context for LLM system prompt."""
        lines = ["## Project Memory\n"]

        # Profile
        profile = self.get_all_profile()
        if profile:
            lines.append("### Profile")
            for key, value in profile.items():
                lines.append(f"- {key}: {value}")
            lines.append("")

        # Recent decisions
        decisions = self.get_decisions(5)
        if decisions:
            lines.append("### Recent Decisions")
            for d in decisions:
                lines.append(f"- {d['decision']}")
            lines.append("")

        # Recent summaries
        summaries = self.get_recent_summaries(2)
        if summaries:
            lines.append("### Previous Sessions")
            for s in summaries:
                lines.append(f"- [{s['created_at'][:10]}] {s['summary'][:200]}...")
            lines.append("")

        return "\n".join(lines)
