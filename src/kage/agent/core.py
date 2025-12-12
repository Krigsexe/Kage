"""Core agent - ReAct loop implementation with full memory integration."""

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator

from kage.llm.base import LLMClient, Message
from kage.memory.compactor import ContextCompactor
from kage.memory.session import SessionMemory
from kage.memory.persistent import PersistentMemory
from kage.memory.working import WorkingMemory
from kage.knowledge.retriever import KnowledgeRetriever
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


SYSTEM_PROMPT = """You are KAGE, a coding assistant.

## Available Tools
{tools_description}

## CRITICAL RULES
1. TOOL CALL: Reply with ONLY this JSON, nothing else:
   {{"tool": "name", "args": {{...}}}}

2. AFTER "[OK] Tool executed": Give your FINAL ANSWER in plain text.
   DO NOT call another tool. DO NOT output JSON. Just answer the question.

3. Never guess file contents - read first.

## Project Context
{project_path}

{persistent_context}

{knowledge_context}
"""


class Agent:
    """Main agent orchestrator with full YGGDRASIL memory integration.

    Memory layers:
    - PersistentMemory: Cross-session storage (SQLite)
    - SessionMemory: Current session tracking
    - WorkingMemory: Context window management
    - KnowledgeRetriever: RAG for codebase search
    """

    def __init__(
        self,
        llm: LLMClient,
        tool_registry: ToolRegistry,
        session_memory: SessionMemory,
        persistent_memory: PersistentMemory | None = None,
        knowledge_retriever: KnowledgeRetriever | None = None,
    ):
        self.llm = llm
        self.tools = tool_registry
        self.session = session_memory

        # Initialize persistent memory (SQLite cross-session)
        self.persistent = persistent_memory or PersistentMemory(
            session_memory.project_path
        )

        # Initialize knowledge retriever (RAG)
        self.knowledge = knowledge_retriever or KnowledgeRetriever(
            session_memory.project_path
        )

        # Initialize working memory (context window management)
        self.working = WorkingMemory()

        # Initialize compactor for auto-summarization
        self.compactor = ContextCompactor(llm)

        # Build and set system prompt
        self._init_system_prompt()

    def _init_system_prompt(self) -> None:
        """Initialize system prompt with tools and persistent context."""
        tools_desc = self.tools.get_tools_description()

        # Get persistent context (decisions, profile, past sessions)
        persistent_ctx = self.persistent.get_context_for_llm()

        # Knowledge context starts empty, filled on demand
        knowledge_ctx = ""

        system = SYSTEM_PROMPT.format(
            tools_description=tools_desc,
            project_path=self.session.project_path or Path.cwd(),
            persistent_context=persistent_ctx,
            knowledge_context=knowledge_ctx,
        )

        self.working.system_prompt = system

    async def _check_compaction(self) -> None:
        """Check and perform compaction if needed."""
        if self.working.needs_compaction:
            # Get messages for compaction
            messages = self.working.get_messages_for_llm()

            result = await self.compactor.compact(messages)

            # Replace working memory messages
            # Skip system message (index 0) as working memory handles it separately
            new_messages = [m for m in result.messages if m.role != "system"]
            self.working.replace_messages(new_messages)

            # Save session summary to persistent memory
            if result.summary:
                files_modified = list(self.session.get_modified_files())
                self.persistent.save_session_summary(result.summary, files_modified)

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

    async def _retrieve_knowledge(self, query: str) -> str:
        """Retrieve relevant knowledge for the query."""
        try:
            context = self.knowledge.retrieve(query, max_results=3)
            if context.get("code_snippets") or context.get("documentation"):
                return self.knowledge.format_for_llm(context)
        except Exception:
            pass  # Knowledge base may not be indexed
        return ""

    async def run(self, user_input: str) -> AsyncIterator[AgentStep]:
        """Execute agent loop for user input."""

        # Add user message to working memory
        self.working.add_user_message(user_input)

        # Check if compaction needed
        await self._check_compaction()

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            yield AgentStep(state=AgentState.THINKING)

            try:
                # Get messages from working memory
                messages = self.working.get_messages_for_llm()
                response = await self.llm.chat(messages)
            except Exception as e:
                # Record error in persistent memory
                self.persistent.record_error(str(e))
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
                    self.working.add_tool_result(tool_name, error_msg, success=False)
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

                # Track file modifications in session memory
                if "file" in tool_name and result.success:
                    path = tool_args.get("path", "")
                    self.session.record_file_modification(path)

                # Record errors in persistent memory
                if not result.success and result.error:
                    self.persistent.record_error(
                        result.error,
                        file_path=tool_args.get("path"),
                    )

                # Add to working memory
                self.working.add_assistant_message(response)
                self.working.add_tool_result(
                    tool_name,
                    result.to_llm_message(),
                    success=result.success,
                )

            else:
                # Final response - add to working memory
                self.working.add_assistant_message(response)

                yield AgentStep(
                    state=AgentState.DONE,
                    response=response,
                )
                return

        # Max iterations error
        error_msg = f"Max iterations ({max_iterations}) reached"
        self.persistent.record_error(error_msg)
        yield AgentStep(
            state=AgentState.ERROR,
            error=error_msg,
        )

    async def confirm_tool(self, confirmed: bool) -> AsyncIterator[AgentStep]:
        """Continue after dangerous tool confirmation."""
        if not confirmed:
            self.working.add_tool_result(
                "user_action",
                "User declined to execute the tool.",
                success=False,
            )
            yield AgentStep(
                state=AgentState.DONE,
                response="Operation cancelled by user.",
            )
            return

        last_assistant = self.working.get_last_assistant_message()

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

        # Track modifications
        if "file" in tool_name and result.success:
            path = tool_args.get("path", "")
            self.session.record_file_modification(path)

        self.working.add_tool_result(
            tool_name,
            result.to_llm_message(),
            success=result.success,
        )

        async for step in self.run("Continue based on the tool result."):
            yield step

    def get_memory_status(self) -> dict[str, Any]:
        """Get status of all memory layers."""
        return {
            "working": self.working.get_status(),
            "session": {
                "project": str(self.session.project_path),
                "files_modified": len(self.session.get_modified_files()),
            },
            "persistent": {
                "db_path": str(self.persistent.db_path),
                "decisions": len(self.persistent.get_decisions(100)),
            },
        }
