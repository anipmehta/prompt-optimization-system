"""Exception hierarchy for the Prompt Optimization Orchestrator."""


class OrchestratorError(Exception):
    """Base exception for all orchestrator errors."""


class ValidationError(OrchestratorError):
    """Raised when input validation fails (e.g., empty task description, invalid config)."""


class DeserializationError(OrchestratorError):
    """Raised when JSON deserialization of an OptimizationRun fails."""


class RunNotFoundError(OrchestratorError):
    """Raised when a run ID is not found."""


class ComponentError(OrchestratorError):
    """Raised when an external component (Generator, Selector, Evaluator) fails."""


class DataIntegrityError(OrchestratorError):
    """Raised when data integrity checks fail (e.g., selected candidate not in candidate set)."""
