"""Append-only trace recorder kept outside domain stage implementations."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime

from rag_lab.ids import span_id, trace_id, uuid7
from rag_lab.models import ProblemDetails, StageName, TraceEvent


@dataclass(frozen=True, slots=True)
class StageSpan:
    """Opaque handle for completing or failing one stage span."""

    stage: StageName
    span_id: str
    started_at: float
    input_refs: dict[str, tuple[str, ...]]
    attributes: dict[str, str]


class TraceRecorder:
    """Record safe ID/count/hash-only events for one pipeline execution."""

    def __init__(self) -> None:
        self.trace_id = trace_id()
        self._sequence = 0
        self._events: list[TraceEvent] = []

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        """Return the append-only event sequence."""

        return tuple(self._events)

    def start(
        self,
        stage: StageName,
        input_refs: dict[str, tuple[str, ...]],
        attributes: dict[str, str],
    ) -> StageSpan:
        """Record stage_started and return its span handle."""

        handle = StageSpan(stage, span_id(), time.perf_counter(), input_refs, attributes)
        self._append(handle, "stage_started", "ok", {}, {}, None)
        return handle

    def complete(
        self,
        handle: StageSpan,
        output_refs: dict[str, tuple[str, ...]],
        metrics: dict[str, int | float],
        *,
        degraded: bool = False,
    ) -> None:
        """Record completion with real latency and an explicit zero-cost placeholder."""

        enriched = dict(metrics)
        enriched["duration_ms"] = round((time.perf_counter() - handle.started_at) * 1000, 3)
        enriched["estimated_cost_usd"] = 0.0
        status = "degraded" if degraded else "ok"
        self._append(handle, "stage_completed", status, output_refs, enriched, None)

    def fallback(self, handle: StageSpan, problem_details: ProblemDetails) -> None:
        """Record a visible degraded fallback before stage completion."""

        self._append(handle, "fallback", "degraded", {}, {}, problem_details)

    def fail(self, handle: StageSpan, problem_details: ProblemDetails) -> None:
        """Record a safe structured stage failure."""

        self._append(handle, "stage_failed", "error", {}, {}, problem_details)

    def _append(
        self,
        handle: StageSpan,
        event_type: str,
        status: str,
        output_refs: dict[str, tuple[str, ...]],
        metrics: dict[str, int | float],
        problem_details: ProblemDetails | None,
    ) -> None:
        from typing import cast

        from rag_lab.models import EventType, TraceStatus

        event = TraceEvent(
            schema_version="1.0.0",
            event_id=uuid7(),
            trace_id=self.trace_id,
            span_id=handle.span_id,
            sequence=self._sequence,
            stage=handle.stage,
            event_type=cast(EventType, event_type),
            occurred_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            status=cast(TraceStatus, status),
            input_refs=handle.input_refs,
            output_refs=output_refs,
            metrics=metrics,
            attributes=handle.attributes,
            problem=problem_details,
        )
        self._events.append(event)
        self._sequence += 1
