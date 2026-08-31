"""Basic environment-specific latency benchmark for the offline path."""

from __future__ import annotations

import time
from dataclasses import dataclass

from rag_lab.config import LabConfig
from rag_lab.pipeline import OfflineRagPipeline


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Observed latency distribution without a machine-independent pass claim."""

    iterations: int
    total_ms: float
    mean_ms: float
    p50_ms: float
    p95_ms: float
    queries_per_second: float
    estimated_cost_usd: float


def benchmark(config: LabConfig, iterations: int) -> BenchmarkResult:
    """Measure complete cold in-memory pipeline executions."""

    if iterations < 1:
        raise ValueError("iterations must be positive")
    timings: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        OfflineRagPipeline(config).run()
        timings.append((time.perf_counter() - started) * 1000)
    timings.sort()
    total = sum(timings)
    p50 = timings[min(len(timings) - 1, int((len(timings) - 1) * 0.50))]
    p95 = timings[min(len(timings) - 1, int((len(timings) - 1) * 0.95))]
    return BenchmarkResult(
        iterations=iterations,
        total_ms=round(total, 3),
        mean_ms=round(total / iterations, 3),
        p50_ms=round(p50, 3),
        p95_ms=round(p95, 3),
        queries_per_second=round(iterations / (total / 1000), 3),
        estimated_cost_usd=0.0,
    )
