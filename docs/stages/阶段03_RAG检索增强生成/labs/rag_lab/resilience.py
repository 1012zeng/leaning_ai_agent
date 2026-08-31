"""Bounded retry policy for optional remote or model adapters."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from rag_lab.errors import StageError

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Explicit attempt, delay, and operation timeout boundaries."""

    max_attempts: int
    timeout_ms: int
    base_delay_ms: int

    def __post_init__(self) -> None:
        if self.max_attempts < 1 or self.timeout_ms < 1 or self.base_delay_ms < 0:
            raise ValueError("retry policy values are outside supported bounds")


def call_with_retry(
    operation: Callable[[], T],
    policy: RetryPolicy,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Retry only explicitly retryable StageError values within a wall-clock budget."""

    started = time.perf_counter()
    for attempt in range(1, policy.max_attempts + 1):
        try:
            result = operation()
        except StageError as error:
            elapsed_ms = (time.perf_counter() - started) * 1000
            if (
                not error.problem.retryable
                or attempt >= policy.max_attempts
                or elapsed_ms >= policy.timeout_ms
            ):
                raise
            delay_ms = policy.base_delay_ms * (2 ** (attempt - 1))
            if elapsed_ms + delay_ms >= policy.timeout_ms:
                raise
            sleep(delay_ms / 1000)
            continue
        elapsed_ms = (time.perf_counter() - started) * 1000
        if elapsed_ms > policy.timeout_ms:
            raise TimeoutError("operation exceeded configured timeout budget")
        return result
    raise AssertionError("retry loop exhausted without returning or raising")
