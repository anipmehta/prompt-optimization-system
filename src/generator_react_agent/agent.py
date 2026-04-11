"""GeneratorAgent — implements GeneratorInterface via llm-toolbox."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from llm_toolbox.llm_client import LLMClient

from llm_toolbox.agent import Agent as LLMToolboxAgent

from generator_react_agent.config import AgentConfig
from generator_react_agent.parser import parse_candidates
from generator_react_agent.tools import build_tool_registry

logger = logging.getLogger(__name__)


class GeneratorAgent:
    """Thin adapter over llm-toolbox's Agent that satisfies GeneratorInterface.

    Delegates ReAct loop execution to llm-toolbox and parses the result
    into a list of prompt candidates.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        config: AgentConfig | None = None,
        agent_logger: logging.Logger | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._config = config or AgentConfig()
        self._log = agent_logger or logger

    def generate(self, task_description: str, num_candidates: int) -> list[str]:
        """Generate prompt candidates for a task description.

        Satisfies the Orchestrator's GeneratorInterface protocol.
        """
        # --- Input validation ---
        if not task_description or not task_description.strip():
            raise ValueError("task_description must be a non-empty string.")
        if num_candidates < 1:
            raise ValueError(
                f"num_candidates must be >= 1, got {num_candidates}"
            )

        self._log.info(
            "generate() called: task_len=%d, num_candidates=%d",
            len(task_description),
            num_candidates,
        )

        # --- Build system prompt ---
        system_prompt = self._config.system_prompt_template.format(
            num_candidates=num_candidates
        )

        # --- Build tool registry ---
        tool_registry = build_tool_registry(
            llm_client=self._llm_client,
            enabled_tools=self._config.enabled_tools,
        )

        # --- Create llm-toolbox Agent ---
        agent = LLMToolboxAgent(
            name="generator-react-agent",
            system_prompt=system_prompt,
            llm_client=self._llm_client,
            tools=tool_registry,
            max_iterations=self._config.max_iterations,
        )

        # --- Run agent (async-to-sync bridge) ---
        try:
            result = self._run_async(agent.run(task_description))
        except Exception as exc:
            self._log.error("agent.run() failed: %s", exc)
            raise RuntimeError(
                f"Generator agent failed: {exc}"
            ) from exc

        self._log.info(
            "Agent completed: iterations=%d, timed_out=%s",
            result.iterations,
            result.timed_out,
        )

        # --- Handle timeout ---
        if result.timed_out and not result.answer:
            raise TimeoutError(
                f"Generator agent timed out after {result.iterations} iterations "
                "with no answer."
            )

        if not result.answer or not result.answer.strip():
            raise RuntimeError("Generator agent returned an empty answer.")

        # --- Parse candidates ---
        candidates = parse_candidates(result.answer, num_candidates)

        # --- Deduplicate ---
        seen: set[str] = set()
        unique: list[str] = []
        for c in candidates:
            stripped = c.strip()
            if stripped and stripped not in seen:
                seen.add(stripped)
                unique.append(stripped)

        # --- Adjust count ---
        if len(unique) > num_candidates:
            unique = unique[:num_candidates]

        if len(unique) < num_candidates:
            self._log.warning(
                "Parsed %d unique candidates but need %d. "
                "Attempting follow-up generation.",
                len(unique),
                num_candidates,
            )
            try:
                followup_prompt = (
                    f"Generate {num_candidates - len(unique)} more diverse prompt "
                    f"candidates for the same task. Do not repeat these:\n"
                    + "\n".join(f"- {c}" for c in unique)
                )
                followup_result = self._run_async(agent.run(followup_prompt))
                if followup_result.answer:
                    extra = parse_candidates(
                        followup_result.answer,
                        num_candidates - len(unique),
                    )
                    for c in extra:
                        stripped = c.strip()
                        if stripped and stripped not in seen:
                            seen.add(stripped)
                            unique.append(stripped)
                        if len(unique) >= num_candidates:
                            break
            except Exception:
                self._log.warning("Follow-up generation failed, returning what we have.")

        self._log.info(
            "Returning %d candidates (requested %d).",
            len(unique),
            num_candidates,
        )
        return unique[:num_candidates]

    @staticmethod
    def _run_async(coro):
        """Bridge async coroutine to sync, handling already-running event loops."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — safe to use asyncio.run()
            return asyncio.run(coro)

        # Running loop detected — execute in a new thread
        result = None
        exception = None

        def _run():
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
