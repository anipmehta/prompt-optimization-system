"""Unit tests for input validation."""

import pytest

from prompt_optimization_orchestrator.exceptions import ValidationError
from prompt_optimization_orchestrator.models import OptimizationConfig
from prompt_optimization_orchestrator.validation import validate_config, validate_task_description


class TestValidateTaskDescription:
    def test_valid_description(self):
        validate_task_description("summarize articles")  # should not raise

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError, match="task_description is required"):
            validate_task_description("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="task_description is required"):
            validate_task_description("   \t\n  ")


class TestValidateConfig:
    def test_valid_config(self):
        validate_config(OptimizationConfig(num_candidates=5, num_iterations=3))

    def test_zero_candidates_raises(self):
        with pytest.raises(ValidationError, match="num_candidates"):
            validate_config(OptimizationConfig(num_candidates=0, num_iterations=3))

    def test_negative_iterations_raises(self):
        with pytest.raises(ValidationError, match="num_iterations"):
            validate_config(OptimizationConfig(num_candidates=5, num_iterations=-1))

    def test_negative_retry_limit_raises(self):
        with pytest.raises(ValidationError, match="retry_limit"):
            validate_config(OptimizationConfig(num_candidates=5, num_iterations=3, retry_limit=-1))

    def test_multiple_invalid_fields_lists_all(self):
        with pytest.raises(ValidationError) as exc_info:
            validate_config(OptimizationConfig(num_candidates=0, num_iterations=-1, retry_limit=-1))
        msg = str(exc_info.value)
        assert "num_candidates" in msg
        assert "num_iterations" in msg
        assert "retry_limit" in msg
