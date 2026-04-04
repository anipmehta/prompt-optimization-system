# Implementation Plan: Prompt Optimization Orchestrator

## Overview

Implement the Prompt Optimization Orchestrator as a Python library using dataclasses, Protocol-based interfaces, and dependency injection. Tasks are ordered to build up from data models and interfaces through core orchestration logic, serialization, and testing.

## Tasks

- [ ] 1. Set up project structure, exceptions, and data models
  - [ ] 1.1 Create project directory structure and `__init__.py` files
    - Create `src/prompt_optimization_orchestrator/` package
    - Create `tests/` directory with `conftest.py`
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ] 1.2 Implement exception hierarchy
    - Create `exceptions.py` with `OrchestratorError`, `ValidationError`, `DeserializationError`, `RunNotFoundError`, `ComponentError`, `DataIntegrityError`
    - _Requirements: 1.4, 1.5, 10.4_

  - [ ] 1.3 Implement data models and enums
    - Create `models.py` with `IterationStatus`, `RunStatus`, `OptimizationConfig`, `IterationResult`, `OptimizationRun`, `OptimizationResult` dataclasses
    - _Requirements: 1.1, 1.3, 6.2, 6.5_

  - [ ] 1.4 Implement component interfaces (Protocols)
    - Create `interfaces.py` with `GeneratorInterface`, `SelectorInterface`, `EvaluatorInterface` Protocol classes
    - _Requirements: 8.1, 8.2, 8.3_

- [ ] 2. Implement validation and run initialization
  - [ ] 2.1 Implement input validation functions
    - Validate `task_description` is non-empty after stripping whitespace
    - Validate `OptimizationConfig` fields: `num_candidates > 0`, `num_iterations > 0`, `retry_limit >= 0`
    - Return descriptive errors listing each invalid field
    - _Requirements: 1.2, 1.3, 1.4, 1.5_

  - [ ]* 2.2 Write property test: empty task descriptions are rejected
    - **Property 2: Empty task descriptions are rejected**
    - **Validates: Requirements 1.2, 1.4**

  - [ ]* 2.3 Write property test: invalid config values are rejected
    - **Property 3: Invalid config values are rejected**
    - **Validates: Requirements 1.3, 1.5**

  - [ ] 2.4 Implement `start_run` method on Orchestrator
    - Create `orchestrator.py` with `Orchestrator` class
    - Accept Generator, Selector, Evaluator via constructor (dependency injection)
    - `start_run` validates inputs, creates `OptimizationRun` with unique `run_id`, stores it, returns `run_id`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 8.4_

  - [ ]* 2.5 Write property test: run creation produces unique identifiers
    - **Property 1: Run creation produces unique identifiers**
    - **Validates: Requirements 1.1**

- [ ] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement iteration lifecycle — generate, select, evaluate, reward
  - [ ] 4.1 Implement candidate generation step with retry logic
    - Call Generator with `task_description` and `num_candidates`
    - Validate returned candidate count; log warning if fewer than requested
    - Mark iteration as FAILED if zero candidates returned
    - Retry on timeout/connection error up to `retry_limit`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 4.2 Implement candidate selection step with retry and integrity check
    - Pass candidates to Selector
    - Verify chosen candidate exists in original candidate set; mark FAILED with data integrity error if not
    - Retry on failure up to `retry_limit`
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ] 4.3 Implement evaluation step with retry and score validation
    - Send chosen candidate and `task_description` to Evaluator
    - Validate score is a finite number; mark FAILED with validation error if not
    - Retry on failure up to `retry_limit`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ] 4.4 Implement reward feedback step
    - Send evaluation score to Selector's `reward` method
    - On success, mark iteration as COMPLETE
    - On failure, log the failure and mark iteration as DEGRADED, continue to next iteration
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 4.5 Write property test: component argument passing integrity
    - **Property 4: Component argument passing integrity**
    - **Validates: Requirements 2.1, 3.1, 4.1, 5.1**

  - [ ]* 4.6 Write property test: retry behavior on component failure
    - **Property 5: Retry behavior on component failure**
    - **Validates: Requirements 2.5, 3.4, 4.4**

  - [ ]* 4.7 Write property test: selected candidate membership invariant
    - **Property 6: Selected candidate membership invariant**
    - **Validates: Requirements 3.2, 3.3**

  - [ ]* 4.8 Write property test: evaluation score finiteness validation
    - **Property 7: Evaluation score finiteness validation**
    - **Validates: Requirements 4.2, 4.3**

  - [ ]* 4.9 Write property test: successful iteration completeness
    - **Property 8: Successful iteration completeness**
    - **Validates: Requirements 5.2, 6.2**

- [ ] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement run execution, abort logic, and results
  - [ ] 6.1 Implement `execute_run` method
    - Execute iterations sequentially up to `num_iterations`
    - Track iteration statuses (PENDING, IN_PROGRESS, COMPLETE, FAILED, DEGRADED)
    - Abort run if more than half of iterations fail; set status to ABORTED
    - Mark run as COMPLETE when all iterations finish without abort
    - _Requirements: 6.1, 6.3, 6.4, 6.5_

  - [ ] 6.2 Implement result aggregation and best candidate selection
    - Build `OptimizationResult` from completed iterations
    - Select candidate with highest `evaluation_score`; tie-break by latest iteration
    - Return list of all iteration results
    - _Requirements: 7.1, 7.2, 7.4_

  - [ ] 6.3 Implement `get_run` method
    - Look up run by `run_id`, return current state
    - Raise `RunNotFoundError` for unknown IDs
    - _Requirements: 7.3_

  - [ ]* 6.4 Write property test: iteration count matches configuration
    - **Property 9: Iteration count matches configuration**
    - **Validates: Requirements 6.1**

  - [ ]* 6.5 Write property test: abort on majority failure
    - **Property 10: Abort on majority failure**
    - **Validates: Requirements 6.4**

  - [ ]* 6.6 Write property test: iteration status validity
    - **Property 11: Iteration status validity**
    - **Validates: Requirements 6.5**

  - [ ]* 6.7 Write property test: best candidate has highest score
    - **Property 12: Best candidate has highest score**
    - **Validates: Requirements 7.1, 7.4**

  - [ ]* 6.8 Write property test: run lookup returns current state
    - **Property 13: Run lookup returns current state**
    - **Validates: Requirements 7.3**

- [ ] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement observability, serialization, and final wiring
  - [ ] 8.1 Implement logging throughout the Orchestrator
    - Log run start with run_id, task_description, config
    - Log iteration start with iteration number and run_id
    - Log component failures with component name, error details, retry attempt
    - Log run completion/abort with final status and summary
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [ ] 8.2 Implement serialization module
    - Create `serialization.py` with `serialize_run` and `deserialize_run` functions
    - Handle dataclass-to-JSON and JSON-to-dataclass conversion including enums
    - Validate JSON structure on deserialization; raise `DeserializationError` for malformed input
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [ ]* 8.3 Write property test: serialization round-trip
    - **Property 14: Serialization round-trip**
    - **Validates: Requirements 10.1, 10.2, 10.3**

  - [ ] 8.4 Wire up package exports in `__init__.py`
    - Export all public classes, interfaces, functions, and exceptions
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ] 9. Implement shared test fixtures and unit tests
  - [ ] 9.1 Create `conftest.py` with mock components and shared fixtures
    - Mock `GeneratorInterface`, `SelectorInterface`, `EvaluatorInterface`
    - Create fixture for a default `OptimizationConfig`
    - Create fixture for a pre-built `Orchestrator` with mocks
    - _Requirements: 8.1, 8.2, 8.3_

  - [ ]* 9.2 Write unit tests for happy-path run execution
    - Test a full run with known inputs and verify results
    - _Requirements: 6.1, 6.2, 6.3, 7.1, 7.2_

  - [ ]* 9.3 Write unit tests for edge cases and error conditions
    - Test generator returning fewer candidates than requested (Requirement 2.3)
    - Test NaN/Inf evaluation scores (Requirement 4.3)
    - Test reward rejection leading to DEGRADED iteration (Requirement 5.3)
    - Test deserialization of malformed JSON (Requirement 10.4)
    - _Requirements: 2.3, 4.3, 5.3, 10.4_

  - [ ]* 9.4 Write unit tests for logging verification
    - Capture log output and assert expected messages for run start, iteration start, component failures, run completion
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 10. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples, edge cases, and logging behavior
- All component interactions use dependency injection for testability
