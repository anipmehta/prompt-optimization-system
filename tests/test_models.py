"""Unit tests for data models and enums."""

from prompt_optimization_orchestrator.models import (
    IterationResult,
    IterationStatus,
    OptimizationConfig,
    OptimizationResult,
    OptimizationRun,
    RunStatus,
)


class TestIterationStatus:
    def test_values(self):
        assert {s.value for s in IterationStatus} == {
            "pending",
            "in_progress",
            "complete",
            "failed",
            "degraded",
        }


class TestRunStatus:
    def test_values(self):
        assert {s.value for s in RunStatus} == {
            "pending",
            "in_progress",
            "complete",
            "aborted",
        }


class TestOptimizationConfig:
    def test_defaults(self):
        config = OptimizationConfig(num_candidates=5, num_iterations=10)
        assert config.retry_limit == 3
        assert config.evaluation_criteria == ""

    def test_custom_values(self):
        config = OptimizationConfig(
            num_candidates=5,
            num_iterations=10,
            retry_limit=0,
            evaluation_criteria="accuracy",
        )
        assert config.retry_limit == 0
        assert config.evaluation_criteria == "accuracy"


class TestIterationResult:
    def test_defaults(self):
        result = IterationResult(iteration_number=0, status=IterationStatus.PENDING)
        assert result.candidates == []
        assert result.selected_candidate is None
        assert result.evaluation_score is None
        assert result.error is None


class TestOptimizationRun:
    def test_defaults(self):
        config = OptimizationConfig(num_candidates=3, num_iterations=5)
        run = OptimizationRun(run_id="r1", task_description="test", config=config)
        assert run.status == RunStatus.PENDING
        assert run.iterations == []


class TestOptimizationResult:
    def test_construction(self):
        result = OptimizationResult(
            run_id="r1",
            status=RunStatus.COMPLETE,
            best_candidate="prompt A",
            best_score=0.95,
            iterations=[],
        )
        assert result.best_candidate == "prompt A"
        assert result.best_score == 0.95
