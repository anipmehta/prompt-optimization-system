"""Input validation for the Prompt Optimization Orchestrator."""

from prompt_optimization_orchestrator.exceptions import ValidationError
from prompt_optimization_orchestrator.models import OptimizationConfig


def validate_task_description(task_description: str) -> None:
    """Validate that task_description is a non-empty string after stripping whitespace."""
    if not task_description.strip():
        raise ValidationError("task_description is required and cannot be empty")


def validate_config(config: OptimizationConfig) -> None:
    """Validate OptimizationConfig fields. Raises ValidationError listing all invalid fields."""
    errors: list[str] = []
    if not isinstance(config.num_candidates, int) or config.num_candidates <= 0:
        errors.append("num_candidates must be a positive integer")
    if not isinstance(config.num_iterations, int) or config.num_iterations <= 0:
        errors.append("num_iterations must be a positive integer")
    if not isinstance(config.retry_limit, int) or config.retry_limit < 0:
        errors.append("retry_limit must be a non-negative integer")
    if errors:
        raise ValidationError("Invalid config: " + "; ".join(errors))
