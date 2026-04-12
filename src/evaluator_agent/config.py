"""Evaluator agent configuration."""

from dataclasses import dataclass

DEFAULT_RUBRIC_TEMPLATE = """\
You are an expert prompt evaluator. Rate the following prompt candidate \
on a scale of 1 to 10 based on these criteria:

- Clarity: Is the prompt clear and unambiguous?
- Specificity: Does it provide enough detail for the task?
- Effectiveness: Would this prompt produce good results from an LLM?
- Completeness: Does it cover all aspects of the task?

Task description: {task_description}

Prompt candidate: {candidate}

Return ONLY a single number between 1 and 10. Do not include any \
explanation or other text.
"""


@dataclass(frozen=True)
class EvaluatorConfig:
    """Configuration for the EvaluatorAgent."""

    rubric_template: str = DEFAULT_RUBRIC_TEMPLATE
    min_score: float = 1.0
    max_score: float = 10.0

    def __post_init__(self) -> None:
        if not self.rubric_template.strip():
            raise ValueError("rubric_template must not be empty.")
        if self.min_score >= self.max_score:
            raise ValueError(
                f"min_score ({self.min_score}) must be less than max_score ({self.max_score})."
            )
