"""Unit tests for the Orchestrator class."""

import pytest

from prompt_optimization_orchestrator.exceptions import RunNotFoundError, ValidationError
from prompt_optimization_orchestrator.models import OptimizationConfig, RunStatus
from prompt_optimization_orchestrator.orchestrator import Orchestrator


class FakeGenerator:
    def generate(self, task_description: str, num_candidates: int) -> list[str]:
        return [f"candidate_{i}" for i in range(num_candidates)]


class FakeSelector:
    def select(self, candidates: list[str]) -> str:
        return candidates[0]

    def reward(self, score: float) -> None:
        pass


class FakeEvaluator:
    def evaluate(self, candidate: str, task_description: str) -> float:
        return 0.9


@pytest.fixture
def orchestrator():
    return Orchestrator(
        generator=FakeGenerator(),
        selector=FakeSelector(),
        evaluator=FakeEvaluator(),
    )


@pytest.fixture
def valid_config():
    return OptimizationConfig(num_candidates=3, num_iterations=5)


class TestStartRun:
    def test_returns_unique_run_ids(self, orchestrator, valid_config):
        id1 = orchestrator.start_run("task A", valid_config)
        id2 = orchestrator.start_run("task B", valid_config)
        assert id1 != id2

    def test_creates_run_with_pending_status(self, orchestrator, valid_config):
        run_id = orchestrator.start_run("task A", valid_config)
        run = orchestrator.get_run(run_id)
        assert run.status == RunStatus.PENDING
        assert run.task_description == "task A"
        assert run.config == valid_config
        assert run.iterations == []

    def test_empty_task_description_raises(self, orchestrator, valid_config):
        with pytest.raises(ValidationError, match="task_description is required"):
            orchestrator.start_run("", valid_config)

    def test_invalid_config_raises(self, orchestrator):
        bad_config = OptimizationConfig(num_candidates=0, num_iterations=5)
        with pytest.raises(ValidationError, match="num_candidates"):
            orchestrator.start_run("task A", bad_config)


class TestGetRun:
    def test_returns_existing_run(self, orchestrator, valid_config):
        run_id = orchestrator.start_run("task A", valid_config)
        run = orchestrator.get_run(run_id)
        assert run.run_id == run_id

    def test_unknown_id_raises(self, orchestrator):
        with pytest.raises(RunNotFoundError, match="Run not found"):
            orchestrator.get_run("nonexistent-id")
