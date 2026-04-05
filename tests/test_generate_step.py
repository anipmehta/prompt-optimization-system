"""Unit tests for the generate step of the Orchestrator."""

import logging

import pytest

from prompt_optimization_orchestrator.models import (
    IterationResult,
    IterationStatus,
)
from prompt_optimization_orchestrator.orchestrator import Orchestrator


class FakeSelector:
    def select(self, candidates: list[str]) -> str:
        return candidates[0]

    def reward(self, score: float) -> None:
        pass


class FakeEvaluator:
    def evaluate(self, candidate: str, task_description: str) -> float:
        return 0.9


def _make_orchestrator(generator, logger=None):
    return Orchestrator(
        generator=generator,
        selector=FakeSelector(),
        evaluator=FakeEvaluator(),
        logger=logger,
    )


def _make_iteration():
    return IterationResult(iteration_number=0, status=IterationStatus.IN_PROGRESS)


class SuccessGenerator:
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


class TestGenerateCandidates:
    def test_returns_candidates_on_success(self):
        orch = _make_orchestrator(SuccessGenerator())
        result = orch._generate_candidates("task", 3, retry_limit=0)
        assert len(result) == 3

    def test_retries_on_failure_then_succeeds(self):
        gen = FailThenSucceedGenerator(fail_count=2)
        orch = _make_orchestrator(gen)
        result = orch._generate_candidates("task", 3, retry_limit=2)
        assert len(result) == 3

    def test_raises_after_exhausting_retries(self):
        orch = _make_orchestrator(AlwaysFailGenerator())
        with pytest.raises(ConnectionError):
            orch._generate_candidates("task", 3, retry_limit=2)

    def test_logs_warning_on_fewer_candidates(self, caplog):
        gen = SuccessGenerator(candidates=["only_one"])
        orch = _make_orchestrator(gen, logger=logging.getLogger("test"))
        with caplog.at_level(logging.WARNING, logger="test"):
            result = orch._generate_candidates("task", 3, retry_limit=0)
        assert len(result) == 1
        assert "expected 3" in caplog.text


class TestRunGenerateStep:
    def test_success_populates_candidates(self):
        orch = _make_orchestrator(SuccessGenerator())
        iteration = _make_iteration()
        ok = orch._run_generate_step(iteration, "task", 3, retry_limit=0)
        assert ok is True
        assert len(iteration.candidates) == 3

    def test_zero_candidates_marks_failed(self):
        orch = _make_orchestrator(EmptyGenerator())
        iteration = _make_iteration()
        ok = orch._run_generate_step(iteration, "task", 3, retry_limit=0)
        assert ok is False
        assert iteration.status == IterationStatus.FAILED
        assert "zero candidates" in iteration.error

    def test_exception_marks_failed(self):
        orch = _make_orchestrator(AlwaysFailGenerator())
        iteration = _make_iteration()
        ok = orch._run_generate_step(iteration, "task", 3, retry_limit=1)
        assert ok is False
        assert iteration.status == IterationStatus.FAILED
        assert "failed after retries" in iteration.error
