# Requirements Document

## Introduction

This document specifies the requirements for the Generator ReAct Agent — a thin adapter that implements the Orchestrator's `GeneratorInterface` protocol by delegating to the `llm-toolbox` library's `Agent` class. The `llm-toolbox` library already provides the ReAct loop, LLM client with retry/backoff, tool registry with schema generation and argument validation, and structured result models. This agent's responsibility is limited to: conforming to `GeneratorInterface`, defining custom tools, crafting a system prompt for diverse candidate generation, parsing `AgentResult` into `list[str]`, and bridging async-to-sync execution.

The `llm-toolbox` library is installed as a local editable dependency (`pip install -e .`) from a sibling repository.

## Glossary

- **Generator_Agent**: The adapter class that implements the `GeneratorInterface` protocol and delegates reasoning to the llm-toolbox `Agent`.
- **GeneratorInterface**: The Protocol defined by the Orchestrator: `generate(task_description: str, num_candidates: int) -> list[str]`.
- **LLM_Toolbox_Agent**: The `Agent` class from `llm-toolbox` (`src/agent.py`) that executes an async ReAct loop given a name, system_prompt, LLMClient, ToolRegistry, and max_iterations. Returns an `AgentResult`.
- **AgentResult**: The result model from `llm-toolbox` containing `answer` (str), `reasoning_trace` (list of ReActStep), `iterations` (int), and `timed_out` (bool).
- **LLMClient**: The unified async LLM client from `llm-toolbox` supporting OpenAI/Anthropic/Groq with retry logic and exponential backoff.
- **ToolRegistry**: The tool registry from `llm-toolbox` that registers callable functions, auto-generates JSON schemas, validates arguments, and executes tools.
- **Task_Analyzer**: A custom tool that breaks down a task description into structured components (domain, intent, constraints, expected output format).
- **Template_Retriever**: A custom tool that retrieves relevant prompt templates or patterns based on task characteristics.
- **Example_Searcher**: A custom tool that finds relevant examples or few-shot demonstrations for a given task type.
- **Candidate_Refiner**: A custom tool that takes a draft prompt candidate and improves it based on specified criteria.
- **Task_Description**: A natural-language description of the task for which prompts should be optimized.
- **Prompt_Candidate**: A single generated prompt text that is a candidate solution for a given Task_Description.
- **Agent_Config**: Configuration dataclass for the Generator_Agent, including max_iterations, tool selection, and system prompt.

## Requirements

### Requirement 1: Implement the GeneratorInterface Protocol [P0]

**User Story:** As the Orchestrator, I want the Generator_Agent to conform to the GeneratorInterface protocol, so that it can be injected as the generator component in optimization runs.

#### Acceptance Criteria

1. THE Generator_Agent SHALL implement a `generate` method that accepts a Task_Description (str) and a num_candidates (int) and returns a list of Prompt_Candidates (list[str]).
2. WHEN the Orchestrator calls `generate`, THE Generator_Agent SHALL return exactly the number of Prompt_Candidates specified by num_candidates.
3. THE Generator_Agent SHALL satisfy the `GeneratorInterface` Protocol so that `isinstance` checks using `runtime_checkable` pass and the Orchestrator can accept the Generator_Agent via dependency injection.
4. IF num_candidates is less than 1, THEN THE Generator_Agent SHALL raise a ValueError with a descriptive message.
5. IF the Task_Description is empty or contains only whitespace, THEN THE Generator_Agent SHALL raise a ValueError with a descriptive message.

### Requirement 2: Delegate to llm-toolbox Agent [P0]

**User Story:** As a developer, I want the Generator_Agent to delegate all ReAct loop execution to the llm-toolbox Agent class, so that the codebase stays thin and avoids reimplementing loop mechanics, retries, or tool dispatch.

#### Acceptance Criteria

1. WHEN `generate` is called, THE Generator_Agent SHALL instantiate or reuse an LLM_Toolbox_Agent configured with the appropriate system prompt, LLMClient, ToolRegistry, and max_iterations.
2. THE Generator_Agent SHALL call `await agent.run(task_description)` on the LLM_Toolbox_Agent to execute the ReAct loop.
3. THE Generator_Agent SHALL NOT implement its own ReAct loop, tool dispatch, retry logic, or backoff — these are provided by llm-toolbox.
4. THE Generator_Agent SHALL accept an LLMClient instance via dependency injection at construction time and pass it to the LLM_Toolbox_Agent.
5. THE Generator_Agent SHALL NOT instantiate its own LLMClient internally.

### Requirement 3: Bridge Async-to-Sync Execution [P0]

**User Story:** As the Orchestrator, I want to call `generate()` synchronously, so that the sync GeneratorInterface contract is satisfied even though llm-toolbox's Agent.run is async.

#### Acceptance Criteria

1. THE Generator_Agent SHALL wrap the async `agent.run()` call in a synchronous `generate()` method using `asyncio.run()` or an equivalent mechanism.
2. IF an event loop is already running (e.g., in a Jupyter notebook or async context), THEN THE Generator_Agent SHALL detect this and use an appropriate fallback (e.g., `nest_asyncio` or thread-based execution) to avoid a RuntimeError.
3. THE Generator_Agent SHALL propagate any exceptions raised by the async `agent.run()` call to the synchronous caller without swallowing them.

### Requirement 4: Parse AgentResult into Candidate List [P0]

**User Story:** As the Orchestrator, I want the Generator_Agent to parse the AgentResult.answer into a structured list of prompt candidates, so that the output conforms to the GeneratorInterface contract.

#### Acceptance Criteria

1. WHEN the LLM_Toolbox_Agent returns an AgentResult, THE Generator_Agent SHALL parse the `answer` field into a list of individual Prompt_Candidates.
2. THE Generator_Agent SHALL support parsing candidates from the answer when they are formatted as a numbered list, a JSON array, or delimited by a known separator.
3. IF the parsed candidate count does not match num_candidates, THEN THE Generator_Agent SHALL either truncate (if too many) or request additional candidates (via a follow-up agent.run call) to meet the exact count.
4. IF the AgentResult.answer is empty or cannot be parsed into any candidates, THEN THE Generator_Agent SHALL raise a RuntimeError with a descriptive message.

### Requirement 5: Register Custom Tools with ToolRegistry [P0]

**User Story:** As a developer, I want the Generator_Agent to register its custom tools with llm-toolbox's ToolRegistry, so that the Agent can discover and invoke them during the ReAct loop.

#### Acceptance Criteria

1. THE Generator_Agent SHALL create a ToolRegistry instance and register the Task_Analyzer, Template_Retriever, Example_Searcher, and Candidate_Refiner tools using `register_from_function()` or `register()`.
2. WHEN the LLM_Toolbox_Agent is instantiated, THE Generator_Agent SHALL pass the populated ToolRegistry to it.
3. THE Agent_Config SHALL allow specifying which tools to enable, so that tools can be selectively included or excluded.
4. IF no tools are enabled in the Agent_Config, THEN THE Generator_Agent SHALL still function by relying on the LLM_Toolbox_Agent's reasoning without tool calls.

### Requirement 6: Provide Task Analysis Tool [P1]

**User Story:** As a prompt engineer, I want the Generator_Agent to analyze the task description, so that it understands the domain, intent, and constraints before generating prompts.

#### Acceptance Criteria

1. THE Task_Analyzer tool SHALL accept a Task_Description (str) and return a structured analysis (str) containing the task domain, intent, constraints, and expected output format.
2. THE Task_Analyzer SHALL be implemented as a callable function compatible with ToolRegistry's `register_from_function()`.
3. WHEN the Task_Analyzer uses the LLMClient for analysis, THE Task_Analyzer SHALL accept the LLMClient via closure or partial application at registration time.

### Requirement 7: Provide Template Retrieval Tool [P2]

**User Story:** As a prompt engineer, I want the Generator_Agent to retrieve relevant prompt templates, so that generated candidates follow proven patterns.

#### Acceptance Criteria

1. THE Template_Retriever tool SHALL accept a query (str) describing the task characteristics and return a string containing relevant prompt templates.
2. WHEN no matching templates are found, THE Template_Retriever SHALL return a message indicating no templates were found.

### Requirement 8: Provide Example Search Tool [P2]

**User Story:** As a prompt engineer, I want the Generator_Agent to find relevant examples for the task, so that generated prompts can include effective few-shot demonstrations.

#### Acceptance Criteria

1. THE Example_Searcher tool SHALL accept a task type description (str) and return a string containing relevant input-output examples.
2. WHEN no matching examples are found, THE Example_Searcher SHALL return a message indicating no examples were found.

### Requirement 9: Provide Candidate Refinement Tool [P1]

**User Story:** As a prompt engineer, I want the Generator_Agent to refine draft prompt candidates, so that the final candidates are polished and effective.

#### Acceptance Criteria

1. THE Candidate_Refiner tool SHALL accept a draft Prompt_Candidate (str) and return an improved Prompt_Candidate (str).
2. WHEN the Candidate_Refiner uses the LLMClient for refinement, THE Candidate_Refiner SHALL accept the LLMClient via closure or partial application at registration time.
3. THE Candidate_Refiner SHALL preserve the core intent of the original draft while improving clarity, specificity, and effectiveness.

### Requirement 10: Design System Prompt for Diverse Candidate Generation [P0]

**User Story:** As a prompt engineer, I want the system prompt to instruct the LLM_Toolbox_Agent to generate diverse prompt candidates, so that the Selector has meaningfully different options to choose from.

#### Acceptance Criteria

1. THE Generator_Agent SHALL construct a system prompt that instructs the LLM_Toolbox_Agent to produce exactly num_candidates diverse Prompt_Candidates for the given Task_Description.
2. THE system prompt SHALL instruct the LLM_Toolbox_Agent to vary candidates across dimensions such as instruction style, level of detail, use of examples, and output format specification.
3. THE system prompt SHALL instruct the LLM_Toolbox_Agent to use the available tools (Task_Analyzer, Template_Retriever, Example_Searcher, Candidate_Refiner) to gather context before generating candidates.
4. THE system prompt SHALL instruct the LLM_Toolbox_Agent to format its final answer as a parseable list (e.g., numbered list or JSON array) so that the Generator_Agent can extract individual candidates.
5. THE Agent_Config SHALL allow overriding the default system prompt template.

### Requirement 11: Ensure Candidate Diversity and Uniqueness [P1]

**User Story:** As a prompt engineer, I want the generated prompt candidates to be diverse, so that the Selector has meaningfully different options to choose from.

#### Acceptance Criteria

1. WHEN the Generator_Agent produces the final list of Prompt_Candidates, THE Generator_Agent SHALL verify that no two candidates are identical strings.
2. IF duplicate candidates are detected, THEN THE Generator_Agent SHALL deduplicate them and attempt to generate replacements to meet the requested num_candidates count.
3. THE Generator_Agent SHALL strip leading and trailing whitespace from each candidate before performing uniqueness checks.

### Requirement 12: Handle Agent Timeout and Failure [P0]

**User Story:** As a developer, I want the Generator_Agent to handle cases where the llm-toolbox Agent times out or fails, so that the Orchestrator receives a clear error.

#### Acceptance Criteria

1. IF the AgentResult.timed_out field is True and the AgentResult.answer is empty, THEN THE Generator_Agent SHALL raise a TimeoutError with a descriptive message including the number of iterations completed.
2. IF the AgentResult.timed_out field is True and the AgentResult.answer is non-empty, THEN THE Generator_Agent SHALL attempt to parse whatever candidates are available from the answer.
3. IF the LLM_Toolbox_Agent raises an exception during `agent.run()`, THEN THE Generator_Agent SHALL propagate the exception to the caller wrapped in a RuntimeError with context about the failure.

### Requirement 13: Support Agent Configuration [P1]

**User Story:** As a developer, I want to configure the Generator_Agent's behavior, so that I can tune the agent's max iterations, tool selection, and system prompt.

#### Acceptance Criteria

1. THE Generator_Agent SHALL accept an Agent_Config at construction time.
2. THE Agent_Config SHALL specify max_iterations for the LLM_Toolbox_Agent (default: 5).
3. IF max_iterations is less than 1, THEN THE Generator_Agent SHALL raise a ValueError at construction time.
4. THE Agent_Config SHALL specify which tools to enable (default: all four tools enabled).
5. THE Agent_Config SHALL specify an optional custom system prompt template (default: a built-in template optimized for diverse candidate generation).
6. THE Agent_Config SHALL have sensible defaults so that the Generator_Agent can be constructed with only an LLMClient.

### Requirement 14: Observability and Logging [P1]

**User Story:** As a developer, I want the Generator_Agent to log key events, so that I can debug issues and understand the agent's behavior.

#### Acceptance Criteria

1. WHEN a `generate` call begins, THE Generator_Agent SHALL log the Task_Description length and num_candidates requested.
2. WHEN the LLM_Toolbox_Agent completes, THE Generator_Agent SHALL log the number of iterations executed and whether the agent timed out.
3. WHEN candidate parsing completes, THE Generator_Agent SHALL log the number of candidates parsed and the number returned.
4. IF an error occurs during generation, THE Generator_Agent SHALL log the error details before raising the exception.
5. THE Generator_Agent SHALL accept an optional logger instance via dependency injection, defaulting to a module-level logger.
