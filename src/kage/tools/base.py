"""Base tool interface - MCP compatible."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

from pydantic import BaseModel


class ToolCategory(str, Enum):
    """Tool categories for organization."""
    
    FILESYSTEM = "filesystem"
    CODE_EXECUTION = "code_execution"
    GIT = "git"
    SEARCH = "search"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    SECURITY = "security"


class ToolParameter(BaseModel):
    """Tool parameter definition (MCP-compatible)."""
    
    name: str
    type: str
    description: str
    required: bool = True
    default: Any | None = None
    enum: list[str] | None = None


class ToolDefinition(BaseModel):
    """Tool definition for LLM function calling (MCP-compatible)."""
    
    name: str
    description: str
    category: ToolCategory
    parameters: list[ToolParameter]
    dangerous: bool = False
    requires_sandbox: bool = False


@dataclass
class ToolResult:
    """Result of tool execution."""
    
    success: bool
    output: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_llm_message(self) -> str:
        """Format for LLM consumption."""
        if self.success:
            return f"[OK] Tool executed successfully:\n{self.output}"
        else:
            return f"[FAIL] Tool execution failed:\nError: {self.error}\nOutput: {self.output}"


class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return tool definition for LLM."""
        ...
    
    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given parameters."""
        ...
    
    def validate_params(self, kwargs: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate parameters against definition."""
        for param in self.definition.parameters:
            if param.required and param.name not in kwargs:
                return False, f"Missing required parameter: {param.name}"
        return True, None
    
    async def safe_execute(self, **kwargs: Any) -> ToolResult:
        """Execute with validation and error handling."""
        valid, error = self.validate_params(kwargs)
        if not valid:
            return ToolResult(success=False, output="", error=error)
        
        try:
            return await self.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"{type(e).__name__}: {str(e)}"
            )


ToolFactory = Callable[[], BaseTool]
T = TypeVar("T", bound=BaseTool)


def tool(
    name: str,
    description: str,
    category: ToolCategory,
    dangerous: bool = False,
    requires_sandbox: bool = False,
) -> Callable[[type[T]], type[T]]:
    """Decorator to register a tool class."""
    def decorator(cls: type[T]) -> type[T]:
        cls._tool_meta = {
            "name": name,
            "description": description,
            "category": category,
            "dangerous": dangerous,
            "requires_sandbox": requires_sandbox,
        }
        return cls
    return decorator
