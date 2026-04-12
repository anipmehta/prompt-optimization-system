# Requirements Document

## Introduction

This document specifies the requirements for the Evaluator Agent — a thin adapter that implements the Orchestrator's `EvaluatorInterface` protocol by delegating to the `llm-toolbox` library's `LLMClient` for LLM-as-judge scoring. The Evaluator Agent receives a prompt candidate and the original task description, uses a configurable scoring rubric to ask an LLM to judge the candidate's quality, parses the LLM's response to extract a numeric score, and returns a finite float.

The `llm-toolbox` library is installed as a local editable dependency from a sibling repository. Unlike the Generator Agent (which uses the full ReAct `Agent` class), the Evaluator Agent needs only a single LLM call per evaluation, so it uses `LLMClient` directly.

## Glossary

- **Evaluator_Agent**: The adapter class that implements the `EvaluatorInterface` protocol and delegates scoring to an LLM via `LLMClient`.
- **EvaluatorInterface**: The Protocol defined by the Orchestrator: `evaluate(candidate: str, task_description: str) -> float`.
- **LLMClient**: The unified async LLM client from `llm-toolbox` supporting OpenAI/Anthropic/Groq with retry logic and exponential backoff.
- **Scoring_Rubric**: A system prompt template that instructs the LLM to evaluate a prompt candidate against quality criteria and return a numeric score.
- **Evaluator_Config**: Configuration dataclass for the Evaluator_Agent, including the scoring rubric template and score range bounds.
- **Task_Description**: A natural-language description of the task for which prompts are being optimized.
- **Prompt_Candidate**: A single generated prompt text that is a candidate solution for a given Task_Description.
- **Evaluation_Score**: A finite float returned by the Evaluator_Agent representing the quality of a Prompt_Candidate.

## Requirements

### Requirement 1: Implement the EvaluatorInterface Protocol [P0]

**User Story:** As the Orchestrator, I want the Evaluator_Agent to conform to the EvaluatorInterface protocol, so that it can be injected as the evaluator component in optimization runs.

#### Acceptance Criteria

1. THE Evaluator_Agent SHALL implement an `evaluate` method that accepts a Prompt_Candidate (str) and a Task_Description (str) and returns an Evaluation_Score (float).
2. THE Evaluator_Agent SHALL satisfy the `EvaluatorInterface` Protocol so that the Orchestrator can accept the Evaluator_Agent via dependency injection.
3. IF the Prompt_Candidate is empty or contains only whitespace, THEN THE Evaluator_Agent SHALL raise a ValueError with a descriptive message.
4. IF the Task_Description is empty or contains only whitespace, THEN THE Evaluator_Agent SHALL raise a ValueError with a descriptive message.

### Requirement 2: Accept LLMClient via Dependency Injection [P0]

**User Story:** As a developer, I want the Evaluator_Agent to accept an LLMClient at construction time, so that the caller controls LLM provider configuration and the agent remains testable.

#### Acceptance Criteria

1. THE Evaluator_Agent SHALL accept an LLMClient instance via dependency injection at construction time.
2. THE Evaluator_Agent SHALL NOT instantiate its own LLMClient internally.
3. THE Evaluator_Agent SHALL use the injected LLMClient for all LLM calls during evaluation.

### Requirement 3: Use Configurable Scoring Rubric [P0]

**User Story:** As a prompt engineer, I want to configure the scoring rubric used for evaluation, so that I can tailor the evaluation criteria to different task types.

#### Acceptance Criteria

1. THE Evaluator_Agent SHALL accept an Evaluator_Config at construction time.
2. THE Evaluator_Config SHALL specify a Scoring_Rubric template (str) that instructs the LLM how to evaluate a Prompt_Candidate.
3. THE Scoring_Rubric template SHALL support `{candidate}` and `{task_description}` placeholders that the Evaluator_Agent fills before sending to the LLM.
4. THE Evaluator_Config SHALL specify a minimum score (float) and a maximum score (float) defining the valid score range.
5. THE Evaluator_Config SHALL have sensible defaults so that the Evaluator_Agent can be constructed with only an LLMClient.
6. IF the minimum score is greater than or equal to the maximum score, THEN THE Evaluator_Config SHALL raise a ValueError at construction time.
7. IF the Scoring_Rubric template is empty or contains only whitespace, THEN THE Evaluator_Config SHALL raise a ValueError at construction time.

### Requirement 4: Send Evaluation Request to LLM [P0]

**User Story:** As the Orchestrator, I want the Evaluator_Agent to send the prompt candidate and task description to an LLM for scoring, so that evaluation is performed by an LLM-as-judge.

#### Acceptance Criteria

1. WHEN `evaluate` is called, THE Evaluator_Agent SHALL format the Scoring_Rubric template with the provided Prompt_Candidate and Task_Description.
2. WHEN `evaluate` is called, THE Evaluator_Agent SHALL send the formatted rubric to the LLMClient as a single completion request.
3. THE Evaluator_Agent SHALL use the Scoring_Rubric as the system message and a user message containing the candidate and task description for the LLM call.

### Requirement 5: Parse Numeric Score from LLM Response [P0]

**User Story:** As the Orchestrator, I want the Evaluator_Agent to extract a numeric score from the LLM's response, so that the score can be used as a reward signal for the RL Selector.

#### Acceptance Criteria

1. WHEN the LLM returns a response, THE Evaluator_Agent SHALL parse the response text to extract a numeric score.
2. THE Evaluator_Agent SHALL support extracting a score from responses where the number appears on its own line, within a JSON object, or inline with surrounding text.
3. IF the LLM response contains no parseable numeric value, THEN THE Evaluator_Agent SHALL raise a ValueError with a descriptive message including the raw response text.
4. IF the parsed score falls outside the configured minimum and maximum score range, THEN THE Evaluator_Agent SHALL clamp the score to the nearest bound.

### Requirement 6: Return a Finite Float Score [P0]

**User Story:** As the Orchestrator, I want the Evaluator_Agent to return only finite float scores, so that the Orchestrator's score validation passes and the RL Selector receives a valid reward signal.

#### Acceptance Criteria

1. THE Evaluator_Agent SHALL return an Evaluation_Score that is a finite float (not NaN, not Infinity, not negative Infinity).
2. IF the parsed score is NaN or Infinity, THEN THE Evaluator_Agent SHALL raise a ValueError with a descriptive message.

### Requirement 7: Bridge Async-to-Sync Execution [P0]

**User Story:** As the Orchestrator, I want to call `evaluate()` synchronously, so that the sync EvaluatorInterface contract is satisfied even though LLMClient is async.

#### Acceptance Criteria

1. THE Evaluator_Agent SHALL wrap the async LLMClient call in a synchronous `evaluate()` method using `asyncio.run()` or an equivalent mechanism.
2. IF an event loop is already running, THEN THE Evaluator_Agent SHALL detect this and use a thread-based fallback to avoid a RuntimeError.
3. THE Evaluator_Agent SHALL propagate any exceptions raised by the async LLMClient call to the synchronous caller without swallowing them.

### Requirement 8: Handle LLM Call Failures [P0]

**User Story:** As a developer, I want the Evaluator_Agent to handle LLM call failures gracefully, so that the Orchestrator receives a clear error and can apply its retry logic.

#### Acceptance Criteria

1. IF the LLMClient raises an exception during the evaluation call, THEN THE Evaluator_Agent SHALL propagate the exception to the caller wrapped in a RuntimeError with context about the failure.
2. IF the LLMClient returns an empty response, THEN THE Evaluator_Agent SHALL raise a RuntimeError with a descriptive message.

### Requirement 9: Support Evaluator Configuration [P1]

**User Story:** As a developer, I want to configure the Evaluator_Agent's behavior, so that I can tune the scoring rubric and score range for different use cases.

#### Acceptance Criteria

1. THE Evaluator_Config SHALL specify a default Scoring_Rubric template optimized for evaluating prompt quality on a 1-to-10 scale.
2. THE Evaluator_Config SHALL specify a default minimum score of 1.0 and a default maximum score of 10.0.
3. THE Evaluator_Config SHALL be a frozen dataclass to prevent accidental mutation after construction.

### Requirement 10: Observability and Logging [P1]

**User Story:** As a developer, I want the Evaluator_Agent to log key events, so that I can debug issues and understand the evaluation behavior.

#### Acceptance Criteria

1. WHEN an `evaluate` call begins, THE Evaluator_Agent SHALL log the Prompt_Candidate length and Task_Description length.
2. WHEN score parsing completes, THE Evaluator_Agent SHALL log the parsed score value.
3. IF an error occurs during evaluation, THE Evaluator_Agent SHALL log the error details before raising the exception.
4. THE Evaluator_Agent SHALL accept an optional logger instance via dependency injection, defaulting to a module-level logger.
