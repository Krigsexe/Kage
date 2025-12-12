"""Main CLI application."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.table import Table

from kage.agent.core import Agent, AgentState, AgentStep
from kage.llm.ollama import OllamaClient
from kage.memory.session import SessionMemory
from kage.tools.registry import ToolRegistry
from kage.config.settings import settings

app = typer.Typer(
    name="kage",
    help="KAGE - Krigsexe Agentic Generative Engine",
    no_args_is_help=True,
)
console = Console()


BANNER = """
[bold cyan]+===========================================================+
|   _  __    _    ____ _____                                |
|  | |/ /   / \\  / ___| ____|                               |
|  | ' /   / _ \\| |  _|  _|                                 |
|  | . \\  / ___ \\ |_| | |___                                |
|  |_|\\_\\/_/   \\_\\____|_____|                               |
|                                                           |
|  Krigsexe Agentic Generative Engine v0.1.0                |
|  Local AI Coding Assistant                                |
+===========================================================+[/bold cyan]
"""


def print_banner() -> None:
    """Print welcome banner."""
    console.print(BANNER)


def format_step(step: AgentStep) -> Panel | None:
    """Format an agent step for display."""
    
    if step.state == AgentState.THINKING:
        return Panel(
            "[yellow]Thinking...[/yellow]",
            title="[yellow]Processing[/yellow]",
            border_style="yellow",
        )
    
    elif step.state == AgentState.TOOL_CALL:
        if step.tool_result:
            status = "[OK]" if step.tool_result.success else "[X]"
            style = "green" if step.tool_result.success else "red"
            
            content = f"[bold]{status} {step.tool_name}[/bold]\n\n"
            if step.tool_args:
                args_str = "\n".join(f"  {k}: {v}" for k, v in step.tool_args.items())
                content += f"Args:\n{args_str}\n\n"
            
            output = step.tool_result.output
            if len(output) > 1000:
                output = output[:1000] + "\n... (truncated)"
            content += output
            
            return Panel(
                content,
                title=f"[{style}]Tool Result[/{style}]",
                border_style=style,
            )
        else:
            return Panel(
                f"Calling: [bold]{step.tool_name}[/bold]\nArgs: {step.tool_args}",
                title="[blue]Tool Call[/blue]",
                border_style="blue",
            )
    
    elif step.state == AgentState.WAITING_CONFIRMATION:
        return Panel(
            f"[!] Dangerous operation requested:\n\n"
            f"Tool: [bold]{step.tool_name}[/bold]\n"
            f"Args: {step.tool_args}",
            title="[yellow]Confirmation Required[/yellow]",
            border_style="yellow",
        )
    
    elif step.state == AgentState.DONE:
        return Panel(
            Markdown(step.response or ""),
            title="[green]Response[/green]",
            border_style="green",
        )
    
    elif step.state == AgentState.ERROR:
        return Panel(
            f"[red]{step.error}[/red]",
            title="[red]Error[/red]",
            border_style="red",
        )
    
    return None


@app.command()
def chat(
    project_path: Optional[Path] = typer.Option(
        None, "--project", "-p",
        help="Path to project directory",
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m",
        help="Override default model",
    ),
) -> None:
    """Start interactive chat session."""
    
    print_banner()
    
    project = project_path or Path.cwd()
    console.print(f"Project: [cyan]{project}[/cyan]")

    settings.ensure_directories()

    if model:
        settings.llm.model = model

    console.print(f"Model: [cyan]{settings.llm.model}[/cyan]")
    console.print()
    
    llm = OllamaClient()
    tools = ToolRegistry()
    tools.register_builtin()
    memory = SessionMemory(project_path=project)
    
    agent = Agent(llm, tools, memory)
    
    console.print("[dim]Type 'exit' or 'quit' to end session[/dim]")
    console.print("[dim]Type '/help' for commands[/dim]")
    console.print()
    
    async def run_chat() -> None:
        while True:
            try:
                user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Goodbye![/yellow]")
                break
            
            if user_input.lower() in ("exit", "quit", "/exit", "/quit"):
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if user_input.lower() == "/help":
                show_help()
                continue
            
            if user_input.lower() == "/clear":
                console.clear()
                print_banner()
                continue
            
            if user_input.lower() == "/status":
                console.print(memory.get_summary())
                continue
            
            if not user_input.strip():
                continue
            
            async for step in agent.run(user_input):
                panel = format_step(step)
                if panel:
                    console.print(panel)
                
                if step.state == AgentState.WAITING_CONFIRMATION:
                    confirmed = Confirm.ask("Execute this operation?")
                    async for confirm_step in agent.confirm_tool(confirmed):
                        confirm_panel = format_step(confirm_step)
                        if confirm_panel:
                            console.print(confirm_panel)
            
            console.print()
    
    asyncio.run(run_chat())


@app.command()
def init(
    path: Optional[Path] = typer.Argument(
        None,
        help="Project path (default: current directory)",
    ),
) -> None:
    """Initialize KAGE in a project directory."""
    
    import json
    from datetime import datetime
    
    project_path = path or Path.cwd()
    kage_dir = project_path / ".kage"
    
    if kage_dir.exists():
        console.print(f"[yellow]KAGE already initialized in {project_path}[/yellow]")
        return
    
    kage_dir.mkdir(parents=True)
    
    config = {
        "project_name": project_path.name,
        "created_at": datetime.now().isoformat(),
        "conventions": [],
        "ignore_patterns": list(settings.knowledge.ignore_patterns),
    }
    
    (kage_dir / "config.json").write_text(json.dumps(config, indent=2))
    (kage_dir / "memory").mkdir()
    
    console.print(f"[green][OK] Initialized KAGE in {project_path}[/green]")
    console.print(f"  Created: {kage_dir}")


@app.command()
def doctor() -> None:
    """Check system configuration and dependencies."""
    
    console.print("[bold]KAGE System Check[/bold]\n")
    
    checks: list[tuple[str, str, str, str]] = []
    
    import httpx
    try:
        response = httpx.get(f"{settings.llm.ollama_host}/api/tags", timeout=5)
        models = response.json().get("models", [])
        model_names = [m["name"] for m in models]
        
        if settings.llm.model in model_names or any(settings.llm.model.split(":")[0] in m for m in model_names):
            checks.append(("Ollama", "[OK] Running", "green", f"Model available"))
        else:
            checks.append(("Ollama", "[!] Running", "yellow", f"Model '{settings.llm.model}' not found"))
    except Exception as e:
        checks.append(("Ollama", "[X] Not running", "red", str(e)[:50]))

    for name, path in [
        ("Memory storage", settings.memory.persistent_path),
        ("ChromaDB", settings.knowledge.chroma_path),
        ("Docs cache", settings.knowledge.docs_cache_path),
    ]:
        if path.exists():
            checks.append((name, "[OK] Exists", "green", str(path)))
        else:
            checks.append((name, "[-] Missing", "yellow", f"Will be created"))

    import shutil
    if settings.tools.sandbox_enabled:
        if settings.tools.sandbox_type == "firejail":
            if shutil.which("firejail"):
                checks.append(("Sandbox (firejail)", "[OK] Available", "green", ""))
            else:
                checks.append(("Sandbox (firejail)", "[X] Not installed", "red", "apt install firejail"))
        elif settings.tools.sandbox_type == "docker":
            if shutil.which("docker"):
                checks.append(("Sandbox (docker)", "[OK] Available", "green", ""))
            else:
                checks.append(("Sandbox (docker)", "[X] Not installed", "red", "Install Docker"))
    else:
        checks.append(("Sandbox", "[-] Disabled", "yellow", ""))
    
    table = Table()
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Details", style="dim")
    
    for name, status, color, details in checks:
        table.add_row(name, f"[{color}]{status}[/{color}]", details)
    
    console.print(table)


@app.command()
def version() -> None:
    """Show version information."""
    console.print("KAGE v0.1.0")
    console.print("Krigsexe Agentic Generative Engine")
    console.print("https://github.com/Krigsexe/Kage")


def show_help() -> None:
    """Show help for chat commands."""
    help_text = """
## Chat Commands

| Command | Description |
|---------|-------------|
| `/help` | Show this help |
| `/clear` | Clear screen |
| `/status` | Show session status |
| `/exit` | Exit chat |
| `exit` | Exit chat |

## Tips

- Be specific about what you want
- Reference files by their full path
- Ask KAGE to verify before making changes
"""
    console.print(Markdown(help_text))


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
