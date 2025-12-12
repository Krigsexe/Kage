"""Tool registry for discovery and management."""

from typing import Any

from kage.tools.base import BaseTool, ToolDefinition


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.definition.name] = tool
    
    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_all(self) -> list[ToolDefinition]:
        """List all registered tool definitions."""
        return [t.definition for t in self._tools.values()]
    
    def get_tools_description(self) -> str:
        """Get formatted description of all tools for LLM."""
        lines = []
        for tool in self._tools.values():
            defn = tool.definition
            params_desc = ", ".join(
                f"{p.name}: {p.type}" + ("" if p.required else "?")
                for p in defn.parameters
            )
            danger = " [!] DANGEROUS" if defn.dangerous else ""
            lines.append(f"- **{defn.name}**({params_desc}){danger}")
            lines.append(f"  {defn.description}")
        return "\n".join(lines)
    
    def get_tools_json_schema(self) -> list[dict[str, Any]]:
        """Get JSON schema for all tools (for function calling)."""
        schemas = []
        for tool in self._tools.values():
            defn = tool.definition
            properties = {}
            required = []
            
            for param in defn.parameters:
                prop: dict[str, Any] = {
                    "type": param.type,
                    "description": param.description,
                }
                if param.enum:
                    prop["enum"] = param.enum
                if param.default is not None:
                    prop["default"] = param.default
                properties[param.name] = prop
                
                if param.required:
                    required.append(param.name)
            
            schemas.append({
                "type": "function",
                "function": {
                    "name": defn.name,
                    "description": defn.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            })
        
        return schemas
    
    def register_builtin(self) -> None:
        """Register all built-in tools."""
        from kage.tools.builtin.files import (
            FileReadTool,
            FileWriteTool,
            FileEditTool,
            DirectoryListTool,
        )
        from kage.tools.builtin.bash import BashTool
        from kage.tools.builtin.git import GitTool
        from kage.tools.builtin.search import WebSearchTool
        from kage.tools.builtin.docs import DocsFetchTool
        from kage.tools.builtin.test import TestRunnerTool
        from kage.tools.builtin.cve import CVECheckTool
        from kage.tools.builtin.code_exec import CodeExecTool

        # Core file operations
        self.register(FileReadTool())
        self.register(FileWriteTool())
        self.register(FileEditTool())
        self.register(DirectoryListTool())

        # Execution
        self.register(BashTool())
        self.register(CodeExecTool())

        # Version control
        self.register(GitTool())

        # Search & Documentation
        self.register(WebSearchTool())
        self.register(DocsFetchTool())

        # Testing & Security
        self.register(TestRunnerTool())
        self.register(CVECheckTool())
