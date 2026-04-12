"""Tests for generator_react_agent tools, prompt_templates, and registry."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from generator_react_agent.config import KNOWN_TOOL_NAMES
from generator_react_agent.prompt_templates import retrieve_templates, search_examples
from generator_react_agent.registry import build_tool_registry
from generator_react_agent.tools import (
    _run_async_in_thread,
    make_analyze_task,
    make_refine_candidate,
)


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
        assert tool("some task") == "No analysis produced."

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
        assert tool("draft") == "No refinement produced."


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
