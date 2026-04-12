"""Tests for generator_react_agent.parser."""

from __future__ import annotations

import pytest

from generator_react_agent.parser import parse_candidates


class TestParseCandidates:
    def test_json_array(self):
        answer = '["prompt A", "prompt B", "prompt C"]'
        assert parse_candidates(answer, 3) == ["prompt A", "prompt B", "prompt C"]

    def test_json_array_with_surrounding_text(self):
        answer = 'Here are the candidates:\n["one", "two"]\nDone.'
        assert parse_candidates(answer, 2) == ["one", "two"]

    def test_numbered_list(self):
        answer = "1. First prompt\n2. Second prompt\n3. Third prompt"
        assert parse_candidates(answer, 3) == ["First prompt", "Second prompt", "Third prompt"]

    def test_numbered_list_with_parens(self):
        answer = "1) Alpha\n2) Beta"
        assert parse_candidates(answer, 2) == ["Alpha", "Beta"]

    def test_delimiter_dashes(self):
        answer = "Prompt one\n---\nPrompt two\n---\nPrompt three"
        assert parse_candidates(answer, 3) == ["Prompt one", "Prompt two", "Prompt three"]

    def test_delimiter_equals(self):
        answer = "A\n===\nB"
        assert parse_candidates(answer, 2) == ["A", "B"]

    def test_fallback_single_candidate(self):
        answer = "Just one big prompt here."
        assert parse_candidates(answer, 1) == ["Just one big prompt here."]

    def test_empty_string_raises(self):
        with pytest.raises(RuntimeError, match="empty answer"):
            parse_candidates("", 1)

    def test_whitespace_only_raises(self):
        with pytest.raises(RuntimeError, match="empty answer"):
            parse_candidates("   \n  ", 1)

    def test_strips_whitespace_from_candidates(self):
        answer = '["  padded  ", " also padded "]'
        assert parse_candidates(answer, 2) == ["padded", "also padded"]

    def test_filters_empty_json_entries(self):
        answer = '["good", "", "also good"]'
        assert parse_candidates(answer, 2) == ["good", "also good"]
