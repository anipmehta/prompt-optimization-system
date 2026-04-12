"""Tests for selector_adapter.adapter.SelectorAdapter."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from selector_adapter.adapter import SelectorAdapter

# Test constants
SAMPLE_CANDIDATES = ["prompt A", "prompt B", "prompt C"]
DEFAULT_TASK_STATE = "default"
SCORE_MIN = 1.0
SCORE_MAX = 10.0


def _mock_rl_agent(selected: str = "prompt B") -> MagicMock:
    agent = MagicMock()
    agent.select_action = MagicMock(return_value=selected)
    agent.update = MagicMock()
    agent.store_experience = MagicMock()
    agent.prompts = []
    return agent


class TestSelectorAdapterInit:
    def test_accepts_rl_agent(self):
        adapter = SelectorAdapter(rl_agent=_mock_rl_agent())
        assert adapter._task_state == DEFAULT_TASK_STATE

    def test_accepts_custom_task_state(self):
        adapter = SelectorAdapter(rl_agent=_mock_rl_agent(), task_state="summarize")
        assert adapter._task_state == "summarize"

    def test_accepts_custom_logger(self):
        custom = logging.getLogger("test")
        adapter = SelectorAdapter(rl_agent=_mock_rl_agent(), agent_logger=custom)
        assert adapter._log is custom


class TestSelectorAdapterSelect:
    def test_returns_selected_candidate(self):
        agent = _mock_rl_agent("prompt B")
        adapter = SelectorAdapter(rl_agent=agent)
        result = adapter.select(SAMPLE_CANDIDATES)
        assert result == "prompt B"

    def test_updates_agent_prompts(self):
        agent = _mock_rl_agent()
        adapter = SelectorAdapter(rl_agent=agent)
        adapter.select(SAMPLE_CANDIDATES)
        assert agent.prompts == SAMPLE_CANDIDATES

    def test_calls_select_action_with_task_state(self):
        agent = _mock_rl_agent()
        adapter = SelectorAdapter(rl_agent=agent, task_state="my_task")
        adapter.select(SAMPLE_CANDIDATES)
        agent.select_action.assert_called_once_with("my_task")

    def test_empty_candidates_raises(self):
        adapter = SelectorAdapter(rl_agent=_mock_rl_agent())
        with pytest.raises(ValueError, match="must not be empty"):
            adapter.select([])

    def test_tracks_last_action(self):
        agent = _mock_rl_agent("prompt C")
        adapter = SelectorAdapter(rl_agent=agent)
        adapter.select(SAMPLE_CANDIDATES)
        assert adapter._last_action == "prompt C"


class TestSelectorAdapterReward:
    def test_normalizes_and_sends_reward(self):
        agent = _mock_rl_agent("prompt A")
        adapter = SelectorAdapter(
            rl_agent=agent,
            score_min=SCORE_MIN,
            score_max=SCORE_MAX,
        )
        adapter.select(SAMPLE_CANDIDATES)
        adapter.reward(5.5)
        # 5.5 on [1, 10] → normalized to 2*(5.5-1)/9 - 1 = 0.0
        expected = 2.0 * (5.5 - 1.0) / 9.0 - 1.0
        agent.update.assert_called_once_with(DEFAULT_TASK_STATE, "prompt A", expected)
        agent.store_experience.assert_called_once_with(DEFAULT_TASK_STATE, "prompt A", expected)

    def test_max_score_normalizes_to_one(self):
        agent = _mock_rl_agent("prompt A")
        adapter = SelectorAdapter(rl_agent=agent, score_min=1.0, score_max=10.0)
        adapter.select(SAMPLE_CANDIDATES)
        adapter.reward(10.0)
        agent.update.assert_called_once_with(DEFAULT_TASK_STATE, "prompt A", 1.0)

    def test_min_score_normalizes_to_negative_one(self):
        agent = _mock_rl_agent("prompt A")
        adapter = SelectorAdapter(rl_agent=agent, score_min=1.0, score_max=10.0)
        adapter.select(SAMPLE_CANDIDATES)
        adapter.reward(1.0)
        agent.update.assert_called_once_with(DEFAULT_TASK_STATE, "prompt A", -1.0)

    def test_reward_before_select_is_ignored(self):
        agent = _mock_rl_agent()
        adapter = SelectorAdapter(rl_agent=agent)
        adapter.reward(5.0)  # no select() called yet
        agent.update.assert_not_called()
        agent.store_experience.assert_not_called()


class TestNormalizeScore:
    def test_midpoint(self):
        adapter = SelectorAdapter(rl_agent=_mock_rl_agent(), score_min=0.0, score_max=10.0)
        assert adapter._normalize_score(5.0) == 0.0

    def test_min_maps_to_negative_one(self):
        adapter = SelectorAdapter(rl_agent=_mock_rl_agent(), score_min=1.0, score_max=10.0)
        assert adapter._normalize_score(1.0) == -1.0

    def test_max_maps_to_one(self):
        adapter = SelectorAdapter(rl_agent=_mock_rl_agent(), score_min=1.0, score_max=10.0)
        assert adapter._normalize_score(10.0) == 1.0

    def test_zero_range_returns_zero(self):
        adapter = SelectorAdapter(rl_agent=_mock_rl_agent(), score_min=5.0, score_max=5.0)
        assert adapter._normalize_score(5.0) == 0.0
