"""Tool registry builder for the Generator ReAct Agent."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from llm_toolbox.llm_client import LLMClient

from llm_toolbox.tool_registry import ToolRegistry

from generator_react_agent.prompt_templates import retrieve_templates, search_examples
from generator_react_agent.tools import make_analyze_task, make_refine_candidate


def build_tool_registry(
    llm_client: LLMClient,
    enabled_tools: frozenset[str],
) -> ToolRegistry:
    """Build a ToolRegistry with only the enabled tools registered."""
    registry = ToolRegistry()

    tool_defs: dict[str, tuple[str, str, dict[str, Any], Callable[..., str]]] = {
        "analyze_task": (
            "analyze_task",
            "Break down a task description into domain, intent, constraints, and output format.",
            {
                "type": "object",
                "properties": {"task_description": {"type": "string"}},
                "required": ["task_description"],
            },
            make_analyze_task(llm_client),
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
            make_refine_candidate(llm_client),
        ),
    }

    for name in enabled_tools:
        if name in tool_defs:
            tool_name, description, parameters, function = tool_defs[name]
            registry.register(
                name=tool_name,
                description=description,
                parameters=parameters,
                function=function,
            )

    return registry
