"""Unit tests for the exception hierarchy."""

import pytest

from prompt_optimization_orchestrator.exceptions import (
    ComponentError,
    DataIntegrityError,
    DeserializationError,
    OrchestratorError,
    RunNotFoundError,
    ValidationError,
)


@pytest.mark.parametrize(
    "exc_class",
    [ValidationError, DeserializationError, RunNotFoundError, ComponentError, DataIntegrityError],
)
def test_all_exceptions_inherit_from_orchestrator_error(exc_class):
    assert issubclass(exc_class, OrchestratorError)


@pytest.mark.parametrize(
    "exc_class",
    [
        OrchestratorError,
        ValidationError,
        DeserializationError,
        RunNotFoundError,
        ComponentError,
        DataIntegrityError,
    ],
)
def test_exceptions_carry_message(exc_class):
    err = exc_class("something went wrong")
    assert str(err) == "something went wrong"
