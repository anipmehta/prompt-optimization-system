"""Tests for shared.async_utils."""

from __future__ import annotations

import pytest

from shared.async_utils import run_async_in_sync


class TestRunAsyncInSync:
    def test_runs_simple_coroutine(self):
        async def coro():
            return 42

        assert run_async_in_sync(coro()) == 42

    def test_propagates_exception(self):
        async def failing():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            run_async_in_sync(failing())

    def test_returns_none_from_void_coroutine(self):
        async def void():
            pass

        assert run_async_in_sync(void()) is None
