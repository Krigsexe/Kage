# Contributing to KAGE

Thank you for your interest in contributing to KAGE!

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/Kage.git
cd Kage
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or .venv\Scripts\activate on Windows

# Install dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### 3. Run Tests

```bash
pytest
```

## Development Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Code refactoring

### Commit Messages

Follow conventional commits:
```
type(scope): description

feat(tools): add new web_search tool
fix(agent): prevent infinite loop in ReAct
docs(readme): update installation instructions
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Pull Request Process

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit PR with clear description
5. Address review comments

## Code Standards

### Python Style

- Follow PEP 8
- Use type hints
- Max line length: 100 characters

```python
# Good
async def process_file(path: str, encoding: str = "utf-8") -> str:
    """Process a file and return its contents.

    Args:
        path: File path to process
        encoding: File encoding

    Returns:
        File contents as string
    """
    ...
```

### Linting

```bash
# Run linter
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Type checking
mypy src/
```

## Adding New Tools

1. Create tool file in `src/kage/tools/builtin/`
2. Implement `BaseTool` interface
3. Register in `registry.py`
4. Add tests
5. Update `docs/TOOLS.md`

Example:
```python
# src/kage/tools/builtin/my_tool.py
from kage.tools.base import BaseTool, ToolDefinition, ToolResult

class MyTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="my_tool",
            description="Does something useful",
            ...
        )

    async def execute(self, **kwargs) -> ToolResult:
        ...
```

## Testing

### Unit Tests

```python
# tests/unit/test_my_tool.py
import pytest
from kage.tools.builtin.my_tool import MyTool

@pytest.mark.asyncio
async def test_my_tool_success():
    tool = MyTool()
    result = await tool.execute(param="value")
    assert result.success
    assert "expected" in result.output
```

### Integration Tests

```python
# tests/integration/test_agent_with_tool.py
@pytest.mark.asyncio
async def test_agent_uses_tool():
    agent = create_test_agent()
    async for step in agent.run("Use my_tool"):
        if step.tool_name == "my_tool":
            assert step.tool_result.success
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src/kage

# Specific test file
pytest tests/unit/test_tools.py

# Specific test
pytest tests/unit/test_tools.py::test_file_read
```

## Documentation

- Update relevant `.md` files in `docs/`
- Add docstrings to new functions/classes
- Include examples in docstrings

## Reporting Issues

### Bug Reports

Include:
- KAGE version (`kage --version`)
- Python version
- OS
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

### Feature Requests

Include:
- Clear description of the feature
- Use case / motivation
- Proposed implementation (optional)

## Code of Conduct

- Be respectful
- Be constructive
- Help others learn
- Focus on the code, not the person

## Questions?

- Open an issue with the `question` label
- Check existing issues/discussions first

Thank you for contributing!
