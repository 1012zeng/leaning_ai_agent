"""Fault catalog and bounded retry behavior tests."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from rag_lab.benchmark import benchmark
from rag_lab.config import LabConfig
from rag_lab.errors import StageError, problem
from rag_lab.failures import SCENARIOS, run_failure, run_failures
from rag_lab.resilience import RetryPolicy, call_with_retry


def test_all_failure_scenarios_are_observed(config: LabConfig) -> None:
    results = run_failures(config, "all")
    assert [result.scenario for result in results] == list(SCENARIOS)
    assert all(result.observed for result in results)
    assert all(result.recovery for result in results)


def test_unknown_failure_scenario_is_rejected(config: LabConfig) -> None:
    with pytest.raises(ValueError, match="unknown"):
        run_failure(config, "not-a-scenario")


def test_retry_succeeds_only_for_retryable_problem() -> None:
    attempts = 0

    def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise StageError(
                problem("UPSTREAM_TIMEOUT", "retrieval", "timeout", "retry", 504, retryable=True)
            )
        return "ok"

    delays: list[float] = []
    assert call_with_retry(flaky, RetryPolicy(3, 1000, 1), sleep=delays.append) == "ok"
    assert attempts == 3
    assert delays == [0.001, 0.002]


def test_retry_stops_for_non_retryable_or_exhausted() -> None:
    def operation(retryable: bool) -> Callable[[], str]:
        def fail() -> str:
            raise StageError(problem("FAIL", "indexing", "fail", "safe", 409, retryable=retryable))

        return fail

    with pytest.raises(StageError):
        call_with_retry(operation(False), RetryPolicy(3, 100, 0), sleep=lambda _: None)
    with pytest.raises(StageError):
        call_with_retry(operation(True), RetryPolicy(2, 100, 0), sleep=lambda _: None)
    with pytest.raises(ValueError):
        RetryPolicy(0, 1, 0)


def test_benchmark_reports_cost_placeholder(config: LabConfig) -> None:
    result = benchmark(config, 2)
    assert result.iterations == 2
    assert result.p95_ms >= 0
    assert result.estimated_cost_usd == 0.0
    with pytest.raises(ValueError):
        benchmark(config, 0)
