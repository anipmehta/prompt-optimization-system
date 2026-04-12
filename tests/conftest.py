"""Shared test fixtures for the prompt optimization orchestrator."""

import pytest

from prompt_optimization_orchestrator.models import (
    IterationResult,
    IterationStatus,
    OptimizationConfig,
)
from prompt_optimization_orchestrator.orchestrator import Orchestrator

# --- Test constants ---

TASK_DESCRIPTION = "summarize articles"
NUM_CANDIDATES = 3
NUM_ITERATIONS = 5
DEFAULT_SCORE = 0.9

# --- Mock components ---


class FakeGenerator:
    """Generator that returns predictable candidates."""

    def __init__(self, candidates: list[str] | None = None) -> None:
        self._candidates = candidates

    def generate(self, task_description: str, num_candidates: int) -> list[str]:
        if self._candidates is not None:
            return self._candidates
        return [f"candidate_{i}" for i in range(num_candidates)]


class FakeSelector:
    """Selector that always picks the first candidate."""

    def select(self, candidates: list[str]) -> str:
        return candidates[0]

    def reward(self, score: float) -> None:
        pass


class FakeEvaluator:
    """Evaluator that returns a fixed score."""

    def __init__(self, score: float = DEFAULT_SCORE) -> None:
        self._score = score

    def evaluate(self, candidate: str, task_description: str) -> float:
        return self._score


# --- Fixtures ---


@pytest.fixture
def orchestrator() -> Orchestrator:
    """Pre-built orchestrator with fake components."""
    return Orchestrator(
        generator=FakeGenerator(),
        selector=FakeSelector(),
        evaluator=FakeEvaluator(),
    )


@pytest.fixture
def valid_config() -> OptimizationConfig:
    """Default valid optimization config."""
    return OptimizationConfig(
        num_candidates=NUM_CANDIDATES,
        num_iterations=NUM_ITERATIONS,
    )


@pytest.fixture
def sample_iteration() -> IterationResult:
    """A sample in-progress iteration."""
    return IterationResult(
        iteration_number=0,
        status=IterationStatus.IN_PROGRESS,
        candidates=["prompt_a", "prompt_b", "prompt_c"],
    )
