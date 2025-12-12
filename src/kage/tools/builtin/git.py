"""Git operations tool."""

from pathlib import Path

from git import Repo, InvalidGitRepositoryError
from git.exc import GitCommandError

from kage.tools.base import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)


class GitTool(BaseTool):
    """Git operations - status, diff, commit, etc."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="git",
            description="Execute git operations: status, diff, add, commit, log, branch.",
            category=ToolCategory.GIT,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Git operation to perform",
                    enum=["status", "diff", "add", "commit", "log", "branch", "show"],
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Repository path (default: current directory)",
                    required=False,
                ),
                ToolParameter(
                    name="args",
                    type="string",
                    description="Additional arguments (e.g., file paths, commit message)",
                    required=False,
                ),
            ],
        )
    
    async def execute(
        self,
        operation: str,
        path: str | None = None,
        args: str | None = None,
    ) -> ToolResult:
        repo_path = Path(path).resolve() if path else Path.cwd()
        
        try:
            repo = Repo(repo_path, search_parent_directories=True)
        except InvalidGitRepositoryError:
            return ToolResult(
                success=False,
                output="",
                error=f"Not a git repository: {repo_path}",
            )
        
        try:
            if operation == "status":
                output = repo.git.status()
            
            elif operation == "diff":
                if args:
                    output = repo.git.diff(args)
                else:
                    output = repo.git.diff()
                if not output:
                    output = "(no changes)"
            
            elif operation == "add":
                if not args:
                    return ToolResult(
                        success=False,
                        output="",
                        error="'add' requires file paths in args",
                    )
                repo.git.add(args.split())
                output = f"Added: {args}"
            
            elif operation == "commit":
                if not args:
                    return ToolResult(
                        success=False,
                        output="",
                        error="'commit' requires a message in args",
                    )
                repo.git.commit("-m", args)
                output = f"Committed with message: {args}"
            
            elif operation == "log":
                count = args if args else "10"
                output = repo.git.log(f"--oneline", f"-n{count}")
            
            elif operation == "branch":
                output = repo.git.branch("-a")
            
            elif operation == "show":
                ref = args if args else "HEAD"
                output = repo.git.show(ref, "--stat")
            
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown operation: {operation}",
                )
            
            return ToolResult(
                success=True,
                output=output,
                metadata={"operation": operation, "repo": str(repo.working_dir)},
            )
        
        except GitCommandError as e:
            return ToolResult(
                success=False,
                output=e.stdout or "",
                error=str(e.stderr) if e.stderr else str(e),
            )
