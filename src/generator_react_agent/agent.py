"""GeneratorAgent — implements GeneratorInterface via llm-toolbox."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from llm_toolbox.llm_client import LLMClient

from llm_toolbox.agent import Agent as LLMToolboxAgent

from generator_react_agent.config import AgentConfig
from generator_react_agent.parser import parse_candidates
from generator_react_agent.registry import build_tool_registry
from shared.async_utils import run_async_in_sync

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
        if not task_description or not task_description.strip():
            raise ValueError("task_description must be a non-empty string.")
        if num_candidates < 1:
            raise ValueError(f"num_candidates must be >= 1, got {num_candidates}")

        self._log.info(
            "generate() called: task_len=%d, num_candidates=%d",
            len(task_description),
            num_candidates,
        )

        agent = self._build_agent(num_candidates)
        candidates = self._collect_candidates(agent, task_description, num_candidates)

        self._log.info(
            "Returning %d candidates (requested %d).",
            len(candidates),
            num_candidates,
        )
        return candidates[:num_candidates]

    def _build_agent(self, num_candidates: int) -> LLMToolboxAgent:
        """Configure and return an llm-toolbox Agent."""
        system_prompt = self._config.system_prompt_template.format(
            num_candidates=num_candidates,
        )
        tool_registry = build_tool_registry(
            llm_client=self._llm_client,
            enabled_tools=self._config.enabled_tools,
        )
        return LLMToolboxAgent(
            name="generator-react-agent",
            system_prompt=system_prompt,
            llm_client=self._llm_client,
            tools=tool_registry,
            max_iterations=self._config.max_iterations,
        )

    def _collect_candidates(
        self,
        agent: LLMToolboxAgent,
        task: str,
        num_candidates: int,
    ) -> list[str]:
        """Run the agent and collect unique candidates, retrying if needed."""
        result = self._run_agent(agent, task)
        unique = self._deduplicate(
            parse_candidates(result.answer, num_candidates),
        )

        if len(unique) >= num_candidates:
            return unique[:num_candidates]

        # Not enough — ask for more in a follow-up
        self._log.warning(
            "Parsed %d unique candidates but need %d. Attempting follow-up.",
            len(unique),
            num_candidates,
        )
        remaining = num_candidates - len(unique)
        followup_prompt = (
            f"Generate {remaining} more diverse prompt candidates "
            f"for the same task. Do not repeat these:\n" + "\n".join(f"- {c}" for c in unique)
        )
        try:
            followup_result = self._run_agent(agent, followup_prompt)
            extra = self._deduplicate(
                parse_candidates(followup_result.answer, remaining),
                exclude=set(unique),
            )
            unique.extend(extra)
        except Exception:
            self._log.warning("Follow-up generation failed, returning what we have.")

        return unique

    def _run_agent(self, agent: LLMToolboxAgent, task: str) -> Any:
        """Run the agent and validate the result."""
        try:
            result = run_async_in_sync(agent.run(task))
        except Exception as exc:
            self._log.error("agent.run() failed: %s", exc)
            raise RuntimeError(f"Generator agent failed: {exc}") from exc

        self._log.info(
            "Agent completed: iterations=%d, timed_out=%s",
            result.iterations,
            result.timed_out,
        )

        if result.timed_out and not result.answer:
            raise TimeoutError(
                f"Generator agent timed out after {result.iterations} iterations with no answer."
            )
        if not result.answer or not result.answer.strip():
            raise RuntimeError("Generator agent returned an empty answer.")

        return result

    @staticmethod
    def _deduplicate(
        candidates: list[str],
        exclude: set[str] | None = None,
    ) -> list[str]:
        """Strip whitespace and remove duplicate candidates."""
        seen = set(exclude) if exclude else set()
        unique: list[str] = []
        for c in candidates:
            stripped = c.strip()
            if stripped and stripped not in seen:
                seen.add(stripped)
                unique.append(stripped)
        return unique
