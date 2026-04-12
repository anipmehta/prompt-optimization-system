# Implementation Plan: Evaluator Agent

## Overview

Implement the Evaluator Agent as a thin Python adapter over llm-toolbox's `LLMClient` that satisfies the Orchestrator's `EvaluatorInterface` protocol. Tasks build incrementally: first extract the shared async bridge, then implement config and score parser (pure functions), then the main agent class, and finally wire exports and tests. The shared async utility is extracted from the existing `GeneratorAgent._run_async` to eliminate duplication.

## Tasks

- [ ] 1. Extract shared async bridge and create evaluator package structure
  - [ ] 1.1 Create `src/shared/` package with `__init__.py` and `async_utils.py`
    - Create `src/shared/__init__.py`
    - Create `src/shared/async_utils.py` with `run_async_in_sync(coro)` function
    - Logic: try `asyncio.get_running_loop()` — if `RuntimeError`, use `asyncio.run(coro)`; otherwise spawn a thread with `asyncio.run(coro)` inside
    - This is extracted from `GeneratorAgent._run_async` in `src/generator_react_agent/agent.py`
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ] 1.2 Refactor `GeneratorAgent` to use shared async bridge
    - Replace `GeneratorAgent._run_async` static method with an import of `run_async_in_sync` from `src/shared/async_utils.py`
    - Update all call sites in `agent.py` to use the shared function
    - Ensure existing generator tests still pass
    - _Requirements: 7.1_

  - [ ] 1.3 Create `src/evaluator_agent/` package with module stubs
    - Create `src/evaluator_agent/__init__.py`
    - Create empty module files: `config.py`, `score_parser.py`, `agent.py`, `prompt_templates.py`
    - Update `pyproject.toml`: add `evaluator_agent` and `shared` packages to setuptools find, update coverage source
    - _Requirements: 1.1, 1.2_

- [ ] 2. Implement EvaluatorConfig and prompt templates
  - [ ] 2.1 Implement `DEFAULT_RUBRIC_TEMPLATE` in `prompt_templates.py`
    - Define a rubric template string that instructs the LLM to evaluate a prompt candidate on a 1-to-10 scale
    - Include `{candidate}` and `{task_description}` placeholders
    - Cover criteria: clarity, specificity, effectiveness, alignment with task
    - _Requirements: 3.2, 3.3, 9.1_

  - [ ] 2.2 Implement `EvaluatorConfig` frozen dataclass in `config.py`
    - Define `EvaluatorConfig` frozen dataclass with `rubric_template: str`, `min_score: float`, `max_score: float`
    - Set defaults: `rubric_template=DEFAULT_RUBRIC_TEMPLATE`, `min_score=1.0`, `max_score=10.0`
    - Implement `__post_init__` validation: rubric non-empty after strip, `min_score < max_score`
    - _Requirements: 3.1, 3.4, 3.5, 3.6, 3.7, 9.1, 9.2, 9.3_

  - [ ]* 2.3 Write property test: invalid score range rejected (Property 2)
    - **Property 2: Invalid score range is rejected at config construction**
    - For any pair of floats where `min_score >= max_score`, constructing `EvaluatorConfig` raises `ValueError`
    - **Validates: Requirements 3.6**

  - [ ]* 2.4 Write property test: empty rubric rejected (Property 3)
    - **Property 3: Empty rubric is rejected at config construction**
    - For any whitespace-only string as `rubric_template`, constructing `EvaluatorConfig` raises `ValueError`
    - **Validates: Requirements 3.7**

- [ ] 3. Implement score parser
  - [ ] 3.1 Implement `parse_score()` in `score_parser.py`
    - Try JSON object extraction: look for `{"score": N}` pattern via regex or `json.loads`
    - Try number-on-own-line: regex for a line containing only a number
    - Try inline number: regex `\d+\.?\d*` for first number in text
    - Raise `ValueError` with raw response text if no number found
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 3.2 Write property test: score parsing round-trip (Property 5)
    - **Property 5: Score parsing round-trip across formats**
    - For any finite float, embed in each of the three formats, verify `parse_score()` extracts the original value
    - **Validates: Requirements 5.1, 5.2**

  - [ ]* 3.3 Write property test: unparseable responses rejected (Property 6)
    - **Property 6: Unparseable responses are rejected**
    - For any string with no numeric characters, `parse_score()` raises `ValueError` whose message includes the raw text
    - **Validates: Requirements 5.3**

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement EvaluatorAgent class
  - [ ] 5.1 Implement `EvaluatorAgent.__init__()` in `agent.py`
    - Accept `llm_client: LLMClient` (required), `config: EvaluatorConfig | None` (optional), `agent_logger: logging.Logger | None` (optional)
    - Store config (default to `EvaluatorConfig()` if None), store logger (default to module-level logger)
    - Do NOT instantiate LLMClient internally
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 10.4_

  - [ ] 5.2 Implement `EvaluatorAgent.evaluate()` in `agent.py`
    - Validate `candidate` and `task_description` (non-empty after strip), raise `ValueError` if invalid
    - Log candidate length and task_description length
    - Format rubric template with candidate and task_description
    - Construct messages: system message (formatted rubric), user message (instruction to provide score)
    - Call `LLMClient.complete()` via `run_async_in_sync()` from shared bridge
    - Check response non-empty, raise `RuntimeError` if empty
    - Wrap any LLMClient exception in `RuntimeError` with context
    - Call `parse_score()` on response text
    - Validate finiteness (reject NaN/Infinity with `ValueError`)
    - Clamp to `[min_score, max_score]`
    - Log parsed score, return float
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1, 4.2, 4.3, 5.4, 6.1, 6.2, 7.1, 7.2, 7.3, 8.1, 8.2, 10.1, 10.2, 10.3_

  - [ ]* 5.3 Write property test: whitespace inputs rejected (Property 1)
    - **Property 1: Whitespace inputs are rejected**
    - For any whitespace-only string as `candidate` or `task_description`, `evaluate()` raises `ValueError` and no LLM call is made
    - **Validates: Requirements 1.3, 1.4**

  - [ ]* 5.4 Write property test: rubric template formatting preserves inputs (Property 4)
    - **Property 4: Rubric template formatting preserves inputs**
    - For any non-empty candidate and task_description, the formatted rubric sent to LLM contains both literal strings
    - **Validates: Requirements 3.3, 4.1**

  - [ ]* 5.5 Write property test: score clamping invariant (Property 7)
    - **Property 7: Score clamping invariant**
    - For any valid config and any finite parsed score, the returned score satisfies `min_score <= score <= max_score`
    - **Validates: Requirements 5.4, 6.1**

  - [ ]* 5.6 Write property test: LLM exceptions propagate as RuntimeError (Property 8)
    - **Property 8: LLM exceptions propagate as RuntimeError**
    - For any exception raised by `LLMClient.complete()`, `evaluate()` raises `RuntimeError` whose `__cause__` is the original exception
    - **Validates: Requirements 7.3, 8.1**

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Wire up exports and create unit tests
  - [ ] 7.1 Wire up `src/evaluator_agent/__init__.py` exports
    - Export `EvaluatorAgent`, `EvaluatorConfig`, `parse_score`, `DEFAULT_RUBRIC_TEMPLATE`
    - _Requirements: 1.2_

  - [ ] 7.2 Create `tests/test_evaluator_agent.py` with unit tests
    - Create mock `LLMClient` fixture returning configurable responses
    - Test protocol conformance: `EvaluatorAgent` satisfies `EvaluatorInterface`
    - Test happy-path evaluate with mocked LLM returning "7.5"
    - Test `ValueError` on empty candidate, empty task_description
    - Test `RuntimeError` on empty LLM response
    - Test `RuntimeError` wrapping LLM exceptions
    - Test NaN/Infinity rejection
    - Test score clamping (below min, above max)
    - Test message structure: system message is formatted rubric, user message present
    - Test logging: candidate/task length logged, score logged, errors logged
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 4.2, 4.3, 5.4, 6.1, 6.2, 8.1, 8.2, 10.1, 10.2, 10.3, 10.4_

  - [ ] 7.3 Create `tests/test_evaluator_config.py` with unit tests
    - Test default values: min=1.0, max=10.0, default rubric
    - Test frozen: mutation raises `FrozenInstanceError`
    - Test validation: empty rubric raises ValueError, min >= max raises ValueError
    - _Requirements: 3.1, 3.4, 3.5, 3.6, 3.7, 9.1, 9.2, 9.3_

  - [ ] 7.4 Create `tests/test_score_parser.py` with unit tests
    - Test JSON format: `{"score": 7.5}` → 7.5
    - Test number-on-line format: `"7.5\n"` → 7.5
    - Test inline format: `"I rate this a 7.5 out of 10"` → 7.5
    - Test no-number raises ValueError with raw text in message
    - Test integer scores: `"8"` → 8.0
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 7.5 Create `tests/test_async_utils.py` with unit tests
    - Test `run_async_in_sync` with simple coroutine (no running loop)
    - Test `run_async_in_sync` from within a running event loop (thread fallback)
    - Test exception propagation from coroutine
    - _Requirements: 7.1, 7.2, 7.3_

- [ ] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples, edge cases, and logging behavior
- The shared async bridge extraction (task 1.1–1.2) must happen first since both agents depend on it
- All LLMClient interactions are mocked in tests — never call real LLM providers
