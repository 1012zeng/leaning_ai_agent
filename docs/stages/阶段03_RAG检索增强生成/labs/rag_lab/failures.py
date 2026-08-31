"""Reproducible fault-injection experiments spanning the required course chapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from rag_lab.config import LabConfig
from rag_lab.errors import StageError
from rag_lab.ids import uuid7
from rag_lab.indexing import HashingEmbedder, InMemoryVectorStore
from rag_lab.ingestion import MarkdownIngestion
from rag_lab.models import IngestionCommand, IngestionReport, SourceInput, StageResult
from rag_lab.pipeline import OfflineRagPipeline


@dataclass(frozen=True, slots=True)
class FailureResult:
    """Expected versus observed behavior and its prescribed recovery."""

    scenario: str
    observed: bool
    expected: str
    actual: str
    recovery: str
    evidence: Mapping[str, object]


SCENARIOS = (
    "empty_document",
    "decode_error",
    "semantic_break",
    "dimension_mismatch",
    "duplicate_documents",
    "filter_false_negative",
    "no_hits",
    "rerank_degradation",
    "context_overflow",
)


def run_failure(config: LabConfig, scenario: str) -> FailureResult:
    """Execute one named fault experiment and check its contract behavior."""

    if scenario == "empty_document":
        empty_result = _ingest_bytes(config, (("empty.md", b" \n\t"),))
        observed = (
            empty_result.status == "failed" and empty_result.item_results[0].status == "quarantined"
        )
        item_problem = empty_result.item_results[0].problem
        code = item_problem.code if item_problem else "missing"
        return FailureResult(
            scenario,
            observed,
            "EMPTY_DOCUMENT quarantines the item and creates no parsed/chunk output",
            (
                f"status={empty_result.status}, "
                f"item_status={empty_result.item_results[0].status}, code={code}"
            ),
            "Provide non-whitespace content; do not retry the identical request automatically.",
            {"problem_code": code, "item_results": len(empty_result.item_results)},
        )
    if scenario == "decode_error":
        hex_path = config.project_root / "data/errors/invalid_utf8.hex"
        invalid = bytes.fromhex(hex_path.read_text().strip())
        decode_result = _ingest_bytes(config, (("invalid.md", invalid),))
        decode_problem = decode_result.item_results[0].problem
        code = decode_problem.code if decode_problem else "missing"
        return FailureResult(
            scenario,
            code == "DECODE_ERROR",
            "Strict UTF-8 parsing quarantines malformed bytes",
            f"code={code}",
            "Correct the source encoding or choose a new lenient parser profile.",
            {"problem_code": code},
        )
    if scenario == "semantic_break":
        text = (config.project_root / "data/errors/semantic_break.md").read_text(encoding="utf-8")
        windows = tuple(text[index : index + 18] for index in range(0, len(text), 18))
        separated = not any("只有在" in window and "才可以" in window for window in windows)
        return FailureResult(
            scenario,
            separated,
            "A fixed character window separates the condition from its conclusion",
            f"window_count={len(windows)}, relation_preserved={not separated}",
            "Use Markdown/paragraph-aware chunks and compare retrieval metrics before publishing.",
            {"window_chars": 18, "windows": windows},
        )
    if scenario == "dimension_mismatch":
        baseline = OfflineRagPipeline(config).run()
        chunk = baseline.ingestion.chunks[0]
        embedder = HashingEmbedder(config.embedding_profile, config.embedding_dimension // 2)
        store = InMemoryVectorStore(config.embedding_dimension)
        code = "missing"
        try:
            store.upsert(embedder.embed(chunk))
        except StageError as error:
            code = error.problem.code
        return FailureResult(
            scenario,
            code == "EMBEDDING_DIMENSION_MISMATCH",
            "A vector with the wrong dimension is rejected before index mutation",
            f"code={code}, expected={store.dimension}, received={embedder.dimension}",
            "Build a new immutable index whose manifest matches the new embedding dimension.",
            {"problem_code": code, "index_dimension": store.dimension},
        )
    if scenario == "duplicate_documents":
        original = (config.project_root / "data/corpus/tomato_egg_soup.md").read_bytes()
        duplicate_result = _ingest_bytes(
            config,
            (("original.md", original), ("copied-location.md", original)),
        )
        report = duplicate_result.data
        group_count = 0 if report is None else len(report.duplicate_content_groups)
        source_count = 0 if report is None else len(report.source_documents)
        return FailureResult(
            scenario,
            duplicate_result.status == "success" and source_count == 2 and group_count == 1,
            "Distinct external sources remain distinct while duplicate bytes are observable",
            f"sources={source_count}, duplicate_groups={group_count}",
            (
                "Keep both logical source IDs unless a versioned dedupe policy explicitly "
                "aliases them."
            ),
            {"source_count": source_count, "duplicate_group_count": group_count},
        )
    if scenario == "filter_false_negative":
        bad_filter: dict[str, object] = {
            "field": "category",
            "operator": "eq",
            "value": "does-not-exist",
        }
        filtered = OfflineRagPipeline(config).run(filters=bad_filter)
        recovered = OfflineRagPipeline(config).run(filters={})
        observed = not filtered.candidates.candidates and bool(recovered.candidates.candidates)
        return FailureResult(
            scenario,
            observed,
            "An over-restrictive valid filter yields no hits without becoming a server error",
            (
                f"filtered={len(filtered.candidates.candidates)}, "
                f"recovered={len(recovered.candidates.candidates)}"
            ),
            (
                "Inspect filter selectivity, relax the caller fact, and rerun with the same "
                "index snapshot."
            ),
            {
                "filtered_candidates": len(filtered.candidates.candidates),
                "recovered_candidates": len(recovered.candidates.candidates),
            },
        )
    if scenario == "no_hits":
        no_hits_result = OfflineRagPipeline(config).run(query_text="🙂")
        observed = (
            not no_hits_result.candidates.candidates
            and no_hits_result.generation.answer.outcome == "insufficient_evidence"
        )
        return FailureResult(
            scenario,
            observed,
            "No hits propagate as an empty CandidateSet and explicit abstention",
            (
                f"candidates={len(no_hits_result.candidates.candidates)}, "
                f"outcome={no_hits_result.generation.answer.outcome}"
            ),
            "Ask a supported question, adjust retrieval profiles, or add reviewed corpus evidence.",
            no_hits_result.shape(),
        )
    if scenario == "rerank_degradation":
        degraded_result = OfflineRagPipeline(config).run(inject_rerank_timeout=True)
        fallback_events = [
            event for event in degraded_result.trace_events if event.event_type == "fallback"
        ]
        return FailureResult(
            scenario,
            degraded_result.ranked_hits.degraded and len(fallback_events) == 1,
            "An allowed timeout fallback preserves RRF results and records degraded trace state",
            (
                f"degraded={degraded_result.ranked_hits.degraded}, "
                f"fallback_events={len(fallback_events)}"
            ),
            "Investigate latency; disable fallback when fused rankings are not acceptable.",
            {
                "decision_codes": [
                    list(hit.decision_codes) for hit in degraded_result.ranked_hits.hits
                ]
            },
        )
    if scenario == "context_overflow":
        overflow_result = OfflineRagPipeline(config).run(token_budget=1)
        warning_codes = [warning.code for warning in overflow_result.context.warnings]
        observed = (
            "CHUNK_EXCEEDS_REMAINING_BUDGET" in warning_codes
            and overflow_result.generation.answer.outcome == "insufficient_evidence"
        )
        return FailureResult(
            scenario,
            observed,
            "Oversized chunks are skipped, never silently truncated, and generation abstains",
            f"warnings={warning_codes}, outcome={overflow_result.generation.answer.outcome}",
            "Increase the budget or create a new smaller-chunk profile and rebuild the index.",
            {
                "warning_codes": warning_codes,
                "token_count": overflow_result.context.token_count,
            },
        )
    raise ValueError(f"unknown failure scenario: {scenario}")


def run_failures(config: LabConfig, scenario: str) -> tuple[FailureResult, ...]:
    """Run one scenario or the complete required failure suite."""

    selected = SCENARIOS if scenario == "all" else (scenario,)
    return tuple(run_failure(config, name) for name in selected)


def _ingest_bytes(
    config: LabConfig, items: tuple[tuple[str, bytes], ...]
) -> StageResult[IngestionReport]:
    sources = tuple(
        SourceInput(
            external_source_id=name,
            source_uri=f"repo://labs/errors/{name}",
            display_name=name,
            media_type="text/markdown",
            content=content,
            source_metadata={},
        )
        for name, content in items
    )
    return MarkdownIngestion(
        config.max_chunk_tokens,
        config.overlap_tokens,
        strict_utf8=config.strict_utf8,
    ).ingest(
        IngestionCommand(
            request_id=uuid7(),
            idempotency_key="failure-fixture",
            tenant_id=config.tenant_id,
            connector_id="failure_fixtures",
            items=sources,
            parser_profile=config.parser_profile,
            chunk_profile=config.chunk_profile,
            state_effective_at=config.state_effective_at,
        )
    )
