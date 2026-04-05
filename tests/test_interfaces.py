"""Unit tests for Protocol interfaces — verify structural subtyping works."""

from prompt_optimization_orchestrator.interfaces import (
    EvaluatorInterface,
    GeneratorInterface,
    SelectorInterface,
)


class FakeGenerator:
    def generate(self, task_description: str, num_candidates: int) -> list[str]:
        return ["candidate"]


class FakeSelector:
    def select(self, candidates: list[str]) -> str:
        return candidates[0]

    def reward(self, score: float) -> None:
        pass


class FakeEvaluator:
    def evaluate(self, candidate: str, task_description: str) -> float:
        return 1.0


def test_fake_generator_satisfies_protocol():
    gen: GeneratorInterface = FakeGenerator()
    assert gen.generate("task", 1) == ["candidate"]


def test_fake_selector_satisfies_protocol():
    sel: SelectorInterface = FakeSelector()
    assert sel.select(["a", "b"]) == "a"
    sel.reward(0.5)  # should not raise


def test_fake_evaluator_satisfies_protocol():
    ev: EvaluatorInterface = FakeEvaluator()
    assert ev.evaluate("candidate", "task") == 1.0
