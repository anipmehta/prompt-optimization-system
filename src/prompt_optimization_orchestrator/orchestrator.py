"""Core Orchestrator class for prompt optimization."""

import logging
import uuid

from prompt_optimization_orchestrator.exceptions import RunNotFoundError
from prompt_optimization_orchestrator.interfaces import (
    EvaluatorInterface,
    GeneratorInterface,
    SelectorInterface,
)
from prompt_optimization_orchestrator.models import (
    OptimizationConfig,
    OptimizationRun,
)
from prompt_optimization_orchestrator.validation import validate_config, validate_task_description


class Orchestrator:
    """Coordinates prompt optimization runs across Generator, Selector, and Evaluator."""

    def __init__(
        self,
        generator: GeneratorInterface,
        selector: SelectorInterface,
        evaluator: EvaluatorInterface,
        logger: logging.Logger | None = None,
    ) -> None:
        self._generator = generator
        self._selector = selector
        self._evaluator = evaluator
        self._logger = logger or logging.getLogger(__name__)
        self._runs: dict[str, OptimizationRun] = {}

    def start_run(self, task_description: str, config: OptimizationConfig) -> str:
        """Validate inputs, create an OptimizationRun, and return its unique run_id."""
        validate_task_description(task_description)
        validate_config(config)
        run_id = str(uuid.uuid4())
        self._runs[run_id] = OptimizationRun(
            run_id=run_id,
            task_description=task_description,
            config=config,
        )
        return run_id

    def get_run(self, run_id: str) -> OptimizationRun:
        """Retrieve an OptimizationRun by its run_id."""
        if run_id not in self._runs:
            raise RunNotFoundError(f"Run not found: {run_id}")
        return self._runs[run_id]
