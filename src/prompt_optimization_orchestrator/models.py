"""Data models and enums for the Prompt Optimization Orchestrator."""

from dataclasses import dataclass, field
from enum import Enum


class IterationStatus(Enum):
    """Status of a single iteration within an optimization run."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    DEGRADED = "degraded"


class RunStatus(Enum):
    """Status of an optimization run."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    ABORTED = "aborted"


@dataclass
class OptimizationConfig:
    """Configuration for an optimization run."""

    num_candidates: int
    num_iterations: int
    retry_limit: int = 3
    evaluation_criteria: str = ""


@dataclass
class IterationResult:
    """Result of a single iteration."""

    iteration_number: int
    status: IterationStatus
    candidates: list[str] = field(default_factory=list)
    selected_candidate: str | None = None
    evaluation_score: float | None = None
    error: str | None = None


@dataclass
class OptimizationRun:
    """State of a full optimization run."""

    run_id: str
    task_description: str
    config: OptimizationConfig
    status: RunStatus = RunStatus.PENDING
    iterations: list[IterationResult] = field(default_factory=list)


@dataclass
class OptimizationResult:
    """Final result returned after a run completes."""

    run_id: str
    status: RunStatus
    best_candidate: str | None
    best_score: float | None
    iterations: list[IterationResult]
