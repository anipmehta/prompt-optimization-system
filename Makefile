.PHONY: install test lint typecheck coverage clean all

install:
	pip install -e ".[dev]"

test:
	pytest || test $$? -eq 5

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff check --fix src/ tests/
	ruff format src/ tests/

typecheck:
	mypy src/

coverage:
	pytest --cov --cov-report=term-missing --cov-report=html

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

all: lint typecheck test
