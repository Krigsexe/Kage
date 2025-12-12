# Tools Reference

KAGE includes 11 built-in tools that follow the MCP (Model Context Protocol) specification.

## File System Tools

### file_read

Read file contents.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| path | string | Yes | File path |
| start_line | integer | No | Start line (1-indexed) |
| end_line | integer | No | End line (inclusive) |

**Example:**
```json
{"tool": "file_read", "args": {"path": "src/main.py"}}
{"tool": "file_read", "args": {"path": "src/main.py", "start_line": 10, "end_line": 20}}
```

### file_write

Create or overwrite a file.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| path | string | Yes | File path |
| content | string | Yes | Content to write |

**Dangerous:** Yes (requires confirmation)

### file_edit

Edit a file using str_replace pattern.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| path | string | Yes | File path |
| old_str | string | Yes | Exact string to replace (must be unique) |
| new_str | string | No | Replacement string |

**Dangerous:** Yes

### dir_list

List directory contents.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| path | string | Yes | Directory path |
| depth | integer | No | Max recursion depth (default: 2) |

## Execution Tools

### bash

Execute shell commands.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| command | string | Yes | Command to execute |
| cwd | string | No | Working directory |
| timeout | integer | No | Timeout in seconds (default: 30) |

**Dangerous:** Yes
**Sandboxed:** Yes (when enabled)

**Forbidden commands:**
- `rm -rf /`
- `mkfs`
- Fork bombs
- Direct disk writes

### code_exec

Execute code in a sandboxed environment.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| code | string | Yes | Code to execute |
| language | string | Yes | "python" or "javascript" |
| timeout | integer | No | Timeout in seconds (default: 60) |

**Sandboxed:** Yes

## Version Control Tools

### git

Git operations.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| operation | string | Yes | status, diff, add, commit, log, branch |
| args | string | No | Additional arguments |
| message | string | No | Commit message (for commit) |

**Dangerous:** Yes (for commit, push)

## Search & Documentation Tools

### web_search

Search the web using DuckDuckGo.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | Search query |
| max_results | integer | No | Max results (default: 5) |

### doc_fetch

Fetch documentation from URLs.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| url | string | Yes | Documentation URL |
| selector | string | No | CSS selector to extract |

## Testing Tools

### test_run

Run project tests.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| framework | string | No | pytest, npm, cargo (auto-detected) |
| path | string | No | Test path |
| args | string | No | Additional arguments |

## Security Tools

### cve_check

Check dependencies for CVE vulnerabilities.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| package | string | No | Specific package |
| ecosystem | string | No | pip, npm, cargo |

Uses the OSV (Open Source Vulnerabilities) API.

## Creating Custom Tools

```python
from kage.tools.base import BaseTool, ToolDefinition, ToolParameter, ToolResult, ToolCategory

class MyTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="my_tool",
            description="Description for LLM",
            category=ToolCategory.FILESYSTEM,
            parameters=[
                ToolParameter(
                    name="param1",
                    type="string",
                    description="Parameter description",
                    required=True,
                ),
            ],
            dangerous=False,
        )

    async def execute(self, param1: str) -> ToolResult:
        # Your implementation
        return ToolResult(
            success=True,
            output="Result",
        )
```

Register in `registry.py`:
```python
def register_builtin(self) -> None:
    self.register(MyTool())
```
