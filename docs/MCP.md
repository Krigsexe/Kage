# MCP Protocol Specification

KAGE tools follow the Model Context Protocol (MCP) specification for interoperability.

## Overview

MCP is a standard for AI tool interfaces that enables:
- Consistent tool definitions
- Standardized parameter schemas
- Predictable result formats

## Tool Definition Schema

```json
{
  "name": "tool_name",
  "description": "Human-readable description",
  "category": "filesystem|execution|vcs|search|docs|testing|security",
  "parameters": [
    {
      "name": "param_name",
      "type": "string|integer|boolean|array|object",
      "description": "Parameter description",
      "required": true,
      "default": null,
      "enum": ["option1", "option2"]
    }
  ],
  "dangerous": false,
  "requires_sandbox": false
}
```

## Tool Result Schema

```json
{
  "success": true,
  "output": "Result content",
  "error": null,
  "metadata": {
    "key": "value"
  }
}
```

## LLM Message Format

When an LLM wants to call a tool:
```json
{"tool": "file_read", "args": {"path": "src/main.py"}}
```

Tool result returned to LLM:
```
[OK] Tool executed successfully:
<result content>
```

Or on error:
```
[FAIL] Tool execution failed:
Error: <error message>
Output: <any partial output>
```

## Python Implementation

### Tool Definition

```python
from kage.tools.base import (
    BaseTool,
    ToolDefinition,
    ToolParameter,
    ToolCategory,
    ToolResult,
)

class ExampleTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="example",
            description="An example tool",
            category=ToolCategory.FILESYSTEM,
            parameters=[
                ToolParameter(
                    name="input",
                    type="string",
                    description="Input value",
                    required=True,
                ),
                ToolParameter(
                    name="count",
                    type="integer",
                    description="Number of items",
                    required=False,
                    default=10,
                ),
            ],
            dangerous=False,
            requires_sandbox=False,
        )

    async def execute(self, input: str, count: int = 10) -> ToolResult:
        try:
            result = process(input, count)
            return ToolResult(
                success=True,
                output=result,
                metadata={"processed": count},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )
```

### Tool Registration

```python
from kage.tools.registry import ToolRegistry

registry = ToolRegistry()
registry.register(ExampleTool())

# Get tool by name
tool = registry.get("example")

# Execute
result = await tool.safe_execute(input="test", count=5)
```

## MCP Server Mode

KAGE can run as an MCP server for integration with other tools:

```bash
kage mcp serve --port 3000
```

### JSON-RPC Interface

**List tools:**
```json
{"jsonrpc": "2.0", "method": "tools/list", "id": 1}
```

**Execute tool:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "file_read",
    "arguments": {"path": "src/main.py"}
  },
  "id": 2
}
```

## Categories

| Category | Description |
|----------|-------------|
| filesystem | File operations |
| execution | Code/command execution |
| vcs | Version control |
| search | Web/codebase search |
| docs | Documentation |
| testing | Test runners |
| security | Security scanning |

## Security Considerations

### Dangerous Tools
Tools marked as `dangerous=True` require user confirmation before execution.

Examples:
- file_write
- file_edit
- bash (destructive commands)
- git commit/push

### Sandboxed Tools
Tools marked as `requires_sandbox=True` should run in isolated environments.

Sandbox options:
- firejail (Linux)
- Docker container
- VM isolation

## Error Handling

Tools should:
1. Validate all parameters
2. Return descriptive errors
3. Never crash the agent

```python
async def safe_execute(self, **kwargs) -> ToolResult:
    # Validate parameters
    valid, error = self.validate_params(kwargs)
    if not valid:
        return ToolResult(success=False, output="", error=error)

    # Execute with error handling
    try:
        return await self.execute(**kwargs)
    except Exception as e:
        return ToolResult(
            success=False,
            output="",
            error=f"{type(e).__name__}: {str(e)}"
        )
```
