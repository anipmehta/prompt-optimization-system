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
    IterationResult,
    IterationStatus,
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

    def _generate_candidates(
        self, task_description: str, num_candidates: int, retry_limit: int
    ) -> list[str]:
        """Call the Generator with retry logic. Returns candidates or raises on total failure."""
        last_error: Exception | None = None
        for attempt in range(1 + retry_limit):
            try:
                candidates = self._generator.generate(task_description, num_candidates)
                if len(candidates) < num_candidates and len(candidates) > 0:
                    self._logger.warning(
                        "Generator returned %d candidates, expected %d",
                        len(candidates),
                        num_candidates,
                    )
                return candidates
            except Exception as e:
                last_error = e
                self._logger.warning(
                    "Generator failed (attempt %d/%d): %s",
                    attempt + 1,
                    1 + retry_limit,
                    e,
                )
        raise last_error  # type: ignore[misc]

    def _run_generate_step(
        self,
        iteration: IterationResult,
        task_description: str,
        num_candidates: int,
        retry_limit: int,
    ) -> bool:
        """Execute the generate step for an iteration. Returns True if successful."""
        try:
            candidates = self._generate_candidates(task_description, num_candidates, retry_limit)
            if not candidates:
                iteration.status = IterationStatus.FAILED
                iteration.error = "Generator returned zero candidates"
                return False
            iteration.candidates = candidates
            return True
        except Exception as e:
            iteration.status = IterationStatus.FAILED
            iteration.error = f"Generator failed after retries: {e}"
            return False
