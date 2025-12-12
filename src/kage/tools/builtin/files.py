"""File system tools - read, write, list, edit."""

from pathlib import Path

import aiofiles

from kage.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from kage.config.settings import settings


class FileReadTool(BaseTool):
    """Read file contents."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_read",
            description="Read the contents of a file. Use this BEFORE assuming file contents.",
            category=ToolCategory.FILESYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Absolute or relative path to the file",
                ),
                ToolParameter(
                    name="start_line",
                    type="integer",
                    description="Start line (1-indexed, optional)",
                    required=False,
                ),
                ToolParameter(
                    name="end_line",
                    type="integer",
                    description="End line (inclusive, optional)",
                    required=False,
                ),
            ],
        )
    
    async def execute(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> ToolResult:
        file_path = Path(path).resolve()
        
        if not file_path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"File not found: {path}",
            )
        
        if file_path.stat().st_size > settings.tools.max_file_size:
            return ToolResult(
                success=False,
                output="",
                error=f"File too large (>{settings.tools.max_file_size} bytes)",
            )
        
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                lines = await f.readlines()
            
            if start_line is not None or end_line is not None:
                start = (start_line or 1) - 1
                end = end_line or len(lines)
                lines = lines[start:end]
                
                numbered = [
                    f"{i + start + 1:4d} | {line.rstrip()}"
                    for i, line in enumerate(lines)
                ]
                content = "\n".join(numbered)
            else:
                content = "".join(lines)
            
            return ToolResult(
                success=True,
                output=content,
                metadata={"path": str(file_path), "lines": len(lines)},
            )
        
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                output="",
                error="File is not valid UTF-8 text",
            )


class FileWriteTool(BaseTool):
    """Write content to a file."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_write",
            description="Create or overwrite a file with new content.",
            category=ToolCategory.FILESYSTEM,
            dangerous=True,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to create/overwrite",
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write to the file",
                ),
            ],
        )
    
    async def execute(self, path: str, content: str) -> ToolResult:
        file_path = Path(path).resolve()
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)
            
            return ToolResult(
                success=True,
                output=f"File written: {file_path} ({len(content)} bytes)",
                metadata={"path": str(file_path), "bytes": len(content)},
            )
        
        except PermissionError:
            return ToolResult(
                success=False,
                output="",
                error=f"Permission denied: {path}",
            )


class FileEditTool(BaseTool):
    """Edit file using str_replace pattern."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_edit",
            description="Edit a file by replacing a unique string. The old_str must appear EXACTLY ONCE.",
            category=ToolCategory.FILESYSTEM,
            dangerous=True,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to edit",
                ),
                ToolParameter(
                    name="old_str",
                    type="string",
                    description="Exact string to replace (must be unique in file)",
                ),
                ToolParameter(
                    name="new_str",
                    type="string",
                    description="Replacement string (empty to delete)",
                    required=False,
                    default="",
                ),
            ],
        )
    
    async def execute(
        self,
        path: str,
        old_str: str,
        new_str: str = "",
    ) -> ToolResult:
        file_path = Path(path).resolve()
        
        if not file_path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"File not found: {path}",
            )
        
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
            
            count = content.count(old_str)
            if count == 0:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"String not found in file. Searched for:\n{old_str[:200]}...",
                )
            if count > 1:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"String appears {count} times (must be unique). Be more specific.",
                )
            
            new_content = content.replace(old_str, new_str, 1)
            
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(new_content)
            
            return ToolResult(
                success=True,
                output=f"Edited {file_path}: replaced {len(old_str)} chars with {len(new_str)} chars",
                metadata={
                    "path": str(file_path),
                    "old_len": len(old_str),
                    "new_len": len(new_str),
                },
            )
        
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                output="",
                error="File is not valid UTF-8 text",
            )


class DirectoryListTool(BaseTool):
    """List directory contents."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="dir_list",
            description="List files and directories in a path.",
            category=ToolCategory.FILESYSTEM,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Directory path to list",
                ),
                ToolParameter(
                    name="depth",
                    type="integer",
                    description="Max depth to recurse (default 2)",
                    required=False,
                    default=2,
                ),
            ],
        )
    
    async def execute(self, path: str, depth: int = 2) -> ToolResult:
        dir_path = Path(path).resolve()
        
        if not dir_path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"Directory not found: {path}",
            )
        
        if not dir_path.is_dir():
            return ToolResult(
                success=False,
                output="",
                error=f"Not a directory: {path}",
            )
        
        ignore = set(settings.knowledge.ignore_patterns)
        
        def list_recursive(p: Path, current_depth: int, prefix: str = "") -> list[str]:
            if current_depth > depth:
                return []
            
            lines = []
            try:
                entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                return [f"{prefix}[permission denied]"]
            
            for entry in entries:
                if entry.name in ignore or entry.name.startswith("."):
                    continue
                
                if entry.is_dir():
                    lines.append(f"{prefix}[D] {entry.name}/")
                    lines.extend(list_recursive(entry, current_depth + 1, prefix + "  "))
                else:
                    size = entry.stat().st_size
                    size_str = f"{size:,}" if size < 1024 else f"{size // 1024}KB"
                    lines.append(f"{prefix}[F] {entry.name} ({size_str})")
            
            return lines
        
        tree = list_recursive(dir_path, 1)
        output = f"{dir_path}/\n" + "\n".join(tree)
        
        return ToolResult(
            success=True,
            output=output,
            metadata={"path": str(dir_path), "entries": len(tree)},
        )
