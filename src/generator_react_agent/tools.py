"""Custom tool functions and registry builder for the Generator ReAct Agent."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from llm_toolbox.llm_client import LLMClient

from llm_toolbox.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


def _run_async_in_thread(coro: Any) -> Any:
    """Run an async coroutine from sync code, even inside a running event loop."""
    result: Any = None
    exception: BaseException | None = None

    def _run() -> None:
        nonlocal result, exception
        try:
            result = asyncio.run(coro)
        except Exception as exc:
            exception = exc

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join()

    if exception is not None:
        raise exception
    return result


def _make_analyze_task(llm_client: LLMClient) -> Callable[..., str]:
    """Create an analyze_task tool function with the LLMClient bound via closure."""

    def analyze_task(task_description: str) -> str:
        """Break down a task into domain, intent, constraints, and output format."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a task analysis expert. Analyze the given task description "
                    "and return a structured breakdown with: domain, intent, constraints, "
                    "and expected output format."
                ),
            },
            {"role": "user", "content": task_description},
        ]
        response = _run_async_in_thread(llm_client.complete(messages=messages))
        return response.content or "No analysis produced."

    return analyze_task


def _make_refine_candidate(llm_client: LLMClient) -> Callable[..., str]:
    """Create a refine_candidate tool function with the LLMClient bound via closure."""

    def refine_candidate(draft: str) -> str:
        """Improve a draft prompt candidate while preserving its core intent."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a prompt refinement expert. Improve the given draft prompt "
                    "for clarity, specificity, and effectiveness. Preserve the core intent."
                ),
            },
            {"role": "user", "content": draft},
        ]
        response = _run_async_in_thread(llm_client.complete(messages=messages))
        return response.content or "No refinement produced."

    return refine_candidate


def retrieve_templates(query: str) -> str:
    """Retrieve relevant prompt templates based on task characteristics."""
    # MVP: return a set of common prompt patterns
    return (
        "Common prompt templates for this type of task:\n"
        "- Direct instruction: 'You are a [role]. [Task]. [Format].'\n"
        "- Chain-of-thought: 'Think step by step about [task].'\n"
        "- Few-shot: 'Here are examples: [examples]. Now do [task].'\n"
        "- Role-play: 'Act as an expert [domain] professional. [Task].'"
    )


def search_examples(task_type: str) -> str:
    """Find relevant input-output examples for a given task type."""
    # MVP: return generic guidance
    return (
        "No specific examples found for this task type. "
        "Consider including 2-3 concrete input/output pairs "
        "that demonstrate the expected behavior."
    )


def build_tool_registry(
    llm_client: LLMClient,
    enabled_tools: frozenset[str],
) -> ToolRegistry:
    """Build a ToolRegistry with only the enabled tools registered.

    Tools that need LLM access (analyze_task, refine_candidate) receive
    the llm_client via closure.
    """
    registry = ToolRegistry()

    tool_factories: dict[str, tuple[str, str, dict[str, Any], Callable[..., str]]] = {
        "analyze_task": (
            "analyze_task",
            "Break down a task description into domain, intent, constraints, and output format.",
            {
                "type": "object",
                "properties": {"task_description": {"type": "string"}},
                "required": ["task_description"],
            },
            _make_analyze_task(llm_client),
        ),
        "retrieve_templates": (
            "retrieve_templates",
            "Retrieve relevant prompt templates based on task characteristics.",
            {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            retrieve_templates,
        ),
        "search_examples": (
            "search_examples",
            "Find relevant input-output examples for a given task type.",
            {
                "type": "object",
                "properties": {"task_type": {"type": "string"}},
                "required": ["task_type"],
            },
            search_examples,
        ),
        "refine_candidate": (
            "refine_candidate",
            "Improve a draft prompt candidate while preserving its core intent.",
            {
                "type": "object",
                "properties": {"draft": {"type": "string"}},
                "required": ["draft"],
            },
            _make_refine_candidate(llm_client),
        ),
    }

    for name in enabled_tools:
        if name in tool_factories:
            tool_name, description, parameters, function = tool_factories[name]
            registry.register(
                name=tool_name,
                description=description,
                parameters=parameters,
                function=function,
            )

    return registry
