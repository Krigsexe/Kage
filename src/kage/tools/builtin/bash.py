"""Bash execution tool with sandbox support."""

import asyncio
import os
import shlex
from pathlib import Path

from kage.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from kage.config.settings import settings


FORBIDDEN_COMMANDS = {
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };:",
    "> /dev/sda",
    "chmod -R 777 /",
}

DANGEROUS_PATTERNS = [
    "rm -rf",
    "rm -r",
    "sudo",
    "chmod",
    "chown",
    "systemctl",
    "service",
    "kill",
    "pkill",
    "reboot",
    "shutdown",
    "curl | bash",
    "wget | bash",
]


class BashTool(BaseTool):
    """Execute bash commands with safety checks."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="bash",
            description="Execute a bash command. Use for running scripts, installing packages, etc.",
            category=ToolCategory.CODE_EXECUTION,
            dangerous=True,
            requires_sandbox=True,
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="The bash command to execute",
                ),
                ToolParameter(
                    name="cwd",
                    type="string",
                    description="Working directory (optional)",
                    required=False,
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Timeout in seconds (default: 30)",
                    required=False,
                    default=30,
                ),
            ],
        )
    
    def _is_forbidden(self, command: str) -> bool:
        """Check if command is in forbidden list."""
        cmd_lower = command.lower().strip()
        return any(forbidden in cmd_lower for forbidden in FORBIDDEN_COMMANDS)
    
    def _is_dangerous(self, command: str) -> list[str]:
        """Return list of dangerous patterns found."""
        cmd_lower = command.lower()
        return [p for p in DANGEROUS_PATTERNS if p in cmd_lower]
    
    async def execute(
        self,
        command: str,
        cwd: str | None = None,
        timeout: int | None = None,
    ) -> ToolResult:
        if self._is_forbidden(command):
            return ToolResult(
                success=False,
                output="",
                error="[BLOCKED] Command is forbidden for safety reasons.",
            )
        
        dangerous = self._is_dangerous(command)
        
        work_dir = Path(cwd).resolve() if cwd else Path.cwd()
        if not work_dir.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"Working directory not found: {cwd}",
            )
        
        exec_timeout = timeout or settings.tools.bash_timeout
        
        try:
            if settings.tools.sandbox_enabled and settings.tools.sandbox_type == "firejail":
                full_command = f"firejail --quiet --private-tmp --net=none -- bash -c {shlex.quote(command)}"
            else:
                full_command = command
            
            process = await asyncio.create_subprocess_shell(
                full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env={**os.environ, "TERM": "dumb"},
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=exec_timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {exec_timeout}s",
                )
            
            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()
            
            output_parts = []
            if stdout_str:
                output_parts.append(stdout_str)
            if stderr_str:
                output_parts.append(f"[stderr]\n{stderr_str}")
            
            output = "\n".join(output_parts) or "(no output)"
            
            return ToolResult(
                success=process.returncode == 0,
                output=output,
                error=f"Exit code: {process.returncode}" if process.returncode != 0 else None,
                metadata={
                    "exit_code": process.returncode,
                    "cwd": str(work_dir),
                    "dangerous_patterns": dangerous,
                },
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution error: {type(e).__name__}: {str(e)}",
            )
