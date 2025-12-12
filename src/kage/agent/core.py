"""Core agent - ReAct loop implementation."""

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator

from kage.llm.base import LLMClient, Message
from kage.memory.compactor import ContextCompactor
from kage.memory.session import SessionMemory
from kage.tools.registry import ToolRegistry
from kage.tools.base import ToolResult
from kage.config.settings import settings


class AgentState(str, Enum):
    """Agent execution state."""
    
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    WAITING_CONFIRMATION = "waiting_confirmation"
    RESPONDING = "responding"
    ERROR = "error"
    DONE = "done"


@dataclass
class AgentStep:
    """A single step in agent execution."""
    
    state: AgentState
    thought: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: ToolResult | None = None
    response: str | None = None
    error: str | None = None


SYSTEM_PROMPT = """You are KAGE, a local AI coding assistant. You help developers write, debug, and understand code.

## Core Principles

1. **NEVER ASSUME** - Always verify before acting:
   - Use `file_read` before assuming file contents
   - Use `dir_list` before assuming project structure

2. **VERIFY THEN ACT** - Follow this pattern:
   - Read relevant files first
   - Understand the context
   - Plan your changes
   - Execute one change at a time
   - Verify the result

3. **NO HALLUCINATION** - If you don't know:
   - Ask the user
   - Say "I don't know" rather than guess

4. **INCREMENTAL CHANGES** - Make small, testable changes

## Available Tools

{tools_description}

## Response Format

When you need to use a tool, respond with ONLY a JSON block:
```json
{{"tool": "tool_name", "args": {{"param": "value"}}}}
```

When you have the final answer, respond naturally without JSON.

## Current Context

Project: {project_path}
Working Directory: {cwd}
"""


class Agent:
    """Main agent orchestrator."""
    
    def __init__(
        self,
        llm: LLMClient,
        tool_registry: ToolRegistry,
        session_memory: SessionMemory,
    ):
        self.llm = llm
        self.tools = tool_registry
        self.memory = session_memory
        self.compactor = ContextCompactor(llm)
        self.messages: list[Message] = []
        self._init_system_prompt()
    
    def _init_system_prompt(self) -> None:
        """Initialize system prompt with tools."""
        tools_desc = self.tools.get_tools_description()
        
        system = SYSTEM_PROMPT.format(
            tools_description=tools_desc,
            project_path=self.memory.project_path or "Not initialized",
            cwd=self.memory.cwd,
        )
        
        self.messages.append(Message(role="system", content=system))
    
    async def _check_compaction(self) -> None:
        """Check and perform compaction if needed."""
        if self.compactor.needs_compaction(self.messages):
            result = await self.compactor.compact(self.messages)
            self.messages = result.messages
    
    def _parse_tool_call(self, content: str) -> tuple[str, dict[str, Any]] | None:
        """Extract tool call from LLM response."""
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if "tool" in data:
                    return data["tool"], data.get("args", {})
            except json.JSONDecodeError:
                pass
        
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(content[start:end])
                if "tool" in data:
                    return data["tool"], data.get("args", {})
        except json.JSONDecodeError:
            pass
        
        return None
    
    async def run(self, user_input: str) -> AsyncIterator[AgentStep]:
        """Execute agent loop for user input."""
        
        self.messages.append(Message(role="user", content=user_input))
        
        await self._check_compaction()
        
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            yield AgentStep(state=AgentState.THINKING)
            
            try:
                response = await self.llm.chat(self.messages)
            except Exception as e:
                yield AgentStep(
                    state=AgentState.ERROR,
                    error=f"LLM error: {str(e)}",
                )
                return
            
            tool_call = self._parse_tool_call(response)
            
            if tool_call:
                tool_name, tool_args = tool_call
                
                yield AgentStep(
                    state=AgentState.TOOL_CALL,
                    thought=response,
                    tool_name=tool_name,
                    tool_args=tool_args,
                )
                
                tool = self.tools.get(tool_name)
                if not tool:
                    error_msg = f"Unknown tool: {tool_name}"
                    self.messages.append(Message(
                        role="tool",
                        content=error_msg,
                        metadata={"tool": tool_name, "error": True},
                    ))
                    continue
                
                if tool.definition.dangerous:
                    yield AgentStep(
                        state=AgentState.WAITING_CONFIRMATION,
                        tool_name=tool_name,
                        tool_args=tool_args,
                    )
                    return
                
                result = await tool.safe_execute(**tool_args)
                
                yield AgentStep(
                    state=AgentState.TOOL_CALL,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    tool_result=result,
                )
                
                if "file" in tool_name and result.success:
                    path = tool_args.get("path", "")
                    self.memory.record_file_modification(path)
                
                self.messages.append(Message(
                    role="assistant",
                    content=response,
                ))
                self.messages.append(Message(
                    role="tool",
                    content=result.to_llm_message(),
                    metadata={
                        "tool": tool_name,
                        "success": result.success,
                    },
                ))
            
            else:
                self.messages.append(Message(
                    role="assistant",
                    content=response,
                ))
                
                yield AgentStep(
                    state=AgentState.DONE,
                    response=response,
                )
                return
        
        yield AgentStep(
            state=AgentState.ERROR,
            error=f"Max iterations ({max_iterations}) reached",
        )
    
    async def confirm_tool(self, confirmed: bool) -> AsyncIterator[AgentStep]:
        """Continue after dangerous tool confirmation."""
        if not confirmed:
            self.messages.append(Message(
                role="tool",
                content="User declined to execute the tool.",
            ))
            yield AgentStep(
                state=AgentState.DONE,
                response="Operation cancelled by user.",
            )
            return
        
        last_assistant = next(
            (m for m in reversed(self.messages) if m.role == "assistant"),
            None,
        )
        
        if not last_assistant:
            yield AgentStep(
                state=AgentState.ERROR,
                error="No pending tool call found",
            )
            return
        
        tool_call = self._parse_tool_call(last_assistant.content)
        if not tool_call:
            yield AgentStep(
                state=AgentState.ERROR,
                error="Could not parse tool call",
            )
            return
        
        tool_name, tool_args = tool_call
        tool = self.tools.get(tool_name)
        
        if not tool:
            yield AgentStep(
                state=AgentState.ERROR,
                error=f"Tool not found: {tool_name}",
            )
            return
        
        result = await tool.safe_execute(**tool_args)
        
        yield AgentStep(
            state=AgentState.TOOL_CALL,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=result,
        )
        
        self.messages.append(Message(
            role="tool",
            content=result.to_llm_message(),
            metadata={"tool": tool_name, "success": result.success},
        ))
        
        async for step in self.run("Continue based on the tool result."):
            yield step
