---
inclusion: auto
---

# Testing & Development Guidelines

## Branching
- All changes go out in a separate branch, never commit directly to main.
- Create a new branch for every task execution. Pull main before branching.

## Quality Checks
- Before committing, always run `make all` (lint + typecheck + coverage).
- Coverage threshold is 90%. Do not push code below that.
- Write unit tests only. Integration tests are done separately.
- Every new line of production code must have corresponding unit test coverage.
- Follow DRY in test code — share fixtures, helpers, and setup logic. Don't duplicate.
- Only test our own code. Do not test library utilities or third-party dependencies.
- Test the new code we add, nothing more, nothing less.
- Keep tests for a module in a single test file (e.g., all Orchestrator tests in test_orchestrator.py).
