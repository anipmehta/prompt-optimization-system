"""Tests for generator_react_agent.config."""

from __future__ import annotations

import pytest

from generator_react_agent.config import (
    DEFAULT_SYSTEM_PROMPT,
    KNOWN_TOOL_NAMES,
    AgentConfig,
)


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


class TestSystemPrompt:
    def test_num_candidates_substitution(self):
        prompt = DEFAULT_SYSTEM_PROMPT.format(num_candidates=7)
        assert "7" in prompt
        assert "exactly 7 diverse" in prompt

    def test_contains_formatting_instructions(self):
        prompt = DEFAULT_SYSTEM_PROMPT.format(num_candidates=3)
        assert "numbered list" in prompt
