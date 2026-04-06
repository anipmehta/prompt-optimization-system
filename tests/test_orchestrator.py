"""Unit tests for the Orchestrator class."""

import logging

import pytest

from prompt_optimization_orchestrator.exceptions import (
    DataIntegrityError,
    RunNotFoundError,
    ValidationError,
)
from prompt_optimization_orchestrator.models import (
    IterationResult,
    IterationStatus,
    OptimizationConfig,
    RunStatus,
)
from prompt_optimization_orchestrator.orchestrator import Orchestrator

# --- Shared fakes ---


class FakeGenerator:
    def __init__(self, candidates=None):
        self._candidates = candidates

    def generate(self, task_description: str, num_candidates: int) -> list[str]:
        if self._candidates is not None:
            return self._candidates
        return [f"candidate_{i}" for i in range(num_candidates)]


class FailThenSucceedGenerator:
    def __init__(self, fail_count: int):
        self._fail_count = fail_count
        self._calls = 0

    def generate(self, task_description: str, num_candidates: int) -> list[str]:
        self._calls += 1
        if self._calls <= self._fail_count:
            raise ConnectionError("Generator unavailable")
        return [f"candidate_{i}" for i in range(num_candidates)]


class AlwaysFailGenerator:
    def generate(self, task_description: str, num_candidates: int) -> list[str]:
        raise ConnectionError("Generator unavailable")


class EmptyGenerator:
    def generate(self, task_description: str, num_candidates: int) -> list[str]:
        return []


class FakeSelector:
    def select(self, candidates: list[str]) -> str:
        return candidates[0]

    def reward(self, score: float) -> None:
        pass


class BadCandidateSelector:
    def select(self, candidates: list[str]) -> str:
        return "not_in_set"

    def reward(self, score: float) -> None:
        pass


class FailThenSucceedSelector:
    def __init__(self, fail_count: int):
        self._fail_count = fail_count
        self._calls = 0

    def select(self, candidates: list[str]) -> str:
        self._calls += 1
        if self._calls <= self._fail_count:
            raise ConnectionError("Selector unavailable")
        return candidates[0]

    def reward(self, score: float) -> None:
        pass


class AlwaysFailSelector:
    def select(self, candidates: list[str]) -> str:
        raise ConnectionError("Selector unavailable")

    def reward(self, score: float) -> None:
        pass


class FakeEvaluator:
    def evaluate(self, candidate: str, task_description: str) -> float:
        return 0.9


# --- Helpers ---


def _make_orchestrator(generator=None, selector=None, evaluator=None, logger=None):
    return Orchestrator(
        generator=generator or FakeGenerator(),
        selector=selector or FakeSelector(),
        evaluator=evaluator or FakeEvaluator(),
        logger=logger,
    )


def _make_iteration(candidates=None):
    it = IterationResult(iteration_number=0, status=IterationStatus.IN_PROGRESS)
    if candidates is not None:
        it.candidates = candidates
    return it


@pytest.fixture
def orchestrator():
    return _make_orchestrator()


@pytest.fixture
def valid_config():
    return OptimizationConfig(num_candidates=3, num_iterations=5)


# --- start_run / get_run ---


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


# --- Generate step ---


class TestGenerateCandidates:
    def test_returns_candidates_on_success(self):
        orch = _make_orchestrator()
        result = orch._generate_candidates("task", 3, retry_limit=0)
        assert len(result) == 3

    def test_retries_on_failure_then_succeeds(self):
        gen = FailThenSucceedGenerator(fail_count=2)
        orch = _make_orchestrator(generator=gen)
        result = orch._generate_candidates("task", 3, retry_limit=2)
        assert len(result) == 3

    def test_raises_after_exhausting_retries(self):
        orch = _make_orchestrator(generator=AlwaysFailGenerator())
        with pytest.raises(ConnectionError):
            orch._generate_candidates("task", 3, retry_limit=2)

    def test_logs_warning_on_fewer_candidates(self, caplog):
        gen = FakeGenerator(candidates=["only_one"])
        orch = _make_orchestrator(generator=gen, logger=logging.getLogger("test"))
        with caplog.at_level(logging.WARNING, logger="test"):
            result = orch._generate_candidates("task", 3, retry_limit=0)
        assert len(result) == 1
        assert "expected 3" in caplog.text


class TestRunGenerateStep:
    def test_success_populates_candidates(self):
        orch = _make_orchestrator()
        iteration = _make_iteration()
        ok = orch._run_generate_step(iteration, "task", 3, retry_limit=0)
        assert ok is True
        assert len(iteration.candidates) == 3

    def test_zero_candidates_marks_failed(self):
        orch = _make_orchestrator(generator=EmptyGenerator())
        iteration = _make_iteration()
        ok = orch._run_generate_step(iteration, "task", 3, retry_limit=0)
        assert ok is False
        assert iteration.status == IterationStatus.FAILED
        assert "zero candidates" in iteration.error

    def test_exception_marks_failed(self):
        orch = _make_orchestrator(generator=AlwaysFailGenerator())
        iteration = _make_iteration()
        ok = orch._run_generate_step(iteration, "task", 3, retry_limit=1)
        assert ok is False
        assert iteration.status == IterationStatus.FAILED
        assert "failed after retries" in iteration.error


# --- Select step ---


class TestSelectCandidate:
    def test_returns_valid_candidate(self):
        orch = _make_orchestrator()
        result = orch._select_candidate(["a", "b"], retry_limit=0)
        assert result == "a"

    def test_raises_data_integrity_on_bad_candidate(self):
        orch = _make_orchestrator(selector=BadCandidateSelector())
        with pytest.raises(DataIntegrityError, match="not in original set"):
            orch._select_candidate(["a", "b"], retry_limit=0)

    def test_retries_on_failure_then_succeeds(self):
        sel = FailThenSucceedSelector(fail_count=2)
        orch = _make_orchestrator(selector=sel)
        result = orch._select_candidate(["a", "b"], retry_limit=2)
        assert result == "a"

    def test_raises_after_exhausting_retries(self):
        orch = _make_orchestrator(selector=AlwaysFailSelector())
        with pytest.raises(ConnectionError):
            orch._select_candidate(["a", "b"], retry_limit=1)

    def test_data_integrity_error_not_retried(self):
        orch = _make_orchestrator(selector=BadCandidateSelector())
        with pytest.raises(DataIntegrityError):
            orch._select_candidate(["a", "b"], retry_limit=5)


class TestRunSelectStep:
    def test_success_sets_selected_candidate(self):
        orch = _make_orchestrator()
        iteration = _make_iteration(candidates=["a", "b", "c"])
        ok = orch._run_select_step(iteration, retry_limit=0)
        assert ok is True
        assert iteration.selected_candidate == "a"

    def test_data_integrity_marks_failed(self):
        orch = _make_orchestrator(selector=BadCandidateSelector())
        iteration = _make_iteration(candidates=["a", "b", "c"])
        ok = orch._run_select_step(iteration, retry_limit=0)
        assert ok is False
        assert iteration.status == IterationStatus.FAILED
        assert "Data integrity error" in iteration.error

    def test_exception_marks_failed(self):
        orch = _make_orchestrator(selector=AlwaysFailSelector())
        iteration = _make_iteration(candidates=["a", "b", "c"])
        ok = orch._run_select_step(iteration, retry_limit=1)
        assert ok is False
        assert iteration.status == IterationStatus.FAILED
        assert "failed after retries" in iteration.error
