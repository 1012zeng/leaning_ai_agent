"""Reciprocal rank fusion and deterministic lexical reranking."""

from __future__ import annotations

from collections import defaultdict

from rag_lab.errors import problem
from rag_lab.ids import derived_id
from rag_lab.models import (
    Candidate,
    RankedHit,
    RankedHitSet,
    RerankCommand,
    StageResult,
    WarningRecord,
)
from rag_lab.snapshot import PipelineSnapshot
from rag_lab.text import lexical_overlap


class RrfLexicalReranker:
    """Fuse channel ranks and optionally add a transparent lexical score."""

    def __init__(
        self,
        snapshot: PipelineSnapshot,
        *,
        rrf_k: int,
        lexical_weight: float,
        min_context_score: float,
        timeout_ms: int,
        allow_fallback: bool,
        inject_timeout: bool = False,
    ) -> None:
        self._snapshot = snapshot
        self._rrf_k = rrf_k
        self._lexical_weight = lexical_weight
        self._min_context_score = min_context_score
        self._timeout_ms = timeout_ms
        self._allow_fallback = allow_fallback
        self._inject_timeout = inject_timeout

    def rerank(self, command: RerankCommand) -> StageResult[RankedHitSet]:
        """Resolve candidate IDs, RRF by chunk, and preserve component scores."""

        query = self._snapshot.queries.get(command.query_id)
        if query is None:
            missing = problem(
                "CONTRACT_VALIDATION_ERROR",
                "rerank",
                "Query reference does not exist",
                "Rerank must resolve its query from the same pipeline snapshot.",
                400,
            )
            return StageResult(command.request_id, "failed", problem=missing)
        candidates: list[Candidate] = []
        for candidate_id in command.candidate_ids:
            candidate = self._snapshot.candidates.get(candidate_id)
            if candidate is None or candidate.query_id != command.query_id:
                missing = problem(
                    "CONTRACT_VALIDATION_ERROR",
                    "rerank",
                    "Candidate reference does not exist",
                    "Every candidate must belong to the same query snapshot.",
                    400,
                    item_ref={"candidate_id": candidate_id},
                )
                return StageResult(command.request_id, "failed", problem=missing)
            candidates.append(candidate)
        grouped: defaultdict[str, list[Candidate]] = defaultdict(list)
        for candidate in candidates:
            grouped[candidate.chunk_id].append(candidate)
        degraded = self._inject_timeout
        if degraded and not self._allow_fallback:
            timeout = problem(
                "UPSTREAM_TIMEOUT",
                "rerank",
                "Reranker exceeded its timeout",
                f"Rerank budget of {self._timeout_ms} ms was exceeded.",
                504,
                retryable=True,
            )
            return StageResult(command.request_id, "failed", problem=timeout)
        provisional: list[tuple[str, float, float, tuple[str, ...]]] = []
        for chunk_id, typed_candidates in grouped.items():
            rrf_score = sum(
                (1 / (self._rrf_k + candidate.channel_rank) for candidate in typed_candidates),
                0.0,
            )
            lexical = (
                0.0
                if degraded
                else lexical_overlap(query.normalized_text, self._snapshot.chunks[chunk_id].text)
            )
            final_score = rrf_score + self._lexical_weight * lexical
            ids = tuple(sorted(candidate.candidate_id for candidate in typed_candidates))
            provisional.append((chunk_id, rrf_score, final_score, ids))
        provisional.sort(key=lambda item: (-item[2], item[0]))
        hits: list[RankedHit] = []
        for rank, (chunk_id, rrf_score, final_score, candidate_ids) in enumerate(
            provisional[: command.limit], start=1
        ):
            chunk = self._snapshot.chunks[chunk_id]
            source = self._snapshot.source_for_chunk(chunk)
            eligible = final_score >= self._min_context_score
            decision_codes = ["PASSED_THRESHOLD" if eligible else "LOW_CONFIDENCE"]
            if degraded:
                decision_codes.append("RERANK_FALLBACK_RRF")
            hit = RankedHit(
                schema_version="1.0.0",
                ranked_hit_id=derived_id(
                    "hit", command.query_id, chunk_id, command.rerank_profile.identity
                ),
                query_id=command.query_id,
                chunk_id=chunk_id,
                source_document_id=source.source_document_id,
                source_version_id=source.source_version_id,
                candidate_ids=candidate_ids,
                rank=rank,
                final_score=final_score,
                score_components={
                    "rrf": rrf_score,
                    "lexical": final_score - rrf_score,
                },
                rerank_profile=command.rerank_profile,
                eligible_for_context=eligible,
                decision_codes=tuple(decision_codes),
            )
            hits.append(hit)
        result = RankedHitSet(
            command.query_id,
            tuple(hits),
            hits[0].final_score if hits else 0.0,
            degraded=degraded,
        )
        warnings: tuple[WarningRecord, ...] = ()
        if degraded:
            warnings = (
                WarningRecord(
                    "UPSTREAM_TIMEOUT",
                    "rerank",
                    "Lexical reranker timed out; profile allowed RRF-only fallback.",
                ),
            )
        return StageResult(command.request_id, "success", data=result, warnings=warnings)
