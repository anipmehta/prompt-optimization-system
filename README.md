# Prompt Optimization Orchestrator

A coordination layer that manages the lifecycle of prompt optimization runs. It ties together three external components in an iterative loop:

1. **Generator** — produces prompt candidates from a task description
2. **Selector** — picks the best candidate using reinforcement learning
3. **Evaluator** — scores prompt quality

Each iteration generates candidates, selects the most promising one, evaluates it, and feeds the score back to the Selector as a reward signal. Over multiple iterations, the Selector learns to pick better prompts.

## Architecture

```
User → Orchestrator → Generator (candidates)
                    → Selector  (pick best)
                    → Evaluator (score it)
                    → Selector  (reward signal)
                    → repeat...
       Orchestrator → User (best prompt + results)
```

## Requirements

- Python >= 3.11

## Setup

```bash
# Install with dev dependencies
make install

# Or manually
pip install -e ".[dev]"
```

## Development

```bash
# Run all checks (lint + typecheck + coverage)
make all

# Individual commands
make test        # Run tests
make lint        # Ruff check + format check
make format      # Auto-fix lint + format
make typecheck   # mypy strict mode
make coverage    # Tests with coverage report (90% threshold)
make clean       # Remove caches and build artifacts
```

## Project Structure

```
src/prompt_optimization_orchestrator/
├── __init__.py       # Package exports
├── exceptions.py    # Exception hierarchy
├── interfaces.py    # Protocol interfaces (Generator, Selector, Evaluator)
└── models.py        # Data models and enums

tests/
├── conftest.py          # Shared fixtures
├── test_exceptions.py   # Exception tests
├── test_interfaces.py   # Protocol interface tests
└── test_models.py       # Data model tests
```

## Component Interfaces

The Orchestrator interacts with external components through Protocol interfaces. Any class matching the method signatures works — no inheritance required.

```python
from prompt_optimization_orchestrator.interfaces import (
    GeneratorInterface,
    SelectorInterface,
    EvaluatorInterface,
)
from prompt_optimization_orchestrator.models import OptimizationConfig

# Implement the interfaces with your own classes
# Then inject them into the Orchestrator
```

## License

Internal project.
