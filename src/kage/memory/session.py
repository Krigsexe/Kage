"""Session memory management."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class SessionMemory:
    """Manages session-level memory."""
    
    project_path: Path | None = None
    cwd: Path = field(default_factory=Path.cwd)
    session_start: datetime = field(default_factory=datetime.now)
    modified_files: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    
    def record_file_modification(self, path: str) -> None:
        """Record that a file was modified."""
        if path not in self.modified_files:
            self.modified_files.append(path)

    def get_modified_files(self) -> list[str]:
        """Get list of modified files."""
        return self.modified_files.copy()
    
    def record_error(self, error: str, context: dict[str, Any] | None = None) -> None:
        """Record an error for future reference."""
        self.errors.append({
            "error": error,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
        })
    
    def record_decision(self, decision: str) -> None:
        """Record an architectural or design decision."""
        self.decisions.append(decision)
    
    def set_context(self, key: str, value: Any) -> None:
        """Set a context value."""
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return self.context.get(key, default)
    
    def get_summary(self) -> str:
        """Get a summary of the session."""
        lines = [
            f"Session started: {self.session_start.isoformat()}",
            f"Project: {self.project_path or 'Not set'}",
            f"Working directory: {self.cwd}",
        ]
        
        if self.modified_files:
            lines.append(f"\nModified files ({len(self.modified_files)}):")
            for f in self.modified_files[-10:]:
                lines.append(f"  - {f}")
        
        if self.errors:
            lines.append(f"\nRecent errors ({len(self.errors)}):")
            for e in self.errors[-5:]:
                lines.append(f"  - {e['error'][:100]}")
        
        if self.decisions:
            lines.append(f"\nDecisions ({len(self.decisions)}):")
            for d in self.decisions[-5:]:
                lines.append(f"  - {d}")
        
        return "\n".join(lines)
    
    def save(self, path: Path) -> None:
        """Save session to file."""
        data = {
            "project_path": str(self.project_path) if self.project_path else None,
            "session_start": self.session_start.isoformat(),
            "modified_files": self.modified_files,
            "errors": self.errors,
            "decisions": self.decisions,
            "context": self.context,
        }
        path.write_text(json.dumps(data, indent=2))
    
    @classmethod
    def load(cls, path: Path) -> "SessionMemory":
        """Load session from file."""
        data = json.loads(path.read_text())
        return cls(
            project_path=Path(data["project_path"]) if data.get("project_path") else None,
            session_start=datetime.fromisoformat(data["session_start"]),
            modified_files=data.get("modified_files", []),
            errors=data.get("errors", []),
            decisions=data.get("decisions", []),
            context=data.get("context", {}),
        )
