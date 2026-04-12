"""Tests for evaluator_agent.agent.EvaluatorAgent."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from evaluator_agent.agent import EvaluatorAgent
from evaluator_agent.config import EvaluatorConfig

ASYNC_PATCH = "evaluator_agent.agent.run_async_in_sync"


def _mock_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    return resp


class TestEvaluatorAgentInit:
    def test_accepts_llm_client(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        assert agent._config.min_score == 1.0

    def test_accepts_custom_config(self):
        cfg = EvaluatorConfig(min_score=0.0, max_score=1.0)
        agent = EvaluatorAgent(llm_client=MagicMock(), config=cfg)
        assert agent._config.max_score == 1.0

    def test_accepts_custom_logger(self):
        custom = logging.getLogger("test")
        agent = EvaluatorAgent(llm_client=MagicMock(), agent_logger=custom)
        assert agent._log is custom


class TestEvaluatorAgentValidation:
    def _agent(self) -> EvaluatorAgent:
        return EvaluatorAgent(llm_client=MagicMock())

    def test_empty_candidate_raises(self):
        with pytest.raises(ValueError, match="candidate"):
            self._agent().evaluate("", "task")

    def test_whitespace_candidate_raises(self):
        with pytest.raises(ValueError, match="candidate"):
            self._agent().evaluate("   ", "task")

    def test_empty_task_raises(self):
        with pytest.raises(ValueError, match="task_description"):
            self._agent().evaluate("candidate", "")

    def test_whitespace_task_raises(self):
        with pytest.raises(ValueError, match="task_description"):
            self._agent().evaluate("candidate", "   ")


class TestEvaluatorAgentEvaluate:
    def test_happy_path_returns_score(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response("7.5")):
            score = agent.evaluate("test prompt", "test task")
        assert score == 7.5

    def test_json_format_score(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response('{"score": 8.0}')):
            assert agent.evaluate("prompt", "task") == 8.0

    def test_inline_score(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response("I rate this a 6.5 out of 10")):
            assert agent.evaluate("prompt", "task") == 6.5

    def test_clamps_above_max(self):
        cfg = EvaluatorConfig(min_score=1.0, max_score=10.0)
        agent = EvaluatorAgent(llm_client=MagicMock(), config=cfg)
        with patch(ASYNC_PATCH, return_value=_mock_response("15")):
            assert agent.evaluate("prompt", "task") == 10.0

    def test_clamps_below_min(self):
        cfg = EvaluatorConfig(min_score=1.0, max_score=10.0)
        agent = EvaluatorAgent(llm_client=MagicMock(), config=cfg)
        with patch(ASYNC_PATCH, return_value=_mock_response("0.5")):
            assert agent.evaluate("prompt", "task") == 1.0

    def test_nan_raises_value_error(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response("NaN")):
            with pytest.raises(ValueError, match="Could not parse"):
                agent.evaluate("prompt", "task")

    def test_no_number_raises_value_error(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response("no score here")):
            with pytest.raises(ValueError, match="Could not parse"):
                agent.evaluate("prompt", "task")

    def test_empty_response_raises_runtime_error(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response("")):
            with pytest.raises(RuntimeError, match="empty response"):
                agent.evaluate("prompt", "task")

    def test_llm_exception_wrapped_in_runtime_error(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, side_effect=ConnectionError("down")):
            with pytest.raises(RuntimeError, match="Evaluator LLM call failed") as exc_info:
                agent.evaluate("prompt", "task")
        assert isinstance(exc_info.value.__cause__, ConnectionError)

    def test_integer_score(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response("8")):
            assert agent.evaluate("prompt", "task") == 8.0


class TestParseScore:
    def test_json_object(self):
        assert EvaluatorAgent._parse_score('{"score": 7.5}') == 7.5

    def test_json_with_surrounding_text(self):
        assert EvaluatorAgent._parse_score('Here is my score: {"score": 9}') == 9.0

    def test_number_on_own_line(self):
        assert EvaluatorAgent._parse_score("7.5\n") == 7.5

    def test_inline_number(self):
        assert EvaluatorAgent._parse_score("I'd rate this a 6 out of 10") == 6.0

    def test_no_number_raises(self):
        with pytest.raises(ValueError, match="Could not parse"):
            EvaluatorAgent._parse_score("no numbers here at all")

    def test_negative_number(self):
        assert EvaluatorAgent._parse_score("-3.5") == -3.5
