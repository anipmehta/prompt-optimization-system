# Implementation Plan: Generator ReAct Agent

## Overview

Implement the Generator ReAct Agent as a thin Python adapter over llm-toolbox's `Agent` class. The agent implements the Orchestrator's `GeneratorInterface` protocol by configuring custom tools, crafting a system prompt, parsing `AgentResult.answer` into `list[str]`, and bridging async-to-sync execution. Tasks build incrementally from config/models through parsing, tools, and the main agent class, ending with integration wiring.

## Tasks

- [x] 1. Create package structure, config, and answer parser
  - [x] 1.1 Create `src/generator_react_agent/` package with `__init__.py` and module stubs
    - Create `src/generator_react_agent/__init__.py`
    - Create empty module files: `config.py`, `parser.py`, `tools.py`, `agent.py`
    - Update `pyproject.toml` to add the `generator_react_agent` package (add to packages, update coverage source)
    - _Requirements: 13.1, 13.6_

  - [x] 1.2 Implement `AgentConfig` dataclass in `config.py`
    - Define `AgentConfig` frozen dataclass with `max_iterations`, `enabled_tools`, `system_prompt_template`
    - Implement `__post_init__` validation: `max_iterations >= 1`, `enabled_tools` subset of known names, `system_prompt_template` non-empty after strip
    - Define `DEFAULT_SYSTEM_PROMPT` constant with `{num_candidates}` placeholder
    - Define `KNOWN_TOOL_NAMES` constant
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 10.1, 10.5_

  - [ ]* 1.3 Write property test: invalid config values are rejected (Property 2)
    - **Property 2: Invalid input rejection — config validation**
    - Test that `max_iterations < 1` raises `ValueError`, unknown tool names raise `ValueError`, empty `system_prompt_template` raises `ValueError`
    - **Validates: Requirements 13.3**

  - [x] 1.4 Implement `parse_candidates()` in `parser.py`
    - Implement JSON array parsing (try `json.loads` if answer looks like `[...]`)
    - Implement numbered list parsing (regex for `1. ...`, `2. ...`)
    - Implement delimiter-based parsing (split on `---` or `===`)
    - Implement fallback: treat entire answer as single candidate
    - Strip whitespace from each parsed candidate, filter out empty strings
    - _Requirements: 4.1, 4.2_

  - [ ]* 1.5 Write property test: parsing round-trip (Property 3)
    - **Property 3: Parsing round-trip consistency**
    - For any list of N distinct non-empty strings, format as numbered list, parse with `parse_candidates()`, verify same N strings returned
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 1.6 Write property test: unparseable answer raises RuntimeError (Property 4)
    - **Property 4: Unparseable answer raises RuntimeError**
    - For empty or None-like answer strings, verify `RuntimeError` is raised
    - **Validates: Requirements 4.4**

- [x] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Implement tool functions and tool registry builder
  - [x] 3.1 Implement tool functions in `tools.py`
    - Implement `analyze_task(task_description: str) -> str` — uses LLMClient via closure to break down task
    - Implement `retrieve_templates(query: str) -> str` — returns relevant templates or "no templates found"
    - Implement `search_examples(task_type: str) -> str` — returns relevant examples or "no examples found"
    - Implement `refine_candidate(draft: str) -> str` — uses LLMClient via closure to improve a draft
    - _Requirements: 6.1, 6.2, 6.3, 7.1, 7.2, 8.1, 8.2, 9.1, 9.2, 9.3_

  - [x] 3.2 Implement `build_tool_registry()` in `tools.py`
    - Accept `llm_client` and `enabled_tools` frozenset
    - Register only the tools whose names are in `enabled_tools`
    - Use `ToolRegistry.register_from_function()` for each tool
    - Tools needing LLM access receive `llm_client` via closure
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ]* 3.3 Write property test: tool registry respects enabled_tools config (Property 5)
    - **Property 5: Tool registry respects enabled_tools config**
    - For any subset of known tool names, verify built `ToolRegistry` contains exactly those tools
    - **Validates: Requirements 5.3**

  - [ ]* 3.4 Write property test: tool functions return non-empty strings (Property 6)
    - **Property 6: Tool functions return non-empty strings**
    - For any valid non-empty string input, each tool function returns a non-empty string (with mocked LLMClient)
    - **Validates: Requirements 6.1, 7.1, 8.1, 9.1**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement GeneratorAgent class
  - [x] 5.1 Implement `GeneratorAgent.__init__()` in `agent.py`
    - Accept `llm_client: LLMClient` (required), `config: AgentConfig | None` (optional), `logger: logging.Logger | None` (optional)
    - Store config (default to `AgentConfig()` if None), store logger (default to module-level logger)
    - Do NOT instantiate LLMClient internally — only accept via DI
    - _Requirements: 2.4, 2.5, 13.1, 13.6, 14.5_

  - [x] 5.2 Implement `GeneratorAgent.generate()` in `agent.py`
    - Validate `task_description` (non-empty after strip) and `num_candidates` (>= 1), raise `ValueError` if invalid
    - Build system prompt from template with `num_candidates` substituted
    - Build `ToolRegistry` via `build_tool_registry()`
    - Instantiate llm-toolbox `Agent` with name, system_prompt, llm_client, tool_registry, max_iterations
    - Bridge async `agent.run(task_description)` to sync via `asyncio.run()` with running-loop detection fallback
    - Check `AgentResult.timed_out`: if True and answer empty, raise `TimeoutError`; if True and answer non-empty, attempt parse
    - Parse `AgentResult.answer` via `parse_candidates()`
    - Deduplicate candidates, truncate if too many, attempt follow-up run if too few
    - Log key events: call start, agent completion, parse results, errors
    - Wrap any `agent.run()` exception in `RuntimeError` with `__cause__`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 10.1, 10.2, 10.3, 10.4, 11.1, 11.2, 11.3, 12.1, 12.2, 12.3, 14.1, 14.2, 14.3, 14.4_

  - [ ]* 5.3 Write property test: candidate count guarantee (Property 1)
    - **Property 1: Candidate count guarantee**
    - For any valid task description and num_candidates >= 1, `generate()` returns exactly `num_candidates` strings (with mocked Agent)
    - **Validates: Requirements 1.1, 1.2, 4.3**

  - [ ]* 5.4 Write property test: invalid input rejection (Property 2)
    - **Property 2: Invalid input rejection — generate() inputs**
    - For any `num_candidates < 1`, `generate()` raises `ValueError`; for any empty/whitespace task description, `generate()` raises `ValueError`
    - **Validates: Requirements 1.4, 1.5**

  - [ ]* 5.5 Write property test: system prompt includes num_candidates (Property 7)
    - **Property 7: System prompt includes num_candidates**
    - For any positive integer num_candidates, the constructed system prompt contains the string representation of that integer
    - **Validates: Requirements 10.1**

  - [ ]* 5.6 Write property test: output candidates are stripped and unique (Property 8)
    - **Property 8: Output candidates are stripped and unique**
    - For any successful `generate()` call with num_candidates > 1, all returned candidates have no leading/trailing whitespace and are pairwise distinct
    - **Validates: Requirements 11.1, 11.3**

  - [ ]* 5.7 Write property test: agent exceptions wrapped in RuntimeError (Property 9)
    - **Property 9: Agent exceptions wrapped in RuntimeError**
    - For any exception raised by `agent.run()`, `generate()` raises `RuntimeError` whose `__cause__` is the original exception
    - **Validates: Requirements 12.3**

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Wire up exports and create test fixtures
  - [x] 7.1 Wire up `__init__.py` exports
    - Export `GeneratorAgent`, `AgentConfig`, `parse_candidates`, `build_tool_registry`, `DEFAULT_SYSTEM_PROMPT`
    - _Requirements: 1.3_

  - [x] 7.2 Create `tests/test_generator_agent.py` with shared fixtures and unit tests
    - Create mock `LLMClient` fixture, mock `Agent` fixture, sample `AgentResult` factories
    - Write unit tests for: happy-path generate, config defaults, ValueError on bad inputs, TimeoutError on timed-out result, RuntimeError on empty answer, RuntimeError wrapping agent exceptions, logging verification
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 2.1, 2.4, 2.5, 12.1, 12.2, 12.3, 14.1, 14.2, 14.3, 14.4, 14.5_

  - [ ]* 7.3 Write unit tests for answer parser edge cases
    - Test JSON array format, numbered list format, delimiter format, single-candidate fallback
    - Test empty strings, whitespace-only strings, mixed formats
    - Add to `tests/test_generator_agent.py`
    - _Requirements: 4.1, 4.2, 4.4_

  - [ ]* 7.4 Write unit tests for tool functions
    - Test each tool function with mocked LLMClient
    - Test "no results found" fallback for `retrieve_templates` and `search_examples`
    - Add to `tests/test_generator_agent.py`
    - _Requirements: 6.1, 7.1, 7.2, 8.1, 8.2, 9.1_

- [x] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples, edge cases, and logging behavior
- All component interactions use dependency injection for testability
- The llm-toolbox library is a local editable dependency — never test its internals
