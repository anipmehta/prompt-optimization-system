"""Core Orchestrator class for prompt optimization."""

import logging
import math
import uuid

from prompt_optimization_orchestrator.exceptions import DataIntegrityError, RunNotFoundError
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

    def _select_candidate(self, candidates: list[str], retry_limit: int) -> str:
        """Call the Selector with retry logic. Returns selected candidate or raises."""
        last_error: Exception | None = None
        for attempt in range(1 + retry_limit):
            try:
                selected = self._selector.select(candidates)
                if selected not in candidates:
                    raise DataIntegrityError(
                        f"Selector returned candidate not in original set: {selected!r}"
                    )
                return selected
            except DataIntegrityError:
                raise
            except Exception as e:
                last_error = e
                self._logger.warning(
                    "Selector failed (attempt %d/%d): %s",
                    attempt + 1,
                    1 + retry_limit,
                    e,
                )
        raise last_error  # type: ignore[misc]

    def _run_select_step(
        self,
        iteration: IterationResult,
        retry_limit: int,
    ) -> bool:
        """Execute the select step for an iteration. Returns True if successful."""
        try:
            selected = self._select_candidate(iteration.candidates, retry_limit)
            iteration.selected_candidate = selected
            return True
        except DataIntegrityError as e:
            iteration.status = IterationStatus.FAILED
            iteration.error = f"Data integrity error: {e}"
            return False
        except Exception as e:
            iteration.status = IterationStatus.FAILED
            iteration.error = f"Selector failed after retries: {e}"
            return False

    def _evaluate_candidate(self, candidate: str, task_description: str, retry_limit: int) -> float:
        """Call the Evaluator with retry logic. Returns a finite score or raises."""
        last_error: Exception | None = None
        for attempt in range(1 + retry_limit):
            try:
                score = self._evaluator.evaluate(candidate, task_description)
                if not isinstance(score, (int, float)) or not math.isfinite(score):
                    raise ValueError(f"Evaluator returned non-finite score: {score}")
                return float(score)
            except ValueError:
                raise
            except Exception as e:
                last_error = e
                self._logger.warning(
                    "Evaluator failed (attempt %d/%d): %s",
                    attempt + 1,
                    1 + retry_limit,
                    e,
                )
        raise last_error  # type: ignore[misc]

    def _run_evaluate_step(
        self,
        iteration: IterationResult,
        task_description: str,
        retry_limit: int,
    ) -> bool:
        """Execute the evaluate step for an iteration. Returns True if successful."""
        try:
            score = self._evaluate_candidate(
                iteration.selected_candidate,  # type: ignore[arg-type]
                task_description,
                retry_limit,
            )
            iteration.evaluation_score = score
            return True
        except ValueError as e:
            iteration.status = IterationStatus.FAILED
            iteration.error = f"Evaluation validation error: {e}"
            return False
        except Exception as e:
            iteration.status = IterationStatus.FAILED
            iteration.error = f"Evaluator failed after retries: {e}"
            return False

    def _run_reward_step(self, iteration: IterationResult) -> None:
        """Send evaluation score to Selector as reward. Marks iteration DEGRADED on failure."""
        try:
            self._selector.reward(iteration.evaluation_score)  # type: ignore[arg-type]
            iteration.status = IterationStatus.COMPLETE
        except Exception as e:
            self._logger.warning("Selector failed to accept reward: %s", e)
            iteration.status = IterationStatus.DEGRADED
