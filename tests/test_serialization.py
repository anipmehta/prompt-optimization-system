"""Unit tests for serialization/deserialization of OptimizationRun."""

import pytest

from prompt_optimization_orchestrator.exceptions import DeserializationError
from prompt_optimization_orchestrator.models import (
    IterationResult,
    IterationStatus,
    OptimizationConfig,
    OptimizationRun,
    RunStatus,
)
from prompt_optimization_orchestrator.serialization import deserialize_run, serialize_run

TASK_DESCRIPTION = "summarize articles"
NUM_CANDIDATES = 3
NUM_ITERATIONS = 5


def _make_run(status=RunStatus.COMPLETE, iterations=None):
    config = OptimizationConfig(num_candidates=NUM_CANDIDATES, num_iterations=NUM_ITERATIONS)
    return OptimizationRun(
        run_id="test-run-id",
        task_description=TASK_DESCRIPTION,
        config=config,
        status=status,
        iterations=iterations or [],
    )


def _make_complete_iteration(num=0, score=0.9):
    return IterationResult(
        iteration_number=num,
        status=IterationStatus.COMPLETE,
        candidates=["c0", "c1", "c2"],
        selected_candidate="c0",
        evaluation_score=score,
    )


class TestSerializeRun:
    def test_round_trip_empty_run(self):
        run = _make_run(status=RunStatus.PENDING)
        result = deserialize_run(serialize_run(run))
        assert result.run_id == run.run_id
        assert result.task_description == run.task_description
        assert result.config == run.config
        assert result.status == run.status
        assert result.iterations == []

    def test_round_trip_with_iterations(self):
        iterations = [_make_complete_iteration(i) for i in range(NUM_ITERATIONS)]
        run = _make_run(iterations=iterations)
        result = deserialize_run(serialize_run(run))
        assert len(result.iterations) == NUM_ITERATIONS
        for orig, restored in zip(run.iterations, result.iterations):
            assert restored.iteration_number == orig.iteration_number
            assert restored.status == orig.status
            assert restored.candidates == orig.candidates
            assert restored.selected_candidate == orig.selected_candidate
            assert restored.evaluation_score == orig.evaluation_score

    def test_round_trip_failed_iteration(self):
        it = IterationResult(
            iteration_number=0,
            status=IterationStatus.FAILED,
            error="Generator failed",
        )
        run = _make_run(status=RunStatus.ABORTED, iterations=[it])
        result = deserialize_run(serialize_run(run))
        assert result.iterations[0].status == IterationStatus.FAILED
        assert result.iterations[0].error == "Generator failed"


class TestDeserializeErrors:
    def test_malformed_json(self):
        with pytest.raises(DeserializationError, match="Malformed JSON"):
            deserialize_run("{bad json")

    def test_missing_run_fields(self):
        with pytest.raises(DeserializationError, match="Missing fields"):
            deserialize_run('{"run_id": "x"}')

    def test_missing_config_fields(self):
        data = (
            '{"run_id":"x","task_description":"t","config":{},"status":"pending","iterations":[]}'
        )
        with pytest.raises(DeserializationError, match="Missing config fields"):
            deserialize_run(data)

    def test_missing_iteration_fields(self):
        data = (
            '{"run_id":"x","task_description":"t",'
            '"config":{"num_candidates":3,"num_iterations":5},'
            '"status":"pending","iterations":[{}]}'
        )
        with pytest.raises(DeserializationError, match="Missing iteration fields"):
            deserialize_run(data)
