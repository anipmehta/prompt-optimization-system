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

# --- Test constants ---

TASK_DESCRIPTION = "summarize articles"
TASK_DESCRIPTION_ALT = "translate documents"
NUM_CANDIDATES = 3
NUM_ITERATIONS = 5
RETRY_LIMIT = 2
DEFAULT_SCORE = 0.9
RETRY_SCORE = 0.85
SAMPLE_CANDIDATES = ["prompt_a", "prompt_b", "prompt_c"]

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
        return DEFAULT_SCORE


class NaNEvaluator:
    def evaluate(self, candidate: str, task_description: str) -> float:
        return float("nan")


class InfEvaluator:
    def evaluate(self, candidate: str, task_description: str) -> float:
        return float("inf")


class FailThenSucceedEvaluator:
    def __init__(self, fail_count: int):
        self._fail_count = fail_count
        self._calls = 0

    def evaluate(self, candidate: str, task_description: str) -> float:
        self._calls += 1
        if self._calls <= self._fail_count:
            raise ConnectionError("Evaluator unavailable")
        return RETRY_SCORE


class AlwaysFailEvaluator:
    def evaluate(self, candidate: str, task_description: str) -> float:
        raise ConnectionError("Evaluator unavailable")


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
    return OptimizationConfig(num_candidates=NUM_CANDIDATES, num_iterations=NUM_ITERATIONS)


# --- start_run / get_run ---


class TestStartRun:
    def test_returns_unique_run_ids(self, orchestrator, valid_config):
        id1 = orchestrator.start_run(TASK_DESCRIPTION, valid_config)
        id2 = orchestrator.start_run(TASK_DESCRIPTION_ALT, valid_config)
        assert id1 != id2

    def test_creates_run_with_pending_status(self, orchestrator, valid_config):
        run_id = orchestrator.start_run(TASK_DESCRIPTION, valid_config)
        run = orchestrator.get_run(run_id)
        assert run.status == RunStatus.PENDING
        assert run.task_description == TASK_DESCRIPTION
        assert run.config == valid_config
        assert run.iterations == []

    def test_empty_task_description_raises(self, orchestrator, valid_config):
        with pytest.raises(ValidationError, match="task_description is required"):
            orchestrator.start_run("", valid_config)

    def test_invalid_config_raises(self, orchestrator):
        bad_config = OptimizationConfig(num_candidates=0, num_iterations=NUM_ITERATIONS)
        with pytest.raises(ValidationError, match="num_candidates"):
            orchestrator.start_run(TASK_DESCRIPTION, bad_config)


class TestGetRun:
    def test_returns_existing_run(self, orchestrator, valid_config):
        run_id = orchestrator.start_run(TASK_DESCRIPTION, valid_config)
        run = orchestrator.get_run(run_id)
        assert run.run_id == run_id

    def test_unknown_id_raises(self, orchestrator):
        with pytest.raises(RunNotFoundError, match="Run not found"):
            orchestrator.get_run("nonexistent-id")


# --- Generate step ---


class TestGenerateCandidates:
    def test_returns_candidates_on_success(self):
        orch = _make_orchestrator()
        result = orch._generate_candidates(TASK_DESCRIPTION, NUM_CANDIDATES, retry_limit=0)
        assert len(result) == NUM_CANDIDATES

    def test_retries_on_failure_then_succeeds(self):
        gen = FailThenSucceedGenerator(fail_count=RETRY_LIMIT)
        orch = _make_orchestrator(generator=gen)
        result = orch._generate_candidates(
            TASK_DESCRIPTION, NUM_CANDIDATES, retry_limit=RETRY_LIMIT
        )
        assert len(result) == NUM_CANDIDATES

    def test_raises_after_exhausting_retries(self):
        orch = _make_orchestrator(generator=AlwaysFailGenerator())
        with pytest.raises(ConnectionError):
            orch._generate_candidates(TASK_DESCRIPTION, NUM_CANDIDATES, retry_limit=RETRY_LIMIT)

    def test_logs_warning_on_fewer_candidates(self, caplog):
        gen = FakeGenerator(candidates=["only_one"])
        orch = _make_orchestrator(generator=gen, logger=logging.getLogger("test"))
        with caplog.at_level(logging.WARNING, logger="test"):
            result = orch._generate_candidates(TASK_DESCRIPTION, NUM_CANDIDATES, retry_limit=0)
        assert len(result) == 1
        assert f"expected {NUM_CANDIDATES}" in caplog.text


class TestRunGenerateStep:
    def test_success_populates_candidates(self):
        orch = _make_orchestrator()
        iteration = _make_iteration()
        ok = orch._run_generate_step(iteration, TASK_DESCRIPTION, NUM_CANDIDATES, retry_limit=0)
        assert ok is True
        assert len(iteration.candidates) == NUM_CANDIDATES

    def test_zero_candidates_marks_failed(self):
        orch = _make_orchestrator(generator=EmptyGenerator())
        iteration = _make_iteration()
        ok = orch._run_generate_step(iteration, TASK_DESCRIPTION, NUM_CANDIDATES, retry_limit=0)
        assert ok is False
        assert iteration.status == IterationStatus.FAILED
        assert "zero candidates" in iteration.error

    def test_exception_marks_failed(self):
        orch = _make_orchestrator(generator=AlwaysFailGenerator())
        iteration = _make_iteration()
        ok = orch._run_generate_step(iteration, TASK_DESCRIPTION, NUM_CANDIDATES, retry_limit=1)
        assert ok is False
        assert iteration.status == IterationStatus.FAILED
        assert "failed after retries" in iteration.error


# --- Select step ---


class TestSelectCandidate:
    def test_returns_valid_candidate(self):
        orch = _make_orchestrator()
        result = orch._select_candidate(SAMPLE_CANDIDATES, retry_limit=0)
        assert result == SAMPLE_CANDIDATES[0]

    def test_raises_data_integrity_on_bad_candidate(self):
        orch = _make_orchestrator(selector=BadCandidateSelector())
        with pytest.raises(DataIntegrityError, match="not in original set"):
            orch._select_candidate(SAMPLE_CANDIDATES, retry_limit=0)

    def test_retries_on_failure_then_succeeds(self):
        sel = FailThenSucceedSelector(fail_count=RETRY_LIMIT)
        orch = _make_orchestrator(selector=sel)
        result = orch._select_candidate(SAMPLE_CANDIDATES, retry_limit=RETRY_LIMIT)
        assert result == SAMPLE_CANDIDATES[0]

    def test_raises_after_exhausting_retries(self):
        orch = _make_orchestrator(selector=AlwaysFailSelector())
        with pytest.raises(ConnectionError):
            orch._select_candidate(SAMPLE_CANDIDATES, retry_limit=1)

    def test_data_integrity_error_not_retried(self):
        orch = _make_orchestrator(selector=BadCandidateSelector())
        with pytest.raises(DataIntegrityError):
            orch._select_candidate(SAMPLE_CANDIDATES, retry_limit=5)


class TestRunSelectStep:
    def test_success_sets_selected_candidate(self):
        orch = _make_orchestrator()
        iteration = _make_iteration(candidates=SAMPLE_CANDIDATES)
        ok = orch._run_select_step(iteration, retry_limit=0)
        assert ok is True
        assert iteration.selected_candidate == SAMPLE_CANDIDATES[0]

    def test_data_integrity_marks_failed(self):
        orch = _make_orchestrator(selector=BadCandidateSelector())
        iteration = _make_iteration(candidates=SAMPLE_CANDIDATES)
        ok = orch._run_select_step(iteration, retry_limit=0)
        assert ok is False
        assert iteration.status == IterationStatus.FAILED
        assert "Data integrity error" in iteration.error

    def test_exception_marks_failed(self):
        orch = _make_orchestrator(selector=AlwaysFailSelector())
        iteration = _make_iteration(candidates=SAMPLE_CANDIDATES)
        ok = orch._run_select_step(iteration, retry_limit=1)
        assert ok is False
        assert iteration.status == IterationStatus.FAILED
        assert "failed after retries" in iteration.error


# --- Evaluate step ---


class TestEvaluateCandidate:
    def test_returns_score_on_success(self):
        orch = _make_orchestrator()
        score = orch._evaluate_candidate(SAMPLE_CANDIDATES[0], TASK_DESCRIPTION, retry_limit=0)
        assert score == DEFAULT_SCORE

    def test_raises_on_nan_score(self):
        orch = _make_orchestrator(evaluator=NaNEvaluator())
        with pytest.raises(ValueError, match="non-finite score"):
            orch._evaluate_candidate(SAMPLE_CANDIDATES[0], TASK_DESCRIPTION, retry_limit=0)

    def test_raises_on_inf_score(self):
        orch = _make_orchestrator(evaluator=InfEvaluator())
        with pytest.raises(ValueError, match="non-finite score"):
            orch._evaluate_candidate(SAMPLE_CANDIDATES[0], TASK_DESCRIPTION, retry_limit=0)

    def test_retries_on_failure_then_succeeds(self):
        ev = FailThenSucceedEvaluator(fail_count=RETRY_LIMIT)
        orch = _make_orchestrator(evaluator=ev)
        score = orch._evaluate_candidate(
            SAMPLE_CANDIDATES[0], TASK_DESCRIPTION, retry_limit=RETRY_LIMIT
        )
        assert score == RETRY_SCORE

    def test_raises_after_exhausting_retries(self):
        orch = _make_orchestrator(evaluator=AlwaysFailEvaluator())
        with pytest.raises(ConnectionError):
            orch._evaluate_candidate(SAMPLE_CANDIDATES[0], TASK_DESCRIPTION, retry_limit=1)

    def test_nan_not_retried(self):
        orch = _make_orchestrator(evaluator=NaNEvaluator())
        with pytest.raises(ValueError):
            orch._evaluate_candidate(SAMPLE_CANDIDATES[0], TASK_DESCRIPTION, retry_limit=5)


class TestRunEvaluateStep:
    def test_success_sets_score(self):
        orch = _make_orchestrator()
        iteration = _make_iteration(candidates=SAMPLE_CANDIDATES)
        iteration.selected_candidate = SAMPLE_CANDIDATES[0]
        ok = orch._run_evaluate_step(iteration, TASK_DESCRIPTION, retry_limit=0)
        assert ok is True
        assert iteration.evaluation_score == DEFAULT_SCORE

    def test_nan_marks_failed(self):
        orch = _make_orchestrator(evaluator=NaNEvaluator())
        iteration = _make_iteration(candidates=SAMPLE_CANDIDATES)
        iteration.selected_candidate = SAMPLE_CANDIDATES[0]
        ok = orch._run_evaluate_step(iteration, TASK_DESCRIPTION, retry_limit=0)
        assert ok is False
        assert iteration.status == IterationStatus.FAILED
        assert "validation error" in iteration.error

    def test_exception_marks_failed(self):
        orch = _make_orchestrator(evaluator=AlwaysFailEvaluator())
        iteration = _make_iteration(candidates=SAMPLE_CANDIDATES)
        iteration.selected_candidate = SAMPLE_CANDIDATES[0]
        ok = orch._run_evaluate_step(iteration, TASK_DESCRIPTION, retry_limit=1)
        assert ok is False
        assert iteration.status == IterationStatus.FAILED
        assert "failed after retries" in iteration.error


# --- Reward step ---


class FailRewardSelector:
    def select(self, candidates: list[str]) -> str:
        return candidates[0]

    def reward(self, score: float) -> None:
        raise ConnectionError("Selector reward failed")


class TestRunRewardStep:
    def test_success_marks_complete(self):
        orch = _make_orchestrator()
        iteration = _make_iteration(candidates=SAMPLE_CANDIDATES)
        iteration.selected_candidate = SAMPLE_CANDIDATES[0]
        iteration.evaluation_score = DEFAULT_SCORE
        orch._run_reward_step(iteration)
        assert iteration.status == IterationStatus.COMPLETE

    def test_failure_marks_degraded(self):
        orch = _make_orchestrator(selector=FailRewardSelector())
        iteration = _make_iteration(candidates=SAMPLE_CANDIDATES)
        iteration.selected_candidate = SAMPLE_CANDIDATES[0]
        iteration.evaluation_score = DEFAULT_SCORE
        orch._run_reward_step(iteration)
        assert iteration.status == IterationStatus.DEGRADED

    def test_failure_logs_warning(self, caplog):
        orch = _make_orchestrator(selector=FailRewardSelector(), logger=logging.getLogger("test"))
        iteration = _make_iteration(candidates=SAMPLE_CANDIDATES)
        iteration.selected_candidate = SAMPLE_CANDIDATES[0]
        iteration.evaluation_score = DEFAULT_SCORE
        with caplog.at_level(logging.WARNING, logger="test"):
            orch._run_reward_step(iteration)
        assert "failed to accept reward" in caplog.text


# --- execute_run ---

ABORT_ITERATIONS = 3  # with 3 iterations, 2 failures triggers abort (>50%)


class TestExecuteRun:
    def test_happy_path_completes_all_iterations(self, orchestrator, valid_config):
        run_id = orchestrator.start_run(TASK_DESCRIPTION, valid_config)
        result = orchestrator.execute_run(run_id)
        assert result.status == RunStatus.COMPLETE
        assert len(result.iterations) == NUM_ITERATIONS
        assert result.best_candidate is not None
        assert result.best_score == DEFAULT_SCORE

    def test_all_iterations_have_complete_or_degraded_status(self, orchestrator, valid_config):
        run_id = orchestrator.start_run(TASK_DESCRIPTION, valid_config)
        result = orchestrator.execute_run(run_id)
        for it in result.iterations:
            assert it.status in (IterationStatus.COMPLETE, IterationStatus.DEGRADED)

    def test_aborts_on_majority_failure(self):
        orch = _make_orchestrator(generator=AlwaysFailGenerator())
        config = OptimizationConfig(num_candidates=NUM_CANDIDATES, num_iterations=ABORT_ITERATIONS)
        run_id = orch.start_run(TASK_DESCRIPTION, config)
        result = orch.execute_run(run_id)
        assert result.status == RunStatus.ABORTED
        assert len(result.iterations) < ABORT_ITERATIONS

    def test_best_candidate_has_highest_score(self):
        """When all scores are equal, latest iteration wins."""
        orch = _make_orchestrator()
        config = OptimizationConfig(num_candidates=NUM_CANDIDATES, num_iterations=NUM_ITERATIONS)
        run_id = orch.start_run(TASK_DESCRIPTION, config)
        result = orch.execute_run(run_id)
        assert result.best_score == DEFAULT_SCORE
        # Latest iteration should win the tie
        last_complete = [
            it
            for it in result.iterations
            if it.status in (IterationStatus.COMPLETE, IterationStatus.DEGRADED)
        ][-1]
        assert result.best_candidate == last_complete.selected_candidate

    def test_no_successful_iterations_returns_none(self):
        orch = _make_orchestrator(generator=EmptyGenerator())
        config = OptimizationConfig(num_candidates=NUM_CANDIDATES, num_iterations=ABORT_ITERATIONS)
        run_id = orch.start_run(TASK_DESCRIPTION, config)
        result = orch.execute_run(run_id)
        assert result.best_candidate is None
        assert result.best_score is None

    def test_degraded_iteration_still_counts_for_best(self):
        orch = _make_orchestrator(selector=FailRewardSelector())
        config = OptimizationConfig(num_candidates=NUM_CANDIDATES, num_iterations=NUM_ITERATIONS)
        run_id = orch.start_run(TASK_DESCRIPTION, config)
        result = orch.execute_run(run_id)
        assert result.best_candidate is not None
        assert result.best_score == DEFAULT_SCORE

    def test_aborts_on_select_failures(self):
        orch = _make_orchestrator(selector=AlwaysFailSelector())
        config = OptimizationConfig(
            num_candidates=NUM_CANDIDATES,
            num_iterations=ABORT_ITERATIONS,
            retry_limit=0,
        )
        run_id = orch.start_run(TASK_DESCRIPTION, config)
        result = orch.execute_run(run_id)
        assert result.status == RunStatus.ABORTED

    def test_aborts_on_evaluate_failures(self):
        orch = _make_orchestrator(evaluator=AlwaysFailEvaluator())
        config = OptimizationConfig(
            num_candidates=NUM_CANDIDATES,
            num_iterations=ABORT_ITERATIONS,
            retry_limit=0,
        )
        run_id = orch.start_run(TASK_DESCRIPTION, config)
        result = orch.execute_run(run_id)
        assert result.status == RunStatus.ABORTED

    def test_partial_failures_still_completes(self):
        """One failure after successful iterations should not abort."""

        class FailLastGenerator:
            def __init__(self, total: int):
                self._total = total
                self._calls = 0

            def generate(self, task_description: str, num_candidates: int) -> list[str]:
                self._calls += 1
                if self._calls == self._total:
                    return []
                return [f"c{i}" for i in range(num_candidates)]

        orch = _make_orchestrator(generator=FailLastGenerator(total=NUM_ITERATIONS))
        config = OptimizationConfig(
            num_candidates=NUM_CANDIDATES,
            num_iterations=NUM_ITERATIONS,
        )
        run_id = orch.start_run(TASK_DESCRIPTION, config)
        result = orch.execute_run(run_id)
        assert result.status == RunStatus.COMPLETE
        failed = sum(1 for it in result.iterations if it.status == IterationStatus.FAILED)
        assert failed == 1

    def test_select_failure_continues_when_not_majority(self):
        """Select fails on last iteration but doesn't trigger abort."""

        class FailLastSelector:
            def __init__(self, total: int):
                self._total = total
                self._calls = 0

            def select(self, candidates: list[str]) -> str:
                self._calls += 1
                if self._calls == self._total:
                    raise ConnectionError("Selector failed")
                return candidates[0]

            def reward(self, score: float) -> None:
                pass

        orch = _make_orchestrator(selector=FailLastSelector(total=NUM_ITERATIONS))
        config = OptimizationConfig(
            num_candidates=NUM_CANDIDATES,
            num_iterations=NUM_ITERATIONS,
            retry_limit=0,
        )
        run_id = orch.start_run(TASK_DESCRIPTION, config)
        result = orch.execute_run(run_id)
        assert result.status == RunStatus.COMPLETE
        failed = sum(1 for it in result.iterations if it.status == IterationStatus.FAILED)
        assert failed == 1

    def test_evaluate_failure_continues_when_not_majority(self):
        """Evaluate fails on last iteration but doesn't trigger abort."""

        class FailLastEvaluator:
            def __init__(self, total: int):
                self._total = total
                self._calls = 0

            def evaluate(self, candidate: str, task_description: str) -> float:
                self._calls += 1
                if self._calls == self._total:
                    raise ConnectionError("Evaluator failed")
                return DEFAULT_SCORE

        orch = _make_orchestrator(evaluator=FailLastEvaluator(total=NUM_ITERATIONS))
        config = OptimizationConfig(
            num_candidates=NUM_CANDIDATES,
            num_iterations=NUM_ITERATIONS,
            retry_limit=0,
        )
        run_id = orch.start_run(TASK_DESCRIPTION, config)
        result = orch.execute_run(run_id)
        assert result.status == RunStatus.COMPLETE
        failed = sum(1 for it in result.iterations if it.status == IterationStatus.FAILED)
        assert failed == 1

    def test_abort_on_last_iteration_stays_aborted(self):
        """Abort on final iteration keeps ABORTED status."""

        class FailAfterFirstGenerator:
            def __init__(self):
                self._calls = 0

            def generate(self, task_description: str, num_candidates: int) -> list[str]:
                self._calls += 1
                if self._calls > 1:
                    return []
                return [f"c{i}" for i in range(num_candidates)]

        orch = _make_orchestrator(generator=FailAfterFirstGenerator())
        config = OptimizationConfig(
            num_candidates=NUM_CANDIDATES,
            num_iterations=ABORT_ITERATIONS,
            retry_limit=0,
        )
        run_id = orch.start_run(TASK_DESCRIPTION, config)
        result = orch.execute_run(run_id)
        assert result.status == RunStatus.ABORTED


# --- Logging ---


class TestLogging:
    def test_start_run_logs_info(self, valid_config, caplog):
        orch = _make_orchestrator(logger=logging.getLogger("test"))
        with caplog.at_level(logging.INFO, logger="test"):
            run_id = orch.start_run(TASK_DESCRIPTION, valid_config)
        assert run_id in caplog.text
        assert TASK_DESCRIPTION in caplog.text

    def test_execute_run_logs_iteration_start(self, valid_config, caplog):
        orch = _make_orchestrator(logger=logging.getLogger("test"))
        run_id = orch.start_run(TASK_DESCRIPTION, valid_config)
        with caplog.at_level(logging.INFO, logger="test"):
            orch.execute_run(run_id)
        assert "Iteration 0 started" in caplog.text

    def test_execute_run_logs_completion(self, valid_config, caplog):
        orch = _make_orchestrator(logger=logging.getLogger("test"))
        run_id = orch.start_run(TASK_DESCRIPTION, valid_config)
        with caplog.at_level(logging.INFO, logger="test"):
            orch.execute_run(run_id)
        assert "Run complete" in caplog.text

    def test_abort_logs_warning(self, caplog):
        orch = _make_orchestrator(generator=AlwaysFailGenerator(), logger=logging.getLogger("test"))
        config = OptimizationConfig(num_candidates=NUM_CANDIDATES, num_iterations=ABORT_ITERATIONS)
        run_id = orch.start_run(TASK_DESCRIPTION, config)
        with caplog.at_level(logging.WARNING, logger="test"):
            orch.execute_run(run_id)
        assert "Run aborted" in caplog.text
