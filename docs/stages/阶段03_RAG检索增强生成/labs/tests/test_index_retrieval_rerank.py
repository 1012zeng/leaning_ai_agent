"""Index shape, retrieval filters, score semantics, and rerank fallback tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from rag_lab.config import LabConfig
from rag_lab.errors import StageError
from rag_lab.indexing import HashingEmbedder, InMemoryVectorStore
from rag_lab.models import IndexManifest
from rag_lab.pipeline import OfflineRagPipeline, PipelineResult
from rag_lab.retrieval import HybridRetriever
from rag_lab.snapshot import PipelineSnapshot


def _snapshot(result: PipelineResult) -> PipelineSnapshot:
    snapshot = PipelineSnapshot()
    snapshot.add_ingestion(
        result.ingestion.source_documents,
        result.ingestion.parsed_documents,
        result.ingestion.chunks,
    )
    return snapshot


def _ready_retriever(
    config: LabConfig, result: PipelineResult
) -> tuple[HybridRetriever, PipelineSnapshot]:
    snapshot = _snapshot(result)
    embedder = HashingEmbedder(config.embedding_profile, config.embedding_dimension)
    store = InMemoryVectorStore(config.embedding_dimension)
    for chunk in result.ingestion.chunks:
        store.upsert(embedder.embed(chunk))
    retriever = HybridRetriever(
        snapshot,
        embedder,
        store,
        result.indexing.manifest,
        top_k_per_channel=3,
        min_dense_score=0.05,
    )
    return retriever, snapshot


def test_embedding_and_vector_store_shape(
    config: LabConfig, pipeline_result: PipelineResult
) -> None:
    chunk = pipeline_result.ingestion.chunks[0]
    embedder = HashingEmbedder(config.embedding_profile, 8)
    first = embedder.embed(chunk)
    assert first.vector == embedder.embed(chunk).vector
    assert len(embedder.embed_query("query")) == 8
    store = InMemoryVectorStore(8)
    store.upsert(first)
    assert store.search(first.vector, 1)[0][0] == chunk.chunk_id
    with pytest.raises(StageError) as error:
        InMemoryVectorStore(4).upsert(first)
    assert error.value.problem.code == "EMBEDDING_DIMENSION_MISMATCH"
    with pytest.raises(StageError):
        store.search((0.0,), 1)


def test_filter_operators_and_invalid_filter(
    config: LabConfig, pipeline_result: PipelineResult
) -> None:
    retriever, snapshot = _ready_retriever(config, pipeline_result)
    base = pipeline_result.query
    filters: list[dict[str, object]] = [
        {"field": "category", "operator": "eq", "value": "soup"},
        {"field": "category", "operator": "in", "value": ["soup", "guide"]},
        {"and": [{"field": "category", "operator": "eq", "value": "soup"}]},
        {"or": [{"field": "category", "operator": "eq", "value": "guide"}]},
        {"not": {"field": "category", "operator": "eq", "value": "guide"}},
    ]
    for index, expression in enumerate(filters):
        query = replace(base, query_id=f"query-{index}", filters=expression)
        snapshot.queries[query.query_id] = query
        assert retriever.retrieve(query).status == "success"

    invalid = replace(
        base,
        query_id="bad-query",
        filters={"field": "secret", "operator": "eq", "value": "x"},
    )
    failed = retriever.retrieve(invalid)
    assert failed.status == "failed"
    assert failed.problem is not None and failed.problem.code == "INVALID_FILTER"


def test_retrieval_rejects_non_ready_manifest(
    config: LabConfig, pipeline_result: PipelineResult
) -> None:
    retriever, snapshot = _ready_retriever(config, pipeline_result)
    _ = retriever
    manifest: IndexManifest = replace(pipeline_result.indexing.manifest, state="partial")
    embedder = HashingEmbedder(config.embedding_profile, config.embedding_dimension)
    store = InMemoryVectorStore(config.embedding_dimension)
    not_ready = HybridRetriever(
        snapshot,
        embedder,
        store,
        manifest,
        top_k_per_channel=2,
        min_dense_score=0,
    )
    failed = not_ready.retrieve(pipeline_result.query)
    assert failed.status == "failed"
    assert failed.problem is not None and failed.problem.retryable


def test_rerank_timeout_fallback_and_context_budget(config: LabConfig) -> None:
    degraded = OfflineRagPipeline(config).run(inject_rerank_timeout=True)
    assert degraded.ranked_hits.degraded
    assert all("RERANK_FALLBACK_RRF" in hit.decision_codes for hit in degraded.ranked_hits.hits)
    overflow = OfflineRagPipeline(config).run(token_budget=1)
    assert overflow.context.selected_hits == ()
    assert {warning.code for warning in overflow.context.warnings} >= {
        "CHUNK_EXCEEDS_REMAINING_BUDGET",
        "NO_ELIGIBLE_HITS",
    }
