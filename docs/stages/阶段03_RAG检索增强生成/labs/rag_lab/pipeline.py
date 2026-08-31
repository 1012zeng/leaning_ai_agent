"""Explicit offline RAG orchestration with observable intermediate objects."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from rag_lab.config import LabConfig
from rag_lab.context import BudgetedContextAssembler
from rag_lab.errors import StageError
from rag_lab.generation import ExtractiveGroundedGenerator
from rag_lab.ids import deterministic_uuid7, uuid7
from rag_lab.indexing import HashingEmbedder, InMemoryVectorStore, OfflineIndexing
from rag_lab.ingestion import MarkdownIngestion
from rag_lab.models import (
    CandidateSet,
    ContextAssemblyCommand,
    ContextBundle,
    GenerationCommand,
    GenerationResult,
    IndexBuildCommand,
    IndexBuildReport,
    IngestionCommand,
    IngestionReport,
    RankedHitSet,
    RerankCommand,
    RetrievalQuery,
    SourceInput,
    StageResult,
    TraceEvent,
)
from rag_lab.observability import StageSpan, TraceRecorder
from rag_lab.rerank import RrfLexicalReranker
from rag_lab.retrieval import HybridRetriever
from rag_lab.serialization import write_json, write_jsonl
from rag_lab.snapshot import PipelineSnapshot

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """All major immutable objects produced by one offline query."""

    ingestion: IngestionReport
    indexing: IndexBuildReport
    query: RetrievalQuery
    candidates: CandidateSet
    ranked_hits: RankedHitSet
    context: ContextBundle
    generation: GenerationResult
    trace_events: tuple[TraceEvent, ...]

    def shape(self) -> dict[str, int | str | bool]:
        """Return compact stage shapes for teaching and smoke checks."""

        return {
            "source_documents": len(self.ingestion.source_documents),
            "parsed_documents": len(self.ingestion.parsed_documents),
            "chunks": len(self.ingestion.chunks),
            "embeddings": len(self.indexing.embedding_refs),
            "candidates": len(self.candidates.candidates),
            "ranked_hits": len(self.ranked_hits.hits),
            "selected_hits": len(self.context.selected_hits),
            "citations": len(self.generation.citations),
            "trace_events": len(self.trace_events),
            "answer_outcome": self.generation.answer.outcome,
            "rerank_degraded": self.ranked_hits.degraded,
        }


class OfflineRagPipeline:
    """Construct and execute all offline adapters from one validated config."""

    def __init__(self, config: LabConfig) -> None:
        self.config = config

    def run(
        self,
        *,
        query_text: str | None = None,
        filters: Mapping[str, object] | None = None,
        inject_rerank_timeout: bool = False,
        token_budget: int | None = None,
    ) -> PipelineResult:
        """Run ingestion through cited generation with optional teaching faults."""

        config = self.config
        snapshot = PipelineSnapshot()
        trace = TraceRecorder()
        source_inputs = self._load_sources(config.corpus_dir)
        ingestion_span = trace.start(
            "ingestion",
            {"external_source_ids": tuple(item.external_source_id for item in source_inputs)},
            {"parser_profile_id": config.parser_profile.profile_id},
        )
        ingestion_result = MarkdownIngestion(
            config.max_chunk_tokens,
            config.overlap_tokens,
            strict_utf8=config.strict_utf8,
        ).ingest(
            IngestionCommand(
                request_id=uuid7(),
                idempotency_key=f"ingest:{config.connector_id}:{config.corpus_version}",
                tenant_id=config.tenant_id,
                connector_id=config.connector_id,
                items=source_inputs,
                parser_profile=config.parser_profile,
                chunk_profile=config.chunk_profile,
                state_effective_at=config.state_effective_at,
            )
        )
        ingestion = self._unwrap(ingestion_result, trace, ingestion_span)
        snapshot.add_ingestion(
            ingestion.source_documents, ingestion.parsed_documents, ingestion.chunks
        )
        trace.complete(
            ingestion_span,
            {"chunk_ids": tuple(chunk.chunk_id for chunk in ingestion.chunks)},
            {
                "source_count": len(ingestion.source_documents),
                "chunk_count": len(ingestion.chunks),
                "quarantined_count": ingestion.quarantined_count,
            },
        )

        embedder = HashingEmbedder(
            config.embedding_profile,
            config.embedding_dimension,
            normalized=config.embedding_normalized,
        )
        vector_store = InMemoryVectorStore(config.embedding_dimension)
        indexing = OfflineIndexing(snapshot, embedder, vector_store, config.chunk_profile)
        index_span = trace.start(
            "indexing",
            {"chunk_ids": tuple(chunk.chunk_id for chunk in ingestion.chunks)},
            {"embedding_profile_id": config.embedding_profile.profile_id},
        )
        index_result = indexing.build(
            IndexBuildCommand(
                request_id=uuid7(),
                idempotency_key=f"index:{config.index_id}:{config.corpus_version}",
                index_build_id=deterministic_uuid7(
                    config.state_effective_at, config.index_id, config.corpus_version
                ),
                tenant_id=config.tenant_id,
                corpus_version=config.corpus_version,
                chunk_ids=tuple(chunk.chunk_id for chunk in ingestion.chunks),
                embedding_profile=config.embedding_profile,
                index_profile=config.index_profile,
                index_id=config.index_id,
                dimension=config.embedding_dimension,
                filterable_fields=config.filterable_fields,
            )
        )
        index_report = self._unwrap(index_result, trace, index_span)
        trace.complete(
            index_span,
            {"index_ids": (index_report.manifest.index_id,)},
            {
                "indexed_chunk_count": index_report.manifest.indexed_chunk_count,
                "failed_chunk_count": index_report.manifest.failed_chunk_count,
                "coverage": index_report.manifest.coverage,
            },
        )

        query_value = config.query_text if query_text is None else query_text
        query = RetrievalQuery(
            schema_version="1.0.0",
            query_id=config.query_id,
            tenant_id=config.tenant_id,
            original_text=query_value,
            normalized_text=" ".join(query_value.split()),
            locale=config.locale,
            filters=config.filters if filters is None else filters,
            top_k=config.query_top_k,
            retrieval_profile=config.retrieval_profile,
            index_id=config.index_id,
        )
        snapshot.queries[query.query_id] = query
        retrieval_span = trace.start(
            "retrieval",
            {"query_ids": (query.query_id,)},
            {
                "index_id": config.index_id,
                "profile_id": config.retrieval_profile.profile_id,
            },
        )
        retrieval_result = HybridRetriever(
            snapshot,
            embedder,
            vector_store,
            index_report.manifest,
            top_k_per_channel=config.top_k_per_channel,
            min_dense_score=config.min_dense_score,
        ).retrieve(query)
        candidates = self._unwrap(retrieval_result, trace, retrieval_span)
        snapshot.candidates.update(
            (candidate.candidate_id, candidate) for candidate in candidates.candidates
        )
        trace.complete(
            retrieval_span,
            {"candidate_ids": tuple(candidate.candidate_id for candidate in candidates.candidates)},
            {
                "candidate_count": len(candidates.candidates),
                "dense_count": sum(
                    candidate.retrieval_channel == "dense" for candidate in candidates.candidates
                ),
                "sparse_count": sum(
                    candidate.retrieval_channel == "bm25" for candidate in candidates.candidates
                ),
            },
        )

        rerank_span = trace.start(
            "rerank",
            {"candidate_ids": tuple(candidate.candidate_id for candidate in candidates.candidates)},
            {"profile_id": config.rerank_profile.profile_id},
        )
        rerank_result = RrfLexicalReranker(
            snapshot,
            rrf_k=config.rrf_k,
            lexical_weight=config.lexical_weight,
            min_context_score=config.min_context_score,
            timeout_ms=config.rerank_timeout_ms,
            allow_fallback=config.allow_rerank_fallback,
            inject_timeout=inject_rerank_timeout,
        ).rerank(
            RerankCommand(
                request_id=uuid7(),
                idempotency_key=f"rerank:{query.query_id}:{config.rerank_profile.config_hash}",
                query_id=query.query_id,
                candidate_ids=tuple(candidate.candidate_id for candidate in candidates.candidates),
                rerank_profile=config.rerank_profile,
                limit=config.rerank_limit,
            )
        )
        ranked_hits = self._unwrap(rerank_result, trace, rerank_span)
        snapshot.ranked_hits.update((hit.ranked_hit_id, hit) for hit in ranked_hits.hits)
        if ranked_hits.degraded and rerank_result.warnings:
            fallback_problem = rerank_result.warnings[0]
            from rag_lab.errors import problem

            trace.fallback(
                rerank_span,
                problem(
                    fallback_problem.code,
                    "rerank",
                    "Reranker timed out",
                    fallback_problem.detail,
                    504,
                    retryable=True,
                ),
            )
        trace.complete(
            rerank_span,
            {"ranked_hit_ids": tuple(hit.ranked_hit_id for hit in ranked_hits.hits)},
            {
                "hits_count": len(ranked_hits.hits),
                "eligible_count": sum(hit.eligible_for_context for hit in ranked_hits.hits),
            },
            degraded=ranked_hits.degraded,
        )

        context_span = trace.start(
            "context",
            {"ranked_hit_ids": tuple(hit.ranked_hit_id for hit in ranked_hits.hits)},
            {"profile_id": config.context_profile.profile_id},
        )
        context_result = BudgetedContextAssembler(snapshot).assemble(
            ContextAssemblyCommand(
                request_id=uuid7(),
                idempotency_key=f"context:{query.query_id}:{config.context_profile.config_hash}",
                query_id=query.query_id,
                ranked_hit_ids=tuple(hit.ranked_hit_id for hit in ranked_hits.hits),
                assembly_profile=config.context_profile,
                token_budget=config.token_budget if token_budget is None else token_budget,
            )
        )
        context_bundle = self._unwrap(context_result, trace, context_span)
        snapshot.context_bundles[context_bundle.context_bundle_id] = context_bundle
        trace.complete(
            context_span,
            {"context_bundle_ids": (context_bundle.context_bundle_id,)},
            {
                "token_count": context_bundle.token_count,
                "selected_count": len(context_bundle.selected_hits),
                "dropped_count": sum(
                    warning.code == "CHUNK_EXCEEDS_REMAINING_BUDGET"
                    for warning in context_bundle.warnings
                ),
            },
        )

        generation_span = trace.start(
            "generation",
            {"context_bundle_ids": (context_bundle.context_bundle_id,)},
            {"profile_id": config.generator_profile.profile_id},
        )
        generation_result = ExtractiveGroundedGenerator(snapshot, config.max_claim_chars).generate(
            GenerationCommand(
                request_id=uuid7(),
                idempotency_key=f"answer:{config.answer_id}",
                answer_id=config.answer_id,
                query_id=query.query_id,
                context_bundle_id=context_bundle.context_bundle_id,
                generator_profile=config.generator_profile,
            )
        )
        generation = self._unwrap(generation_result, trace, generation_span)
        trace.complete(
            generation_span,
            {
                "answer_ids": (generation.answer.answer_id,),
                "citation_ids": tuple(citation.citation_id for citation in generation.citations),
            },
            {
                "citation_count": len(generation.citations),
                "claim_count": len(generation.answer.claims),
                "abstained": int(generation.answer.outcome == "insufficient_evidence"),
            },
        )
        return PipelineResult(
            ingestion,
            index_report,
            query,
            candidates,
            ranked_hits,
            context_bundle,
            generation,
            trace.events,
        )

    def write_outputs(self, result: PipelineResult) -> tuple[Path, Path]:
        """Write reproducible domain output separately from variable trace observations."""

        output_path = self.config.output_dir / "latest.json"
        trace_path = self.config.output_dir / "trace.jsonl"
        payload = {
            "schema_version": "1.0.0",
            "shape": result.shape(),
            "ingestion": result.ingestion,
            "indexing": result.indexing,
            "query": result.query,
            "candidates": result.candidates,
            "ranked_hits": result.ranked_hits,
            "context": result.context,
            "generation": result.generation,
        }
        write_json(output_path, payload)
        write_jsonl(trace_path, result.trace_events)
        return output_path, trace_path

    @staticmethod
    def _load_sources(corpus_dir: Path) -> tuple[SourceInput, ...]:
        inputs: list[SourceInput] = []
        paths = sorted(corpus_dir.rglob("*.md"))
        if len(paths) > 1000:
            raise ValueError("corpus_dir exceeds the 1000-document teaching limit")
        for path in paths:
            if path.stat().st_size > 1_000_000:
                raise ValueError("source exceeds the 1 MB teaching limit")
            relative = path.relative_to(corpus_dir).as_posix()
            inputs.append(
                SourceInput(
                    external_source_id=relative,
                    source_uri=f"repo://labs/corpus/{relative}",
                    display_name=path.stem,
                    media_type="text/markdown",
                    content=path.read_bytes(),
                    source_metadata={},
                )
            )
        if not inputs:
            raise ValueError("corpus_dir contains no Markdown source")
        return tuple(inputs)

    @staticmethod
    def _unwrap(result: StageResult[T], trace: TraceRecorder, span: StageSpan) -> T:
        if result.status == "failed" or result.data is None:
            if result.problem is None:
                raise ValueError("failed stage omitted ProblemDetails")
            trace.fail(span, result.problem)
            raise StageError(result.problem)
        return result.data
