"""Tests for the Generator ReAct Agent (config, parser, and agent logic)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from generator_react_agent.agent import GeneratorAgent
from generator_react_agent.config import (
    DEFAULT_SYSTEM_PROMPT,
    KNOWN_TOOL_NAMES,
    AgentConfig,
)
from generator_react_agent.parser import parse_candidates
from generator_react_agent.prompt_templates import retrieve_templates, search_examples
from generator_react_agent.registry import build_tool_registry
from generator_react_agent.tools import (
    _run_async_in_thread,
    make_analyze_task,
    make_refine_candidate,
)

# ── Config tests ──────────────────────────────────────────────────────


class TestAgentConfig:
    def test_defaults(self):
        cfg = AgentConfig()
        assert cfg.max_iterations == 5
        assert cfg.enabled_tools == KNOWN_TOOL_NAMES
        assert cfg.system_prompt_template == DEFAULT_SYSTEM_PROMPT

    def test_custom_values(self):
        cfg = AgentConfig(
            max_iterations=10,
            enabled_tools=frozenset({"analyze_task"}),
        )
        assert cfg.max_iterations == 10
        assert cfg.enabled_tools == frozenset({"analyze_task"})

    def test_max_iterations_zero_raises(self):
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            AgentConfig(max_iterations=0)

    def test_max_iterations_negative_raises(self):
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            AgentConfig(max_iterations=-5)

    def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool names"):
            AgentConfig(enabled_tools=frozenset({"bogus_tool"}))

    def test_empty_prompt_template_raises(self):
        with pytest.raises(ValueError, match="system_prompt_template must not be empty"):
            AgentConfig(system_prompt_template="   ")

    def test_frozen(self):
        cfg = AgentConfig()
        with pytest.raises(AttributeError):
            cfg.max_iterations = 10  # type: ignore[misc]


# ── Parser tests ──────────────────────────────────────────────────────


class TestParseCandidates:
    def test_json_array(self):
        answer = '["prompt A", "prompt B", "prompt C"]'
        result = parse_candidates(answer, 3)
        assert result == ["prompt A", "prompt B", "prompt C"]

    def test_json_array_with_surrounding_text(self):
        answer = 'Here are the candidates:\n["one", "two"]\nDone.'
        result = parse_candidates(answer, 2)
        assert result == ["one", "two"]

    def test_numbered_list(self):
        answer = "1. First prompt\n2. Second prompt\n3. Third prompt"
        result = parse_candidates(answer, 3)
        assert result == ["First prompt", "Second prompt", "Third prompt"]

    def test_numbered_list_with_parens(self):
        answer = "1) Alpha\n2) Beta"
        result = parse_candidates(answer, 2)
        assert result == ["Alpha", "Beta"]

    def test_delimiter_dashes(self):
        answer = "Prompt one\n---\nPrompt two\n---\nPrompt three"
        result = parse_candidates(answer, 3)
        assert result == ["Prompt one", "Prompt two", "Prompt three"]

    def test_delimiter_equals(self):
        answer = "A\n===\nB"
        result = parse_candidates(answer, 2)
        assert result == ["A", "B"]

    def test_fallback_single_candidate(self):
        answer = "Just one big prompt here."
        result = parse_candidates(answer, 1)
        assert result == ["Just one big prompt here."]

    def test_empty_string_raises(self):
        with pytest.raises(RuntimeError, match="empty answer"):
            parse_candidates("", 1)

    def test_whitespace_only_raises(self):
        with pytest.raises(RuntimeError, match="empty answer"):
            parse_candidates("   \n  ", 1)

    def test_strips_whitespace_from_candidates(self):
        answer = '["  padded  ", " also padded "]'
        result = parse_candidates(answer, 2)
        assert result == ["padded", "also padded"]

    def test_filters_empty_json_entries(self):
        answer = '["good", "", "also good"]'
        result = parse_candidates(answer, 2)
        assert result == ["good", "also good"]


# ── System prompt template tests ──────────────────────────────────────


class TestSystemPrompt:
    def test_num_candidates_substitution(self):
        prompt = DEFAULT_SYSTEM_PROMPT.format(num_candidates=7)
        assert "7" in prompt
        assert "exactly 7 diverse" in prompt

    def test_contains_formatting_instructions(self):
        prompt = DEFAULT_SYSTEM_PROMPT.format(num_candidates=3)
        assert "numbered list" in prompt


# ── Tool tests ────────────────────────────────────────────────────────


class TestStaticTools:
    def test_retrieve_templates_returns_nonempty(self):
        result = retrieve_templates("coding task")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Direct instruction" in result

    def test_search_examples_returns_nonempty(self):
        result = search_examples("summarization")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "No specific examples" in result


class TestLLMBackedTools:
    def _mock_llm_client(self, content: str = "analysis result") -> MagicMock:
        client = MagicMock()
        response = MagicMock()
        response.content = content
        client.complete = AsyncMock(return_value=response)
        return client

    def test_analyze_task_calls_llm(self):
        client = self._mock_llm_client("Domain: coding")
        tool = make_analyze_task(client)
        result = tool("Write a sort function")
        assert result == "Domain: coding"
        client.complete.assert_called_once()

    def test_analyze_task_fallback_on_empty_content(self):
        client = self._mock_llm_client("")
        response = MagicMock()
        response.content = ""
        client.complete = AsyncMock(return_value=response)
        tool = make_analyze_task(client)
        result = tool("some task")
        assert result == "No analysis produced."

    def test_refine_candidate_calls_llm(self):
        client = self._mock_llm_client("Improved prompt")
        tool = make_refine_candidate(client)
        result = tool("draft prompt")
        assert result == "Improved prompt"
        client.complete.assert_called_once()

    def test_refine_candidate_fallback_on_empty_content(self):
        client = self._mock_llm_client("")
        response = MagicMock()
        response.content = ""
        client.complete = AsyncMock(return_value=response)
        tool = make_refine_candidate(client)
        result = tool("draft")
        assert result == "No refinement produced."


class TestRunAsyncInThread:
    def test_runs_coroutine(self):
        async def coro():
            return 42

        assert _run_async_in_thread(coro()) == 42

    def test_propagates_exception(self):
        async def failing():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            _run_async_in_thread(failing())


class TestBuildToolRegistry:
    def test_all_tools_registered(self):
        client = MagicMock()
        client.complete = AsyncMock()
        registry = build_tool_registry(client, KNOWN_TOOL_NAMES)
        assert set(registry.list_tools()) == set(KNOWN_TOOL_NAMES)

    def test_subset_of_tools(self):
        client = MagicMock()
        client.complete = AsyncMock()
        enabled = frozenset({"analyze_task", "retrieve_templates"})
        registry = build_tool_registry(client, enabled)
        assert set(registry.list_tools()) == {"analyze_task", "retrieve_templates"}

    def test_empty_tools(self):
        client = MagicMock()
        registry = build_tool_registry(client, frozenset())
        assert registry.list_tools() == []


# ── GeneratorAgent tests ──────────────────────────────────────────────


@dataclass
class FakeAgentResult:
    answer: str | None
    reasoning_trace: list = None  # type: ignore[assignment]
    iterations: int = 1
    timed_out: bool = False

    def __post_init__(self):
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
    def _make_agent(self):

        client = MagicMock()
        return GeneratorAgent(
            llm_client=client,
            config=AgentConfig(enabled_tools=frozenset()),
        )

    def test_empty_task_raises(self):
        agent = self._make_agent()
        with pytest.raises(ValueError, match="non-empty"):
            agent.generate("", 3)

    def test_whitespace_task_raises(self):
        agent = self._make_agent()
        with pytest.raises(ValueError, match="non-empty"):
            agent.generate("   ", 3)

    def test_zero_candidates_raises(self):
        agent = self._make_agent()
        with pytest.raises(ValueError, match="num_candidates must be >= 1"):
            agent.generate("valid task", 0)

    def test_negative_candidates_raises(self):
        agent = self._make_agent()
        with pytest.raises(ValueError, match="num_candidates must be >= 1"):
            agent.generate("valid task", -1)


class TestGeneratorAgentGenerate:
    def _make_agent_with_mock_run(self, agent_result):

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
        agent = self._make_agent_with_mock_run(result)
        candidates = agent.generate("test task", 3)
        assert candidates == ["Prompt A", "Prompt B", "Prompt C"]

    def test_deduplicates_candidates(self):
        result = FakeAgentResult(answer='["A", "A", "B", "C"]')
        agent = self._make_agent_with_mock_run(result)
        candidates = agent.generate("test task", 3)
        assert candidates == ["A", "B", "C"]

    def test_truncates_extra_candidates(self):
        result = FakeAgentResult(answer='["A", "B", "C", "D", "E"]')
        agent = self._make_agent_with_mock_run(result)
        candidates = agent.generate("test task", 3)
        assert len(candidates) == 3

    def test_timeout_with_no_answer_raises(self):
        result = FakeAgentResult(answer=None, timed_out=True, iterations=5)
        agent = self._make_agent_with_mock_run(result)
        with pytest.raises(TimeoutError, match="timed out"):
            agent.generate("test task", 3)

    def test_timeout_with_answer_parses(self):
        result = FakeAgentResult(
            answer="1. Partial A\n2. Partial B",
            timed_out=True,
        )
        agent = self._make_agent_with_mock_run(result)
        candidates = agent.generate("test task", 2)
        assert candidates == ["Partial A", "Partial B"]

    def test_empty_answer_raises_runtime_error(self):
        result = FakeAgentResult(answer="")
        agent = self._make_agent_with_mock_run(result)
        with pytest.raises(RuntimeError, match="empty answer"):
            agent.generate("test task", 3)

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
        agent = self._make_agent_with_mock_run(result)
        candidates = agent.generate("test task", 2)
        assert candidates == ["padded", "also padded"]

    def test_follow_up_on_insufficient_candidates(self):

        client = MagicMock()
        agent = GeneratorAgent(
            llm_client=client,
            config=AgentConfig(max_iterations=1, enabled_tools=frozenset()),
        )
        first_result = FakeAgentResult(answer='["Only one"]')
        second_result = FakeAgentResult(answer='["Second", "Third"]')
        agent._run_async = MagicMock(side_effect=[first_result, second_result])
        candidates = agent.generate("test task", 3)
        assert len(candidates) == 3
        assert "Only one" in candidates
        assert "Second" in candidates
        assert "Third" in candidates

    def test_follow_up_failure_returns_partial(self):

        client = MagicMock()
        agent = GeneratorAgent(
            llm_client=client,
            config=AgentConfig(max_iterations=1, enabled_tools=frozenset()),
        )
        first_result = FakeAgentResult(answer='["Only one"]')
        agent._run_async = MagicMock(side_effect=[first_result, RuntimeError("follow-up failed")])
        candidates = agent.generate("test task", 3)
        assert candidates == ["Only one"]
