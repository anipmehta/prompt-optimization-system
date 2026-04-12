"""SelectorAdapter — wraps RLAgent to satisfy SelectorInterface."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agent import RLAgent

logger = logging.getLogger(__name__)


class SelectorAdapter:
    """Adapts prompt-selection-rl-agent's RLAgent to SelectorInterface.

    Handles:
    - Dynamic candidate lists (RLAgent expects fixed prompts at init)
    - Score normalization (evaluator returns 1-10, RLAgent expects -1 to 1)
    - Tracking the last selection for reward routing
    """

    def __init__(
        self,
        rl_agent: RLAgent,
        task_state: str = "default",
        score_min: float = 1.0,
        score_max: float = 10.0,
        agent_logger: logging.Logger | None = None,
    ) -> None:
        self._rl_agent = rl_agent
        self._task_state = task_state
        self._score_min = score_min
        self._score_max = score_max
        self._log = agent_logger or logger
        self._last_action: str | None = None

    def select(self, candidates: list[str]) -> str:
        """Select the best candidate from a list.

        Updates the RLAgent's prompt list to match the current candidates,
        then delegates selection to the RL policy.
        """
        if not candidates:
            raise ValueError("candidates list must not be empty.")

        # Update the agent's prompt list to match current candidates
        self._rl_agent.prompts = list(candidates)

        selected: str = self._rl_agent.select_action(self._task_state)
        self._last_action = selected

        self._log.info(
            "Selected candidate: %s (from %d candidates)",
            selected[:80],
            len(candidates),
        )
        return selected

    def reward(self, score: float) -> None:
        """Send evaluation score as reward signal.

        Normalizes the score from [score_min, score_max] to [-1.0, 1.0]
        before passing to the RLAgent.
        """
        if self._last_action is None:
            self._log.warning("reward() called before select(). Ignoring.")
            return

        normalized = self._normalize_score(score)

        self._log.info(
            "Reward: raw=%.2f, normalized=%.2f",
            score,
            normalized,
        )

        self._rl_agent.update(
            self._task_state,
            self._last_action,
            normalized,
        )
        self._rl_agent.store_experience(
            self._task_state,
            self._last_action,
            normalized,
        )

    def _normalize_score(self, score: float) -> float:
        """Normalize score from [score_min, score_max] to [-1.0, 1.0]."""
        score_range = self._score_max - self._score_min
        if score_range == 0:
            return 0.0
        return 2.0 * (score - self._score_min) / score_range - 1.0
