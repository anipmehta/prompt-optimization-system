"""LLM-backed tool functions for the Generator ReAct Agent."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from llm_toolbox.llm_client import LLMClient


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
        response = _run_async_in_thread(llm_client.complete(messages=messages))
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
        response = _run_async_in_thread(llm_client.complete(messages=messages))
        return response.content or "No refinement produced."

    return refine_candidate
