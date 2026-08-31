"""Deterministic hashing embedding and in-memory vector index adapter."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Literal

from rag_lab.errors import StageError, problem
from rag_lab.ids import derived_id, hash_values, sha256_text
from rag_lab.models import (
    Chunk,
    EmbeddingRecord,
    IndexBuildCommand,
    IndexBuildReport,
    IndexManifest,
    ItemResult,
    ProfileRef,
    StageResult,
)
from rag_lab.snapshot import PipelineSnapshot
from rag_lab.text import tokens


class HashingEmbedder:
    """Small deterministic feature-hashing adapter for offline contract tests."""

    def __init__(self, profile: ProfileRef, dimension: int, *, normalized: bool = True) -> None:
        if dimension < 1:
            raise ValueError("embedding dimension must be positive")
        self._profile = profile
        self._dimension = dimension
        self._normalized = normalized

    @property
    def dimension(self) -> int:
        """Return the adapter's fixed output dimension."""

        return self._dimension

    def embed(self, chunk: Chunk) -> EmbeddingRecord:
        """Embed a chunk and preserve the exact profile and input hash."""

        vector = self._vector(chunk.text)
        return EmbeddingRecord(
            schema_version="1.0.0",
            embedding_id=derived_id(
                "emb",
                chunk.chunk_id,
                chunk.text_sha256,
                self._profile.identity,
                self._dimension,
                "float32",
                self._normalized,
            ),
            chunk_id=chunk.chunk_id,
            source_version_id=chunk.source_version_id,
            embedding_profile=self._profile,
            input_sha256=chunk.text_sha256,
            dimension=self._dimension,
            dtype="float32",
            normalized=self._normalized,
            vector=vector,
        )

    def embed_query(self, text: str) -> tuple[float, ...]:
        """Embed query text using the same deterministic feature space."""

        return self._vector(text)

    def _vector(self, text: str) -> tuple[float, ...]:
        values = [0.0] * self._dimension
        for token in tokens(text):
            digest = hash_values(token)
            bucket = int(digest[:16], 16) % self._dimension
            sign = 1.0 if int(digest[16:18], 16) % 2 == 0 else -1.0
            values[bucket] += sign
        norm = math.sqrt(sum(value * value for value in values))
        if self._normalized and norm:
            values = [value / norm for value in values]
        return tuple(values)


class InMemoryVectorStore:
    """Manifest-shaped cosine vector backend with strict dimension checks."""

    def __init__(self, dimension: int) -> None:
        if dimension < 1:
            raise ValueError("vector store dimension must be positive")
        self._dimension = dimension
        self._vectors: dict[str, tuple[float, ...]] = {}

    @property
    def dimension(self) -> int:
        """Return the immutable backend dimension."""

        return self._dimension

    def upsert(self, record: EmbeddingRecord) -> None:
        """Insert by deterministic embedding ID after schema validation."""

        if record.dimension != self._dimension:
            raise StageError(
                problem(
                    "EMBEDDING_DIMENSION_MISMATCH",
                    "indexing",
                    "Embedding dimension does not match index",
                    f"Expected {self._dimension} dimensions, received {record.dimension}.",
                    409,
                    item_ref={"chunk_id": record.chunk_id},
                )
            )
        self._vectors[record.chunk_id] = record.vector

    def search(self, query_vector: tuple[float, ...], limit: int) -> tuple[tuple[str, float], ...]:
        """Return stable cosine-ranked chunk IDs and scores."""

        if len(query_vector) != self._dimension:
            raise StageError(
                problem(
                    "EMBEDDING_DIMENSION_MISMATCH",
                    "retrieval",
                    "Query dimension does not match index",
                    f"Expected {self._dimension} dimensions, received {len(query_vector)}.",
                    409,
                )
            )
        scored = [
            (chunk_id, sum(left * right for left, right in zip(query_vector, vector, strict=True)))
            for chunk_id, vector in self._vectors.items()
        ]
        scored.sort(key=lambda item: (-item[1], item[0]))
        return tuple(scored[:limit])


class OfflineIndexing:
    """Indexing port that separates vector generation from successful writes."""

    def __init__(
        self,
        snapshot: PipelineSnapshot,
        embedder: HashingEmbedder,
        store: InMemoryVectorStore,
        chunk_profile: ProfileRef,
    ) -> None:
        self._snapshot = snapshot
        self._embedder = embedder
        self._store = store
        self._chunk_profile = chunk_profile
        self.embeddings: dict[str, EmbeddingRecord] = {}

    def build(self, command: IndexBuildCommand) -> StageResult[IndexBuildReport]:
        """Embed exact chunk IDs, write valid records, and emit an immutable manifest."""

        if command.dimension != self._store.dimension:
            mismatch = problem(
                "EMBEDDING_DIMENSION_MISMATCH",
                "indexing",
                "Configured index dimension does not match backend",
                (
                    f"Index command declares {command.dimension}; backend expects "
                    f"{self._store.dimension}."
                ),
                409,
            )
            return StageResult(command.request_id, "failed", problem=mismatch)
        item_results: list[ItemResult] = []
        embedding_refs: list[str] = []
        source_version_ids: set[str] = set()
        for chunk_id in command.chunk_ids:
            chunk = self._snapshot.chunks.get(chunk_id)
            if chunk is None:
                missing = problem(
                    "CONTRACT_VALIDATION_ERROR",
                    "indexing",
                    "Chunk reference does not exist",
                    "The index build referenced a chunk outside this pipeline snapshot.",
                    400,
                    item_ref={"chunk_id": chunk_id},
                )
                item_results.append(ItemResult(chunk_id, "failed", problem=missing))
                continue
            record = self._embedder.embed(chunk)
            try:
                self._store.upsert(record)
            except StageError as error:
                item_results.append(ItemResult(chunk_id, "failed", problem=error.problem))
                continue
            self.embeddings[record.embedding_id] = record
            embedding_refs.append(record.embedding_id)
            source_version_ids.add(record.source_version_id)
            item_results.append(
                ItemResult(
                    chunk_id,
                    "created",
                    output_refs={"embedding_ids": (record.embedding_id,)},
                )
            )
        indexed = len(embedding_refs)
        expected = len(command.chunk_ids)
        failed = expected - indexed
        coverage = indexed / expected if expected else 0.0
        state: Literal["partial", "ready"] = "ready" if expected and failed == 0 else "partial"
        checksum = sha256_text("\n".join(sorted(embedding_refs)))
        manifest = IndexManifest(
            schema_version="1.0.0",
            index_id=command.index_id,
            index_build_id=command.index_build_id,
            tenant_id=command.tenant_id,
            corpus_version=command.corpus_version,
            chunk_profile=self._chunk_profile,
            embedding_profile=command.embedding_profile,
            dimension=command.dimension,
            metric="cosine",
            filterable_fields=dict.fromkeys(command.filterable_fields, "string"),
            source_version_ids=tuple(sorted(source_version_ids)),
            expected_chunk_count=expected,
            indexed_chunk_count=indexed,
            failed_chunk_count=failed,
            coverage=coverage,
            content_checksum=f"sha256:{checksum}",
            state=state,
        )
        report = IndexBuildReport(manifest, tuple(embedding_refs), tuple(item_results))
        if indexed and failed:
            return StageResult(
                command.request_id,
                "partial_success",
                data=report,
                item_results=tuple(item_results),
            )
        if indexed:
            return StageResult(
                command.request_id, "success", data=report, item_results=tuple(item_results)
            )
        failed_problem = problem(
            "INDEX_WRITE_FAILED",
            "indexing",
            "No embeddings were committed",
            "The index build produced no queryable output.",
            503,
            retryable=True,
        )
        return StageResult(
            command.request_id,
            "failed",
            data=report,
            item_results=tuple(item_results),
            problem=failed_problem,
        )


def term_frequencies(chunks: tuple[Chunk, ...]) -> dict[str, dict[str, int]]:
    """Return per-chunk token frequencies for sparse retrieval and diagnostics."""

    frequencies: dict[str, dict[str, int]] = {}
    for chunk in chunks:
        counts: defaultdict[str, int] = defaultdict(int)
        for token in tokens(chunk.text):
            counts[token] += 1
        frequencies[chunk.chunk_id] = dict(counts)
    return frequencies
