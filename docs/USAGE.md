# Usage Guide

## Getting Started

### Start a Chat Session

```bash
# In current directory
kage chat

# With specific project
kage chat --project /path/to/project

# With different model
kage chat --model qwen2.5-coder:14b
```

### Initialize a Project

```bash
cd your-project
kage init
```

This creates:
- `.kage/config.json` - Project configuration
- `.kage/memory.db` - Persistent memory database

### Index Your Codebase

```bash
kage index
```

This indexes your code for semantic search (RAG).

### Check System Status

```bash
kage doctor
```

## Chat Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/clear` | Clear screen |
| `/status` | Show session status |
| `/exit` | Exit chat |
| `exit` | Exit chat |

## Example Interactions

### Reading and Understanding Code

```
You: Read the main.py file and explain what it does

KAGE: [Uses file_read tool]
      The main.py file contains...
```

### Editing Files

```
You: Add a docstring to the calculate function in utils.py

KAGE: [Uses file_read to see current code]
      [Uses file_edit to add docstring]
      Done! I've added a docstring explaining...
```

### Running Commands

```
You: Run the tests

KAGE: [Uses test_run tool]
      All 15 tests passed!
```

### Git Operations

```
You: Show me the recent changes and commit them

KAGE: [Uses git tool with diff]
      [Uses git tool to commit]
      Committed with message: "Add docstring to calculate function"
```

## Best Practices

### 1. Be Specific
```
# Good
"Read src/utils/helpers.py and add type hints to the parse_date function"

# Less good
"Add type hints"
```

### 2. Work Incrementally
```
# Good workflow
1. "Show me the structure of the project"
2. "Read the authentication module"
3. "Add input validation to the login function"
4. "Run the tests"
```

### 3. Verify Before Committing
```
You: Show me the diff before committing
KAGE: [Shows changes]

You: Looks good, commit it
KAGE: [Commits]
```

### 4. Use Context
KAGE remembers your conversation:
```
You: Read config.py
KAGE: [Shows config.py]

You: Add a new DEBUG setting
KAGE: [Knows you mean config.py]
```

## Memory System

### Session Memory
- Tracks files you've modified
- Remembers errors and solutions
- Cleared when you exit

### Persistent Memory
- Survives across sessions
- Stores project conventions
- Remembers past decisions

### Auto-Compaction
When context gets long, KAGE automatically:
1. Summarizes older messages
2. Keeps recent context
3. Preserves important information

## Safety Features

### Dangerous Operations
Some operations require confirmation:
```
You: Delete the old_tests directory

KAGE: [!] Dangerous operation requested:
      Tool: bash
      Command: rm -rf old_tests/

      Execute this operation? [y/N]
```

### Sandboxed Execution
Code execution is sandboxed when enabled:
- Uses firejail (Linux) or Docker
- Limited file system access
- No network access by default

## Troubleshooting

### KAGE is Slow
- Use a smaller model (1.5B instead of 7B)
- Enable GPU acceleration
- Check available RAM

### Wrong Answers
- Be more specific in your questions
- Ask KAGE to read files first
- Use `kage index` to index your codebase

### Tool Errors
```
You: /status
KAGE: [Shows session status including any errors]
```
