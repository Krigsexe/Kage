"""Sandboxed code execution tool."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Literal

from kage.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from kage.config.settings import settings


class CodeExecTool(BaseTool):
    """Execute code in a sandboxed environment."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="code_exec",
            description="Execute Python or Node.js code in a sandboxed environment. Use for testing code snippets safely.",
            category=ToolCategory.CODE_EXECUTION,
            dangerous=True,
            requires_sandbox=True,
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="Code to execute",
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="Programming language",
                    enum=["python", "javascript"],
                    default="python",
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Execution timeout in seconds (default: 30)",
                    required=False,
                    default=30,
                ),
            ],
        )

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
    ) -> ToolResult:
        if not code.strip():
            return ToolResult(
                success=False,
                output="",
                error="Empty code provided",
            )

        # Limit timeout
        timeout = min(timeout, settings.tools.code_exec_timeout)

        # Create temporary file
        suffix = ".py" if language == "python" else ".js"
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Build command based on sandbox settings
            cmd = self._build_command(temp_path, language)

            # Execute
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_safe_env(),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Execution timed out after {timeout}s",
                )

            output = stdout.decode("utf-8", errors="replace")
            errors = stderr.decode("utf-8", errors="replace")

            success = process.returncode == 0

            return ToolResult(
                success=success,
                output=output + ("\n[stderr]\n" + errors if errors else ""),
                error=None if success else f"Exit code: {process.returncode}",
                metadata={
                    "language": language,
                    "exit_code": process.returncode,
                    "sandboxed": settings.tools.sandbox_enabled,
                },
            )

        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def _build_command(self, script_path: str, language: str) -> str:
        """Build execution command with optional sandboxing."""
        if language == "python":
            interpreter = sys.executable
            base_cmd = f'"{interpreter}" "{script_path}"'
        else:  # javascript
            base_cmd = f'node "{script_path}"'

        if not settings.tools.sandbox_enabled:
            return base_cmd

        if settings.tools.sandbox_type == "firejail":
            # Firejail sandbox (Linux only)
            return f"firejail --quiet --private --net=none {base_cmd}"

        elif settings.tools.sandbox_type == "docker":
            # Docker sandbox
            image = "python:3.11-slim" if language == "python" else "node:20-slim"
            return (
                f"docker run --rm --network=none "
                f"-v {script_path}:/app/script{'.py' if language == 'python' else '.js'}:ro "
                f"{image} "
                f"{'python' if language == 'python' else 'node'} /app/script{'.py' if language == 'python' else '.js'}"
            )

        return base_cmd

    def _get_safe_env(self) -> dict[str, str]:
        """Get a minimal safe environment."""
        safe_vars = ["PATH", "PYTHONPATH", "HOME", "USER", "LANG", "LC_ALL"]
        env = {k: v for k, v in os.environ.items() if k in safe_vars}

        # Add some safety flags
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONUNBUFFERED"] = "1"

        return env
