"""Agent configuration."""

from dataclasses import dataclass

KNOWN_TOOL_NAMES: frozenset[str] = frozenset({
    "analyze_task",
    "retrieve_templates",
    "search_examples",
    "refine_candidate",
})

DEFAULT_SYSTEM_PROMPT = """\
You are a prompt engineering expert. Your task is to generate exactly \
{num_candidates} diverse prompt candidates for the given task.

Use the available tools to analyze the task, find relevant templates \
and examples, and refine your candidates.

Requirements:
- Each candidate must be a complete, self-contained prompt
- Candidates must vary across: instruction style, detail level, \
use of examples, output format
- Use tools to gather context before generating candidates

Format your final answer as a numbered list:
1. [first candidate]
2. [second candidate]
...
"""


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for the GeneratorAgent."""

    max_iterations: int = 5
    enabled_tools: frozenset[str] = KNOWN_TOOL_NAMES
    system_prompt_template: str = DEFAULT_SYSTEM_PROMPT

    def __post_init__(self) -> None:
        if self.max_iterations < 1:
            raise ValueError(
                f"max_iterations must be >= 1, got {self.max_iterations}"
            )
        unknown = self.enabled_tools - KNOWN_TOOL_NAMES
        if unknown:
            raise ValueError(
                f"Unknown tool names: {sorted(unknown)}. "
                f"Known tools: {sorted(KNOWN_TOOL_NAMES)}"
            )
        if not self.system_prompt_template.strip():
            raise ValueError("system_prompt_template must not be empty")
