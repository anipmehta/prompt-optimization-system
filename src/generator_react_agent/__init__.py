"""Generator ReAct Agent — thin adapter over llm-toolbox's Agent class."""

from generator_react_agent.config import (
    DEFAULT_SYSTEM_PROMPT,
    AgentConfig,
)
from generator_react_agent.parser import parse_candidates

__all__ = [
    "GeneratorAgent",
    "AgentConfig",
    "DEFAULT_SYSTEM_PROMPT",
    "parse_candidates",
    "build_tool_registry",
]


def __getattr__(name: str):
    """Lazy imports for modules that depend on llm-toolbox."""
    if name == "GeneratorAgent":
        from generator_react_agent.agent import GeneratorAgent
        return GeneratorAgent
    if name == "build_tool_registry":
        from generator_react_agent.tools import build_tool_registry
        return build_tool_registry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
