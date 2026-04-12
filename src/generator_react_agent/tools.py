"""LLM-backed tool functions for the Generator ReAct Agent."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_toolbox.llm_client import LLMClient

from shared.async_utils import run_async_in_sync


def make_analyze_task(llm_client: LLMClient) -> Callable[..., str]:
    """Create an analyze_task tool with the LLMClient bound via closure."""

    def analyze_task(task_description: str) -> str:
        """Break down a task into domain, intent, constraints, and output format."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a task analysis expert. Analyze the given task "
                    "description and return a structured breakdown with: "
                    "domain, intent, constraints, and expected output format."
                ),
            },
            {"role": "user", "content": task_description},
        ]
        response = run_async_in_sync(llm_client.complete(messages=messages))
        return response.content or "No analysis produced."

    return analyze_task


def make_refine_candidate(llm_client: LLMClient) -> Callable[..., str]:
    """Create a refine_candidate tool with the LLMClient bound via closure."""

    def refine_candidate(draft: str) -> str:
        """Improve a draft prompt candidate while preserving its core intent."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a prompt refinement expert. Improve the given "
                    "draft prompt for clarity, specificity, and effectiveness. "
                    "Preserve the core intent."
                ),
            },
            {"role": "user", "content": draft},
        ]
        response = run_async_in_sync(llm_client.complete(messages=messages))
        return response.content or "No refinement produced."

    return refine_candidate
