"""Sparse and dense retrieval with explicit channel candidates."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping

from rag_lab.errors import problem
from rag_lab.ids import derived_id
from rag_lab.indexing import HashingEmbedder, InMemoryVectorStore, term_frequencies
from rag_lab.models import Candidate, CandidateSet, IndexManifest, RetrievalQuery, StageResult
from rag_lab.snapshot import PipelineSnapshot
from rag_lab.text import tokens


class HybridRetriever:
    """Return BM25 and cosine candidates without comparing raw cross-channel scores."""

    def __init__(
        self,
        snapshot: PipelineSnapshot,
        embedder: HashingEmbedder,
        store: InMemoryVectorStore,
        manifest: IndexManifest,
        *,
        top_k_per_channel: int,
        min_dense_score: float,
    ) -> None:
        self._snapshot = snapshot
        self._embedder = embedder
        self._store = store
        self._manifest = manifest
        self._top_k = top_k_per_channel
        self._min_dense_score = min_dense_score

    def retrieve(self, query: RetrievalQuery) -> StageResult[CandidateSet]:
        """Validate filters, then emit stable dense and BM25 channel rankings."""

        if query.index_id != self._manifest.index_id or self._manifest.state != "ready":
            index_problem = problem(
                "INDEX_NOT_READY",
                "retrieval",
                "Requested index is not ready",
                "Retrieval requires the exact ready index manifest.",
                409,
                retryable=True,
            )
            return StageResult(query.query_id, "failed", problem=index_problem)
        try:
            eligible = self._eligible_chunk_ids(query.filters)
        except ValueError as error:
            filter_problem = problem(
                "INVALID_FILTER",
                "retrieval",
                "Filter expression is invalid",
                str(error),
                422,
            )
            return StageResult(query.query_id, "failed", problem=filter_problem)
        dense = [
            item
            for item in self._store.search(
                self._embedder.embed_query(query.normalized_text), len(self._snapshot.chunks)
            )
            if item[0] in eligible and item[1] >= self._min_dense_score
        ][: self._top_k]
        sparse = self._bm25(query.normalized_text, eligible)[: self._top_k]
        candidates: list[Candidate] = []
        for channel, score_kind, ranked in (
            ("dense", "cosine_similarity", dense),
            ("bm25", "bm25", sparse),
        ):
            for rank, (chunk_id, score) in enumerate(ranked, start=1):
                chunk = self._snapshot.chunks[chunk_id]
                candidates.append(
                    Candidate(
                        schema_version="1.0.0",
                        candidate_id=derived_id(
                            "can", query.query_id, query.index_id, channel, chunk_id
                        ),
                        query_id=query.query_id,
                        chunk_id=chunk_id,
                        source_version_id=chunk.source_version_id,
                        index_id=query.index_id,
                        retrieval_channel=channel,
                        raw_score=score,
                        score_semantics="higher_better",
                        score_kind=score_kind,
                        channel_rank=rank,
                        normalized_score=score if channel == "dense" else None,
                    )
                )
        candidate_set = CandidateSet(query.query_id, query.index_id, tuple(candidates))
        return StageResult(query.query_id, "success", data=candidate_set)

    def _eligible_chunk_ids(self, filters: Mapping[str, object]) -> set[str]:
        return {
            chunk.chunk_id
            for chunk in self._snapshot.chunks.values()
            if self._matches(filters, self._snapshot.source_for_chunk(chunk).source_metadata)
        }

    def _matches(self, expression: Mapping[str, object], metadata: Mapping[str, object]) -> bool:
        if not expression:
            return True
        if "and" in expression:
            values = expression["and"]
            if not isinstance(values, list | tuple):
                raise ValueError("and requires an array")
            return all(self._matches_dict(value, metadata) for value in values)
        if "or" in expression:
            values = expression["or"]
            if not isinstance(values, list | tuple):
                raise ValueError("or requires an array")
            return any(self._matches_dict(value, metadata) for value in values)
        if "not" in expression:
            return not self._matches_dict(expression["not"], metadata)
        field = expression.get("field")
        operator = expression.get("operator")
        value = expression.get("value")
        if not isinstance(field, str) or field not in self._manifest.filterable_fields:
            raise ValueError("filter field is not in the index manifest whitelist")
        actual = metadata.get(field)
        if operator == "eq":
            return actual == value
        if operator == "in" and isinstance(value, list | tuple):
            return actual in value
        if (
            operator in {"gte", "lte"}
            and isinstance(actual, int | float)
            and isinstance(value, int | float)
        ):
            return actual >= value if operator == "gte" else actual <= value
        raise ValueError("filter operator and value type are incompatible")

    def _matches_dict(self, value: object, metadata: Mapping[str, object]) -> bool:
        if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
            raise ValueError("nested filter must be an object")
        return self._matches(value, metadata)

    def _bm25(self, query_text: str, eligible: set[str]) -> list[tuple[str, float]]:
        chunks = tuple(
            chunk for chunk in self._snapshot.chunks.values() if chunk.chunk_id in eligible
        )
        if not chunks:
            return []
        frequencies = term_frequencies(chunks)
        query_terms = Counter(tokens(query_text))
        document_count = len(chunks)
        average_length = sum(sum(freq.values()) for freq in frequencies.values()) / document_count
        document_frequency = {
            term: sum(term in frequency for frequency in frequencies.values())
            for term in query_terms
        }
        results: list[tuple[str, float]] = []
        for chunk in chunks:
            frequency = frequencies[chunk.chunk_id]
            length = sum(frequency.values())
            score = 0.0
            for term, query_frequency in query_terms.items():
                tf = frequency.get(term, 0)
                if not tf:
                    continue
                df = document_frequency[term]
                inverse_document_frequency = math.log(1 + (document_count - df + 0.5) / (df + 0.5))
                denominator = tf + 1.5 * (1 - 0.75 + 0.75 * length / average_length)
                score += query_frequency * inverse_document_frequency * (tf * 2.5 / denominator)
            if score > 0:
                results.append((chunk.chunk_id, score))
        results.sort(key=lambda item: (-item[1], item[0]))
        return results
