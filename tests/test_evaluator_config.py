"""Tests for evaluator_agent.config."""

from __future__ import annotations

import pytest

from evaluator_agent.config import DEFAULT_RUBRIC_TEMPLATE, EvaluatorConfig


class TestEvaluatorConfig:
    def test_defaults(self):
        cfg = EvaluatorConfig()
        assert cfg.min_score == 1.0
        assert cfg.max_score == 10.0
        assert cfg.rubric_template == DEFAULT_RUBRIC_TEMPLATE

    def test_custom_values(self):
        cfg = EvaluatorConfig(
            min_score=0.0, max_score=1.0, rubric_template="Rate: {candidate} {task_description}"
        )
        assert cfg.min_score == 0.0
        assert cfg.max_score == 1.0

    def test_min_equals_max_raises(self):
        with pytest.raises(ValueError, match="min_score.*must be less than"):
            EvaluatorConfig(min_score=5.0, max_score=5.0)

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValueError, match="min_score.*must be less than"):
            EvaluatorConfig(min_score=10.0, max_score=1.0)

    def test_empty_rubric_raises(self):
        with pytest.raises(ValueError, match="rubric_template must not be empty"):
            EvaluatorConfig(rubric_template="   ")

    def test_frozen(self):
        cfg = EvaluatorConfig()
        with pytest.raises(AttributeError):
            cfg.min_score = 0.0  # type: ignore[misc]


class TestDefaultRubric:
    def test_has_placeholders(self):
        assert "{candidate}" in DEFAULT_RUBRIC_TEMPLATE
        assert "{task_description}" in DEFAULT_RUBRIC_TEMPLATE

    def test_formats_without_error(self):
        result = DEFAULT_RUBRIC_TEMPLATE.format(
            candidate="test prompt",
            task_description="test task",
        )
        assert "test prompt" in result
        assert "test task" in result
