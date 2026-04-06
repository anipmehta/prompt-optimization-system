"""Serialization and deserialization of OptimizationRun state."""

import json
from typing import Any

from prompt_optimization_orchestrator.exceptions import DeserializationError
from prompt_optimization_orchestrator.models import (
    IterationResult,
    IterationStatus,
    OptimizationConfig,
    OptimizationRun,
    RunStatus,
)

_REQUIRED_RUN_FIELDS = {"run_id", "task_description", "config", "status", "iterations"}
_REQUIRED_CONFIG_FIELDS = {"num_candidates", "num_iterations"}
_REQUIRED_ITERATION_FIELDS = {"iteration_number", "status"}


def serialize_run(run: OptimizationRun) -> str:
    """Serialize an OptimizationRun to a JSON string."""
    return json.dumps(_run_to_dict(run))


def deserialize_run(json_str: str) -> OptimizationRun:
    """Deserialize a JSON string back to an OptimizationRun."""
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise DeserializationError(f"Malformed JSON: {e}") from e
    return _dict_to_run(data)


def _run_to_dict(run: OptimizationRun) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "task_description": run.task_description,
        "config": {
            "num_candidates": run.config.num_candidates,
            "num_iterations": run.config.num_iterations,
            "retry_limit": run.config.retry_limit,
            "evaluation_criteria": run.config.evaluation_criteria,
        },
        "status": run.status.value,
        "iterations": [_iteration_to_dict(it) for it in run.iterations],
    }


def _iteration_to_dict(it: IterationResult) -> dict[str, Any]:
    return {
        "iteration_number": it.iteration_number,
        "status": it.status.value,
        "candidates": it.candidates,
        "selected_candidate": it.selected_candidate,
        "evaluation_score": it.evaluation_score,
        "error": it.error,
    }


def _dict_to_run(data: dict[str, Any]) -> OptimizationRun:
    missing = _REQUIRED_RUN_FIELDS - set(data.keys())
    if missing:
        raise DeserializationError(f"Missing fields: {sorted(missing)}")
    config_data = data["config"]
    missing_config = _REQUIRED_CONFIG_FIELDS - set(config_data.keys())
    if missing_config:
        raise DeserializationError(f"Missing config fields: {sorted(missing_config)}")
    config = OptimizationConfig(
        num_candidates=config_data["num_candidates"],
        num_iterations=config_data["num_iterations"],
        retry_limit=config_data.get("retry_limit", 3),
        evaluation_criteria=config_data.get("evaluation_criteria", ""),
    )
    iterations = [_dict_to_iteration(it) for it in data["iterations"]]
    return OptimizationRun(
        run_id=data["run_id"],
        task_description=data["task_description"],
        config=config,
        status=RunStatus(data["status"]),
        iterations=iterations,
    )


def _dict_to_iteration(data: dict[str, Any]) -> IterationResult:
    missing = _REQUIRED_ITERATION_FIELDS - set(data.keys())
    if missing:
        raise DeserializationError(f"Missing iteration fields: {sorted(missing)}")
    return IterationResult(
        iteration_number=data["iteration_number"],
        status=IterationStatus(data["status"]),
        candidates=data.get("candidates", []),
        selected_candidate=data.get("selected_candidate"),
        evaluation_score=data.get("evaluation_score"),
        error=data.get("error"),
    )
