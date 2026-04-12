"""Tests for evaluator_agent.agent.EvaluatorAgent."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from evaluator_agent.agent import EvaluatorAgent
from evaluator_agent.config import EvaluatorConfig

ASYNC_PATCH = "evaluator_agent.agent.run_async_in_sync"

# Test constants
SAMPLE_CANDIDATE = "Write a clear summary of the article in 3 sentences."
SAMPLE_TASK = "Summarize news articles for a general audience."
DEFAULT_MIN = 1.0
DEFAULT_MAX = 10.0

# Score responses
SCORE_7_5 = "7.5"
SCORE_JSON_8 = '{"score": 8.0}'
SCORE_INLINE_6_5 = "I rate this a 6.5 out of 10"
SCORE_ABOVE_MAX = "15"
SCORE_BELOW_MIN = "0.5"
SCORE_INTEGER = "8"
SCORE_NAN = "NaN"
SCORE_NO_NUMBER = "no score here"
SCORE_EMPTY = ""

# Parse score test data
PARSE_JSON = '{"score": 7.5}'
PARSE_JSON_SURROUNDED = 'Here is my score: {"score": 9}'
PARSE_OWN_LINE = "7.5\n"
PARSE_INLINE = "I'd rate this a 6 out of 10"
PARSE_NO_NUMBER = "no numbers here at all"
PARSE_NEGATIVE = "-3.5"


def _mock_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    return resp


class TestEvaluatorAgentInit:
    def test_accepts_llm_client(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        assert agent._config.min_score == DEFAULT_MIN

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
            self._agent().evaluate("", SAMPLE_TASK)

    def test_whitespace_candidate_raises(self):
        with pytest.raises(ValueError, match="candidate"):
            self._agent().evaluate("   ", SAMPLE_TASK)

    def test_empty_task_raises(self):
        with pytest.raises(ValueError, match="task_description"):
            self._agent().evaluate(SAMPLE_CANDIDATE, "")

    def test_whitespace_task_raises(self):
        with pytest.raises(ValueError, match="task_description"):
            self._agent().evaluate(SAMPLE_CANDIDATE, "   ")


class TestEvaluatorAgentEvaluate:
    def test_happy_path_returns_score(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response(SCORE_7_5)):
            assert agent.evaluate(SAMPLE_CANDIDATE, SAMPLE_TASK) == 7.5

    def test_json_format_score(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response(SCORE_JSON_8)):
            assert agent.evaluate(SAMPLE_CANDIDATE, SAMPLE_TASK) == 8.0

    def test_inline_score(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response(SCORE_INLINE_6_5)):
            assert agent.evaluate(SAMPLE_CANDIDATE, SAMPLE_TASK) == 6.5

    def test_clamps_above_max(self):
        cfg = EvaluatorConfig(min_score=DEFAULT_MIN, max_score=DEFAULT_MAX)
        agent = EvaluatorAgent(llm_client=MagicMock(), config=cfg)
        with patch(ASYNC_PATCH, return_value=_mock_response(SCORE_ABOVE_MAX)):
            assert agent.evaluate(SAMPLE_CANDIDATE, SAMPLE_TASK) == DEFAULT_MAX

    def test_clamps_below_min(self):
        cfg = EvaluatorConfig(min_score=DEFAULT_MIN, max_score=DEFAULT_MAX)
        agent = EvaluatorAgent(llm_client=MagicMock(), config=cfg)
        with patch(ASYNC_PATCH, return_value=_mock_response(SCORE_BELOW_MIN)):
            assert agent.evaluate(SAMPLE_CANDIDATE, SAMPLE_TASK) == DEFAULT_MIN

    def test_nan_raises_value_error(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response(SCORE_NAN)):
            with pytest.raises(ValueError, match="Could not parse"):
                agent.evaluate(SAMPLE_CANDIDATE, SAMPLE_TASK)

    def test_no_number_raises_value_error(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response(SCORE_NO_NUMBER)):
            with pytest.raises(ValueError, match="Could not parse"):
                agent.evaluate(SAMPLE_CANDIDATE, SAMPLE_TASK)

    def test_empty_response_raises_runtime_error(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response(SCORE_EMPTY)):
            with pytest.raises(RuntimeError, match="empty response"):
                agent.evaluate(SAMPLE_CANDIDATE, SAMPLE_TASK)

    def test_llm_exception_wrapped_in_runtime_error(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, side_effect=ConnectionError("down")):
            with pytest.raises(RuntimeError, match="Evaluator LLM call failed") as exc_info:
                agent.evaluate(SAMPLE_CANDIDATE, SAMPLE_TASK)
        assert isinstance(exc_info.value.__cause__, ConnectionError)

    def test_integer_score(self):
        agent = EvaluatorAgent(llm_client=MagicMock())
        with patch(ASYNC_PATCH, return_value=_mock_response(SCORE_INTEGER)):
            assert agent.evaluate(SAMPLE_CANDIDATE, SAMPLE_TASK) == 8.0


class TestParseScore:
    def test_json_object(self):
        assert EvaluatorAgent._parse_score(PARSE_JSON) == 7.5

    def test_json_with_surrounding_text(self):
        assert EvaluatorAgent._parse_score(PARSE_JSON_SURROUNDED) == 9.0

    def test_number_on_own_line(self):
        assert EvaluatorAgent._parse_score(PARSE_OWN_LINE) == 7.5

    def test_inline_number(self):
        assert EvaluatorAgent._parse_score(PARSE_INLINE) == 6.0

    def test_no_number_raises(self):
        with pytest.raises(ValueError, match="Could not parse"):
            EvaluatorAgent._parse_score(PARSE_NO_NUMBER)

    def test_negative_number(self):
        assert EvaluatorAgent._parse_score(PARSE_NEGATIVE) == -3.5
