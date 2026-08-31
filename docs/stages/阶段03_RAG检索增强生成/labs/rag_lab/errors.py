"""Structured stage errors and problem catalog."""

from __future__ import annotations

from rag_lab.ids import uuid7
from rag_lab.models import ProblemDetails, StageName


class StageError(Exception):
    """Exception carrying a safe ProblemDetails payload at an adapter boundary."""

    def __init__(self, problem: ProblemDetails) -> None:
        super().__init__(problem.code)
        self.problem = problem


def problem(
    code: str,
    stage: StageName,
    title: str,
    detail: str,
    status: int,
    *,
    retryable: bool = False,
    item_ref: dict[str, str] | None = None,
) -> ProblemDetails:
    """Build a safe RFC 9457 problem without stack, raw content, or disk paths."""

    slug = code.lower().replace("_", "-")
    return ProblemDetails(
        type=f"https://contracts.example/rag/problems/{slug}",
        title=title,
        status=status,
        detail=detail,
        instance=f"urn:request:{uuid7()}",
        code=code,
        stage=stage,
        retryable=retryable,
        item_ref={} if item_ref is None else item_ref,
    )
