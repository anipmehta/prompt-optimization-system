"""Tests for generator_react_agent.agent.GeneratorAgent."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from generator_react_agent.agent import GeneratorAgent
from generator_react_agent.config import AgentConfig


@dataclass
class FakeAgentResult:
    answer: str | None
    reasoning_trace: list = None  # type: ignore[assignment]
    iterations: int = 1
    timed_out: bool = False

    def __post_init__(self) -> None:
        if self.reasoning_trace is None:
            self.reasoning_trace = []


class TestGeneratorAgentInit:
    def test_accepts_llm_client(self):
        client = MagicMock()
        agent = GeneratorAgent(llm_client=client)
        assert agent._llm_client is client
        assert agent._config.max_iterations == 5

    def test_accepts_custom_config(self):
        client = MagicMock()
        cfg = AgentConfig(max_iterations=10, enabled_tools=frozenset())
        agent = GeneratorAgent(llm_client=client, config=cfg)
        assert agent._config.max_iterations == 10

    def test_accepts_custom_logger(self):
        client = MagicMock()
        custom_logger = logging.getLogger("test")
        agent = GeneratorAgent(llm_client=client, agent_logger=custom_logger)
        assert agent._log is custom_logger


class TestGeneratorAgentValidation:
    def _make_agent(self) -> GeneratorAgent:
        client = MagicMock()
        return GeneratorAgent(
            llm_client=client,
            config=AgentConfig(enabled_tools=frozenset()),
        )

    def test_empty_task_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            self._make_agent().generate("", 3)

    def test_whitespace_task_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            self._make_agent().generate("   ", 3)

    def test_zero_candidates_raises(self):
        with pytest.raises(ValueError, match="num_candidates must be >= 1"):
            self._make_agent().generate("valid task", 0)

    def test_negative_candidates_raises(self):
        with pytest.raises(ValueError, match="num_candidates must be >= 1"):
            self._make_agent().generate("valid task", -1)


class TestGeneratorAgentGenerate:
    def _make_agent_with_mock_run(self, agent_result: FakeAgentResult) -> GeneratorAgent:
        client = MagicMock()
        client._config = MagicMock()
        client._config.default_provider = "openai"
        agent = GeneratorAgent(
            llm_client=client,
            config=AgentConfig(max_iterations=1, enabled_tools=frozenset()),
        )
        agent._run_async = MagicMock(return_value=agent_result)
        return agent

    def test_happy_path_returns_candidates(self):
        result = FakeAgentResult(answer="1. Prompt A\n2. Prompt B\n3. Prompt C")
        candidates = self._make_agent_with_mock_run(result).generate("test task", 3)
        assert candidates == ["Prompt A", "Prompt B", "Prompt C"]

    def test_deduplicates_candidates(self):
        result = FakeAgentResult(answer='["A", "A", "B", "C"]')
        candidates = self._make_agent_with_mock_run(result).generate("test task", 3)
        assert candidates == ["A", "B", "C"]

    def test_truncates_extra_candidates(self):
        result = FakeAgentResult(answer='["A", "B", "C", "D", "E"]')
        assert len(self._make_agent_with_mock_run(result).generate("test task", 3)) == 3

    def test_timeout_with_no_answer_raises(self):
        result = FakeAgentResult(answer=None, timed_out=True, iterations=5)
        with pytest.raises(TimeoutError, match="timed out"):
            self._make_agent_with_mock_run(result).generate("test task", 3)

    def test_timeout_with_answer_parses(self):
        result = FakeAgentResult(answer="1. Partial A\n2. Partial B", timed_out=True)
        candidates = self._make_agent_with_mock_run(result).generate("test task", 2)
        assert candidates == ["Partial A", "Partial B"]

    def test_empty_answer_raises_runtime_error(self):
        result = FakeAgentResult(answer="")
        with pytest.raises(RuntimeError, match="empty answer"):
            self._make_agent_with_mock_run(result).generate("test task", 3)

    def test_agent_exception_wrapped_in_runtime_error(self):
        client = MagicMock()
        agent = GeneratorAgent(
            llm_client=client,
            config=AgentConfig(max_iterations=1, enabled_tools=frozenset()),
        )
        agent._run_async = MagicMock(side_effect=ConnectionError("network down"))
        with pytest.raises(RuntimeError, match="Generator agent failed") as exc_info:
            agent.generate("test task", 3)
        assert isinstance(exc_info.value.__cause__, ConnectionError)

    def test_strips_whitespace_from_candidates(self):
        result = FakeAgentResult(answer='["  padded  ", " also padded "]')
        candidates = self._make_agent_with_mock_run(result).generate("test task", 2)
        assert candidates == ["padded", "also padded"]

    def test_follow_up_on_insufficient_candidates(self):
        client = MagicMock()
        agent = GeneratorAgent(
            llm_client=client,
            config=AgentConfig(max_iterations=1, enabled_tools=frozenset()),
        )
        first = FakeAgentResult(answer='["Only one"]')
        second = FakeAgentResult(answer='["Second", "Third"]')
        agent._run_async = MagicMock(side_effect=[first, second])
        candidates = agent.generate("test task", 3)
        assert len(candidates) == 3
        assert "Only one" in candidates

    def test_follow_up_failure_returns_partial(self):
        client = MagicMock()
        agent = GeneratorAgent(
            llm_client=client,
            config=AgentConfig(max_iterations=1, enabled_tools=frozenset()),
        )
        first = FakeAgentResult(answer='["Only one"]')
        agent._run_async = MagicMock(
            side_effect=[first, RuntimeError("follow-up failed")],
        )
        candidates = agent.generate("test task", 3)
        assert candidates == ["Only one"]


class TestDeduplicate:
    def test_removes_duplicates(self):
        assert GeneratorAgent._deduplicate(["a", "b", "a", "c"]) == ["a", "b", "c"]

    def test_strips_whitespace(self):
        assert GeneratorAgent._deduplicate(["  x  ", "y "]) == ["x", "y"]

    def test_filters_empty(self):
        assert GeneratorAgent._deduplicate(["a", "", "  ", "b"]) == ["a", "b"]

    def test_exclude_set(self):
        result = GeneratorAgent._deduplicate(["a", "b", "c"], exclude={"a"})
        assert result == ["b", "c"]
