"""Tests for the Generator ReAct Agent (config, parser, and agent logic)."""

from __future__ import annotations

import pytest

from generator_react_agent.config import (
    AgentConfig,
    DEFAULT_SYSTEM_PROMPT,
    KNOWN_TOOL_NAMES,
)
from generator_react_agent.parser import parse_candidates


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
