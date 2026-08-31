"""End-to-end, trace, citation, and deterministic-output tests."""

from __future__ import annotations

import json
import re
from typing import cast

import pytest

from rag_lab.config import LabConfig
from rag_lab.pipeline import OfflineRagPipeline, PipelineResult
from rag_lab.serialization import dumps


def test_offline_pipeline_produces_cited_answer(pipeline_result: PipelineResult) -> None:
    shape = pipeline_result.shape()
    assert shape["source_documents"] == 3
    chunks = shape["chunks"]
    candidates = shape["candidates"]
    assert isinstance(chunks, int) and chunks >= 6
    assert isinstance(candidates, int) and candidates > 0
    assert shape["answer_outcome"] == "answered"
    assert pipeline_result.generation.answer.claims
    assert len(pipeline_result.generation.citations) == len(
        pipeline_result.generation.answer.claims
    )

    chunks_by_id = {chunk.chunk_id: chunk for chunk in pipeline_result.ingestion.chunks}
    answer = pipeline_result.generation.answer
    for citation in pipeline_result.generation.citations:
        chunk = chunks_by_id[citation.chunk_id]
        span = citation.chunk_char_span
        assert chunk.text[span.start : span.end] == citation.quote
        assert citation.source_version_id == chunk.source_version_id
        assert citation.citation_id in answer.citation_ids
    for claim in answer.claims:
        assert answer.text[claim.text_span.start : claim.text_span.end]
        assert claim.citation_ids


def test_domain_results_are_deterministic(
    config: LabConfig, pipeline_result: PipelineResult
) -> None:
    second = OfflineRagPipeline(config).run()
    assert [chunk.chunk_id for chunk in second.ingestion.chunks] == [
        chunk.chunk_id for chunk in pipeline_result.ingestion.chunks
    ]
    assert [candidate.candidate_id for candidate in second.candidates.candidates] == [
        candidate.candidate_id for candidate in pipeline_result.candidates.candidates
    ]
    assert [source.source_state_id for source in second.ingestion.source_documents] == [
        source.source_state_id for source in pipeline_result.ingestion.source_documents
    ]
    assert (
        second.indexing.manifest.index_build_id == pipeline_result.indexing.manifest.index_build_id
    )
    assert second.generation == pipeline_result.generation
    assert (
        second.indexing.manifest.content_checksum
        == pipeline_result.indexing.manifest.content_checksum
    )


def test_trace_is_complete_safe_and_w3c_shaped(pipeline_result: PipelineResult) -> None:
    events = pipeline_result.trace_events
    assert [event.sequence for event in events] == list(range(len(events)))
    assert {event.stage for event in events} == {
        "ingestion",
        "indexing",
        "retrieval",
        "rerank",
        "context",
        "generation",
    }
    assert all(re.fullmatch(r"[0-9a-f]{32}", event.trace_id) for event in events)
    assert all(re.fullmatch(r"[0-9a-f]{16}", event.span_id) for event in events)
    serialized = dumps([event.metrics for event in events])
    assert "番茄" not in serialized
    assert "vector" not in serialized
    completed = [event for event in events if event.event_type == "stage_completed"]
    assert all("duration_ms" in event.metrics for event in completed)
    assert all(event.metrics["estimated_cost_usd"] == 0.0 for event in completed)


def test_domain_mappings_are_runtime_immutable(pipeline_result: PipelineResult) -> None:
    source = pipeline_result.ingestion.source_documents[0]
    metadata = cast(dict[str, object], source.source_metadata)
    with pytest.raises(TypeError):
        metadata["category"] = "mutated"


def test_no_hits_propagate_to_abstention(config: LabConfig) -> None:
    result = OfflineRagPipeline(config).run(query_text="🙂")
    assert result.candidates.candidates == ()
    assert result.ranked_hits.hits == ()
    assert result.context.selected_hits == ()
    assert result.generation.answer.outcome == "insufficient_evidence"
    assert result.generation.citations == ()


def test_output_artifacts_keep_trace_separate(
    config: LabConfig, pipeline_result: PipelineResult
) -> None:
    output_path, trace_path = OfflineRagPipeline(config).write_outputs(pipeline_result)
    output = json.loads(output_path.read_text(encoding="utf-8"))
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    assert output["shape"]["answer_outcome"] == "answered"
    assert len(lines) == len(pipeline_result.trace_events)
    assert all(json.loads(line)["schema_version"] == "1.0.0" for line in lines)
