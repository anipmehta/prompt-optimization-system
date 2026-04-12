"""Async-to-sync bridge for calling async LLMClient from sync interfaces."""

from __future__ import annotations

import asyncio
import threading
from typing import Any


def run_async_in_sync(coro: Any) -> Any:
    """Run an async coroutine from sync code.

    Tries asyncio.run() first. If an event loop is already running,
    falls back to running in a separate thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # Running loop detected — execute in a new thread
    result: Any = None
    exception: BaseException | None = None

    def _run() -> None:
        nonlocal result, exception
        try:
            result = asyncio.run(coro)
        except Exception as exc:
            exception = exc

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join()

    if exception is not None:
        raise exception
    return result
