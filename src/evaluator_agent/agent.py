"""EvaluatorAgent — implements EvaluatorInterface via llm-toolbox LLMClient."""

from __future__ import annotations

import json
import logging
import math
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from llm_toolbox.llm_client import LLMClient

from evaluator_agent.config import EvaluatorConfig
from shared.async_utils import run_async_in_sync

logger = logging.getLogger(__name__)


class EvaluatorAgent:
    """LLM-as-judge that scores prompt candidates.

    Satisfies the Orchestrator's EvaluatorInterface protocol.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        config: EvaluatorConfig | None = None,
        agent_logger: logging.Logger | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._config = config or EvaluatorConfig()
        self._log = agent_logger or logger

    def evaluate(self, candidate: str, task_description: str) -> float:
        """Evaluate a prompt candidate and return a numeric score."""
        if not candidate or not candidate.strip():
            raise ValueError("candidate must be a non-empty string.")
        if not task_description or not task_description.strip():
            raise ValueError("task_description must be a non-empty string.")

        self._log.info(
            "evaluate() called: candidate_len=%d, task_len=%d",
            len(candidate),
            len(task_description),
        )

        # Format rubric and build messages
        rubric = self._config.rubric_template.format(
            candidate=candidate,
            task_description=task_description,
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": rubric},
            {"role": "user", "content": "Provide your numeric score now."},
        ]

        # Call LLM
        try:
            response = run_async_in_sync(self._llm_client.complete(messages=messages))
        except Exception as exc:
            self._log.error("LLM call failed: %s", exc)
            raise RuntimeError(f"Evaluator LLM call failed: {exc}") from exc

        if not response.content or not response.content.strip():
            raise RuntimeError("Evaluator LLM returned an empty response.")

        # Parse score
        score = self._parse_score(response.content)

        # Validate finiteness
        if math.isnan(score) or math.isinf(score):
            raise ValueError(
                f"Parsed score is not finite: {score}. Raw response: {response.content!r}"
            )

        # Clamp to range
        score = max(self._config.min_score, min(self._config.max_score, score))

        self._log.info("Evaluation score: %.2f", score)
        return score

    @staticmethod
    def _parse_score(text: str) -> float:
        """Extract a numeric score from LLM response text.

        Tries: JSON {"score": N}, number on its own line, first inline number.
        Raises ValueError if no number found.
        """
        stripped = text.strip()

        # 1. Try JSON {"score": N}
        try:
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start != -1 and end > start:
                parsed = json.loads(stripped[start : end + 1])
                if isinstance(parsed, dict) and "score" in parsed:
                    return float(parsed["score"])
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # 2. Try number on its own line
        for line in stripped.splitlines():
            line = line.strip()
            if re.fullmatch(r"-?\d+\.?\d*", line):
                return float(line)

        # 3. First number in text
        match = re.search(r"-?\d+\.?\d*", stripped)
        if match:
            return float(match.group())

        raise ValueError(f"Could not parse a numeric score from response: {text!r}")
