# Requirements Document

## Introduction

This document specifies the requirements for the Generator ReAct Agent — a concrete implementation of the `GeneratorInterface` protocol defined in the Prompt Optimization Orchestrator. The agent uses a ReAct (Reason + Act) loop to produce diverse, high-quality prompt candidates for a given task description.

The ReAct loop follows a Thought → Action → Observation cycle: the agent reasons about the task, invokes tools (task analysis, template retrieval, example search, candidate refinement), observes results, and repeats until it has enough information to produce the requested number of prompt candidates. The agent uses the `llm-toolbox` library for its underlying LLM client.

## Glossary

- **Generator_Agent**: The ReAct-based agent that implements the `GeneratorInterface` protocol and produces prompt candidates.
- **ReAct_Loop**: An iterative reasoning cycle consisting of Thought, Action, and Observation steps that the Generator_Agent executes to gather information and refine candidates.
- **Thought**: A reasoning step in the ReAct_Loop where the Generator_Agent plans its next action based on accumulated context.
- **Action**: A tool invocation step in the ReAct_Loop where the Generator_Agent calls one of its available tools.
- **Observation**: The result returned by a tool invocation, which the Generator_Agent incorporates into its reasoning context.
- **Tool**: A callable function available to the Generator_Agent during the ReAct_Loop (e.g., Task_Analyzer, Template_Retriever, Example_Searcher, Candidate_Refiner).
- **Task_Analyzer**: A tool that breaks down a Task_Description into structured components such as domain, intent, constraints, and expected output format.
- **Template_Retriever**: A tool that retrieves relevant prompt templates or patterns based on task characteristics.
- **Example_Searcher**: A tool that finds relevant examples or few-shot demonstrations for a given task type.
- **Candidate_Refiner**: A tool that takes a draft prompt candidate and improves it based on specified criteria.
- **Task_Description**: A natural-language description of the task for which prompts should be optimized (as defined in the Orchestrator).
- **Prompt_Candidate**: A single generated prompt text that is a candidate solution for a given Task_Description.
- **LLM_Client**: The language model client from the `llm-toolbox` library used by the Generator_Agent for reasoning and generation.
- **Max_Iterations**: The maximum number of ReAct_Loop cycles the Generator_Agent executes before producing final candidates.
- **Agent_Config**: Configuration object for the Generator_Agent, including model parameters, max iterations, and tool settings.

## Requirements

### Requirement 1: Implement the GeneratorInterface Protocol

**User Story:** As the Orchestrator, I want the Generator_Agent to conform to the GeneratorInterface protocol, so that it can be injected as the generator component in optimization runs.

#### Acceptance Criteria

1. THE Generator_Agent SHALL implement a `generate` method that accepts a Task_Description (str) and a num_candidates (int) and returns a list of Prompt_Candidates (list[str]).
2. WHEN the Orchestrator calls `generate`, THE Generator_Agent SHALL return exactly the number of Prompt_Candidates specified by num_candidates.
3. THE Generator_Agent SHALL satisfy the `GeneratorInterface` Protocol so that `isinstance` checks using `runtime_checkable` pass and the Orchestrator can accept the Generator_Agent via dependency injection.
4. IF num_candidates is less than 1, THEN THE Generator_Agent SHALL raise a ValueError with a descriptive message.
5. IF the Task_Description is empty or contains only whitespace, THEN THE Generator_Agent SHALL raise a ValueError with a descriptive message.

### Requirement 2: Execute the ReAct Reasoning Loop

**User Story:** As a prompt engineer, I want the Generator_Agent to reason iteratively about the task before generating candidates, so that the resulting prompts are well-informed and high quality.

#### Acceptance Criteria

1. WHEN `generate` is called, THE Generator_Agent SHALL execute a ReAct_Loop consisting of Thought, Action, and Observation steps.
2. WHILE the ReAct_Loop is active, THE Generator_Agent SHALL produce a Thought step before each Action step, documenting its reasoning for the chosen action.
3. WHEN the Generator_Agent invokes a Tool during an Action step, THE Generator_Agent SHALL record the Observation returned by the Tool.
4. WHEN the Generator_Agent determines it has gathered sufficient information, THE Generator_Agent SHALL exit the ReAct_Loop and proceed to candidate generation.
5. IF the ReAct_Loop reaches the Max_Iterations limit, THEN THE Generator_Agent SHALL exit the loop and produce candidates using whatever information has been gathered so far.
6. THE Generator_Agent SHALL maintain an ordered trace of all Thought, Action, and Observation steps for the duration of a single `generate` call.

### Requirement 3: Provide Task Analysis Tool

**User Story:** As a prompt engineer, I want the Generator_Agent to analyze the task description, so that it understands the domain, intent, and constraints before generating prompts.

#### Acceptance Criteria

1. THE Task_Analyzer tool SHALL accept a Task_Description and return a structured analysis containing the task domain, intent, constraints, and expected output format.
2. WHEN the Generator_Agent invokes the Task_Analyzer, THE Task_Analyzer SHALL use the LLM_Client to produce the analysis.
3. IF the Task_Description is ambiguous, THEN THE Task_Analyzer SHALL return its best interpretation along with a confidence indicator.
4. IF the LLM_Client call fails during task analysis, THEN THE Task_Analyzer SHALL raise an error that the Generator_Agent can handle in its ReAct_Loop.

### Requirement 4: Provide Template Retrieval Tool

**User Story:** As a prompt engineer, I want the Generator_Agent to retrieve relevant prompt templates, so that generated candidates follow proven patterns.

#### Acceptance Criteria

1. THE Template_Retriever tool SHALL accept a query describing the task characteristics and return a list of relevant prompt templates.
2. WHEN no matching templates are found, THE Template_Retriever SHALL return an empty list.
3. THE Template_Retriever SHALL return templates ranked by relevance to the query.

### Requirement 5: Provide Example Search Tool

**User Story:** As a prompt engineer, I want the Generator_Agent to find relevant examples for the task, so that generated prompts can include effective few-shot demonstrations.

#### Acceptance Criteria

1. THE Example_Searcher tool SHALL accept a task type description and return a list of relevant input-output examples.
2. WHEN no matching examples are found, THE Example_Searcher SHALL return an empty list.
3. THE Example_Searcher SHALL return examples ranked by relevance to the task type.

### Requirement 6: Provide Candidate Refinement Tool

**User Story:** As a prompt engineer, I want the Generator_Agent to refine draft prompt candidates, so that the final candidates are polished and effective.

#### Acceptance Criteria

1. THE Candidate_Refiner tool SHALL accept a draft Prompt_Candidate and refinement criteria and return an improved Prompt_Candidate.
2. WHEN the Generator_Agent invokes the Candidate_Refiner, THE Candidate_Refiner SHALL use the LLM_Client to improve the draft candidate.
3. IF the LLM_Client call fails during refinement, THEN THE Candidate_Refiner SHALL raise an error that the Generator_Agent can handle in its ReAct_Loop.
4. THE Candidate_Refiner SHALL preserve the core intent of the original draft while improving clarity, specificity, and effectiveness.

### Requirement 7: Produce Diverse Prompt Candidates

**User Story:** As a prompt engineer, I want the generated prompt candidates to be diverse, so that the RL Selector has meaningfully different options to choose from.

#### Acceptance Criteria

1. WHEN the Generator_Agent produces the final list of Prompt_Candidates, THE Generator_Agent SHALL ensure that each candidate uses a distinct prompting strategy or structure.
2. THE Generator_Agent SHALL produce candidates that vary across dimensions such as instruction style, level of detail, use of examples, and output format specification.
3. IF num_candidates is greater than 1, THEN THE Generator_Agent SHALL verify that no two returned Prompt_Candidates are identical strings.

### Requirement 8: Integrate with llm-toolbox LLM Client

**User Story:** As a developer, I want the Generator_Agent to use the llm-toolbox library for LLM calls, so that it shares the same LLM infrastructure as the rest of the system.

#### Acceptance Criteria

1. THE Generator_Agent SHALL accept an LLM_Client instance from the `llm-toolbox` library via dependency injection at construction time.
2. THE Generator_Agent SHALL use the injected LLM_Client for all LLM calls during the ReAct_Loop and candidate generation.
3. THE Generator_Agent SHALL not instantiate its own LLM_Client internally.

### Requirement 9: Handle Errors Gracefully in the ReAct Loop

**User Story:** As a prompt engineer, I want the Generator_Agent to handle tool failures gracefully, so that a single tool error does not prevent candidate generation.

#### Acceptance Criteria

1. IF a Tool invocation fails during the ReAct_Loop, THEN THE Generator_Agent SHALL record the error as an Observation and continue reasoning with the remaining tools.
2. IF all Tool invocations fail during the ReAct_Loop, THEN THE Generator_Agent SHALL fall back to generating candidates using only the original Task_Description and the LLM_Client.
3. IF the LLM_Client fails during final candidate generation, THEN THE Generator_Agent SHALL raise an error to the caller.
4. THE Generator_Agent SHALL not retry failed Tool invocations within the ReAct_Loop (retries are handled at the Orchestrator level).

### Requirement 10: Support Agent Configuration

**User Story:** As a developer, I want to configure the Generator_Agent's behavior, so that I can tune the ReAct loop depth and generation parameters.

#### Acceptance Criteria

1. THE Generator_Agent SHALL accept an Agent_Config at construction time specifying Max_Iterations for the ReAct_Loop.
2. THE Agent_Config SHALL have a default Max_Iterations value of 5.
3. IF Max_Iterations is less than 1, THEN THE Generator_Agent SHALL raise a ValueError at construction time.
4. THE Agent_Config SHALL allow specifying a system prompt template used for the LLM_Client during the ReAct_Loop.
5. THE Agent_Config SHALL have a sensible default system prompt template that instructs the LLM to follow the ReAct pattern.

### Requirement 11: Observability and Logging

**User Story:** As a developer, I want the Generator_Agent to log key events during generation, so that I can debug issues and understand the agent's reasoning process.

#### Acceptance Criteria

1. WHEN a `generate` call begins, THE Generator_Agent SHALL log the Task_Description and num_candidates.
2. WHEN the Generator_Agent produces a Thought step, THE Generator_Agent SHALL log the thought content.
3. WHEN the Generator_Agent invokes a Tool, THE Generator_Agent SHALL log the tool name and input parameters.
4. WHEN a Tool invocation fails, THE Generator_Agent SHALL log the tool name and error details.
5. WHEN the Generator_Agent completes candidate generation, THE Generator_Agent SHALL log the number of candidates produced and the total number of ReAct_Loop iterations executed.
6. THE Generator_Agent SHALL accept an optional logger instance via dependency injection, defaulting to a module-level logger.
### Requirement 12: Circuit Breaker for Tool Failures

**User Story:** As a developer, I want the Generator_Agent to stop calling a tool that keeps failing, so that the ReAct loop doesn't waste time on broken tools.

#### Acceptance Criteria

1. THE Generator_Agent SHALL track consecutive failure counts per tool across ReAct_Loop iterations within a single `generate` call.
2. IF a tool fails more than a configurable failure threshold (default: 3 consecutive failures), THEN THE Generator_Agent SHALL mark that tool as tripped and skip it for the remainder of the `generate` call.
3. WHEN a tripped tool is skipped, THE Generator_Agent SHALL log a warning indicating the tool is circuit-broken and record this in the Observation trace.
4. THE Agent_Config SHALL allow specifying the circuit breaker failure threshold per tool.
5. THE Generator_Agent SHALL reset all circuit breaker states at the start of each new `generate` call.

### Requirement 13: Prompt Injection Protection

**User Story:** As a security engineer, I want the Generator_Agent to sanitize inputs before passing them to the LLM, so that malicious task descriptions cannot hijack the agent's behavior.

#### Acceptance Criteria

1. BEFORE passing the Task_Description to the LLM_Client or any tool, THE Generator_Agent SHALL sanitize the input by escaping or removing known prompt injection patterns (e.g., instruction overrides, role reassignment, delimiter escapes).
2. THE Generator_Agent SHALL reject Task_Descriptions that contain control characters or null bytes, raising a ValueError with a descriptive message.
3. THE Generator_Agent SHALL enforce a maximum length for Task_Description (configurable via Agent_Config, default: 10,000 characters) and raise a ValueError if exceeded.
4. THE Generator_Agent SHALL NOT include raw user input directly in system prompts — user input SHALL always be placed in clearly delimited user-content sections.
5. WHEN a sanitization step modifies the Task_Description, THE Generator_Agent SHALL log a warning with details of what was sanitized.

### Requirement 14: Generation Timeout

**User Story:** As a developer, I want the Generator_Agent to respect a time budget, so that a slow LLM or stuck ReAct loop doesn't block the Orchestrator indefinitely.

#### Acceptance Criteria

1. THE Agent_Config SHALL allow specifying a timeout_seconds for the `generate` call (default: 60 seconds).
2. IF the `generate` call exceeds timeout_seconds, THEN THE Generator_Agent SHALL stop the ReAct_Loop and produce candidates using whatever information has been gathered so far.
3. IF no useful information has been gathered when the timeout fires, THEN THE Generator_Agent SHALL raise a TimeoutError with a descriptive message.
4. THE Generator_Agent SHALL check the elapsed time before each ReAct_Loop iteration and before final candidate generation.
5. WHEN a timeout occurs, THE Generator_Agent SHALL log a warning including the elapsed time and the number of iterations completed.

### Requirement 15: Input Sanitization for Tools

**User Story:** As a security engineer, I want all inputs passed to tools to be sanitized, so that tool implementations are protected from malformed or malicious data.

#### Acceptance Criteria

1. BEFORE passing any input to a Tool, THE Generator_Agent SHALL validate that the input is a non-empty string and does not contain control characters or null bytes.
2. THE Generator_Agent SHALL enforce a maximum input length per tool call (configurable via Agent_Config, default: 5,000 characters) and truncate inputs that exceed the limit.
3. WHEN an input is truncated, THE Generator_Agent SHALL log a warning and record the truncation in the Observation trace.
4. IF a Tool returns output that exceeds a configurable maximum output length (default: 50,000 characters), THEN THE Generator_Agent SHALL truncate the output before incorporating it into the ReAct_Loop context.
