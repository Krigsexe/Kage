"""Test runner tool."""

import asyncio
import os
from pathlib import Path
from typing import Any

from kage.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from kage.config.settings import settings


class TestRunnerTool(BaseTool):
    """Run tests using pytest or other test frameworks."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="test_run",
            description="Run tests in a project. Automatically detects pytest, unittest, or npm test.",
            category=ToolCategory.TESTING,
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to test file or directory (default: current dir)",
                    required=False,
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Test pattern to match (e.g., 'test_auth', '-k auth')",
                    required=False,
                ),
                ToolParameter(
                    name="verbose",
                    type="boolean",
                    description="Verbose output",
                    required=False,
                    default=False,
                ),
            ],
        )

    async def execute(
        self,
        path: str = ".",
        pattern: str = "",
        verbose: bool = False,
    ) -> ToolResult:
        test_path = Path(path).resolve()

        if not test_path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"Path not found: {path}",
            )

        # Detect test framework
        framework = self._detect_framework(test_path)

        if not framework:
            return ToolResult(
                success=False,
                output="",
                error="No test framework detected (pytest, unittest, npm test)",
            )

        # Build command
        cmd = self._build_command(framework, test_path, pattern, verbose)

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(test_path if test_path.is_dir() else test_path.parent),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=settings.tools.code_exec_timeout,
            )

            output = stdout.decode("utf-8", errors="replace")
            errors = stderr.decode("utf-8", errors="replace")

            success = process.returncode == 0

            return ToolResult(
                success=success,
                output=output + ("\n" + errors if errors else ""),
                error=None if success else f"Tests failed (exit code {process.returncode})",
                metadata={
                    "framework": framework,
                    "path": str(test_path),
                    "exit_code": process.returncode,
                },
            )

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"Test execution timed out after {settings.tools.code_exec_timeout}s",
            )

    def _detect_framework(self, path: Path) -> str | None:
        """Detect test framework from project files."""
        base = path if path.is_dir() else path.parent

        # Python: pytest or unittest
        if (base / "pytest.ini").exists() or (base / "pyproject.toml").exists():
            return "pytest"

        if (base / "setup.py").exists():
            return "pytest"

        # Check for test files
        if list(base.glob("test_*.py")) or list(base.glob("*_test.py")):
            return "pytest"

        if list(base.glob("tests/*.py")):
            return "pytest"

        # Node.js
        package_json = base / "package.json"
        if package_json.exists():
            import json
            try:
                pkg = json.loads(package_json.read_text())
                if "test" in pkg.get("scripts", {}):
                    return "npm"
            except json.JSONDecodeError:
                pass

        return None

    def _build_command(
        self,
        framework: str,
        path: Path,
        pattern: str,
        verbose: bool,
    ) -> str:
        """Build test command."""
        if framework == "pytest":
            cmd = "python -m pytest"
            if verbose:
                cmd += " -v"
            if pattern:
                if pattern.startswith("-"):
                    cmd += f" {pattern}"
                else:
                    cmd += f" -k {pattern}"
            if path.is_file():
                cmd += f" {path}"
            return cmd

        elif framework == "npm":
            cmd = "npm test"
            if pattern:
                cmd += f" -- {pattern}"
            return cmd

        return ""
