"""Protocol interfaces for external components."""

from typing import Protocol


class GeneratorInterface(Protocol):
    """Interface for the prompt candidate generator."""

    def generate(self, task_description: str, num_candidates: int) -> list[str]:
        """Generate prompt candidates for a task description."""
        ...


class SelectorInterface(Protocol):
    """Interface for the RL-based candidate selector."""

    def select(self, candidates: list[str]) -> str:
        """Select the best candidate from a list."""
        ...

    def reward(self, score: float) -> None:
        """Send evaluation score as reward signal."""
        ...


class EvaluatorInterface(Protocol):
    """Interface for the prompt candidate evaluator."""

    def evaluate(self, candidate: str, task_description: str) -> float:
        """Evaluate a prompt candidate and return a numeric score."""
        ...
