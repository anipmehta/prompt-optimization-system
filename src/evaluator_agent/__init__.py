"""Evaluator Agent — LLM-as-judge for prompt quality scoring."""

from evaluator_agent.config import DEFAULT_RUBRIC_TEMPLATE, EvaluatorConfig

__all__ = [
    "EvaluatorAgent",
    "EvaluatorConfig",
    "DEFAULT_RUBRIC_TEMPLATE",
]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    if name == "EvaluatorAgent":
        from evaluator_agent.agent import EvaluatorAgent

        return EvaluatorAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
