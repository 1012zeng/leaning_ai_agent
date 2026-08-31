"""Stable ports that keep framework and vendor objects behind adapters."""

from __future__ import annotations

from typing import Protocol

from rag_lab.models import (
    CandidateSet,
    Chunk,
    ContextAssemblyCommand,
    ContextBundle,
    EmbeddingRecord,
    GenerationCommand,
    GenerationResult,
    IndexBuildCommand,
    IndexBuildReport,
    IngestionCommand,
    IngestionReport,
    RankedHitSet,
    RerankCommand,
    RetrievalQuery,
    StageResult,
)


class IngestionPort(Protocol):
    """Parse and chunk source facts without downstream dependencies."""

    def ingest(self, command: IngestionCommand) -> StageResult[IngestionReport]: ...


class IndexingPort(Protocol):
    """Build an immutable vector index manifest."""

    def build(self, command: IndexBuildCommand) -> StageResult[IndexBuildReport]: ...


class RetrievalPort(Protocol):
    """Return channel-specific candidates without fusion."""

    def retrieve(self, query: RetrievalQuery) -> StageResult[CandidateSet]: ...


class RerankPort(Protocol):
    """Fuse and rerank candidates resolved from a pipeline snapshot."""

    def rerank(self, command: RerankCommand) -> StageResult[RankedHitSet]: ...


class ContextAssemblyPort(Protocol):
    """Build a frozen context without calling a generator."""

    def assemble(self, command: ContextAssemblyCommand) -> StageResult[ContextBundle]: ...


class GenerationPort(Protocol):
    """Generate and validate a cited answer from a frozen context."""

    def generate(self, command: GenerationCommand) -> StageResult[GenerationResult]: ...


class EmbeddingPort(Protocol):
    """Replaceable embedding adapter."""

    @property
    def dimension(self) -> int: ...

    def embed(self, chunk: Chunk) -> EmbeddingRecord: ...

    def embed_query(self, text: str) -> tuple[float, ...]: ...


class VectorStorePort(Protocol):
    """Replaceable vector backend with manifest-enforced shape."""

    @property
    def dimension(self) -> int: ...

    def upsert(self, record: EmbeddingRecord) -> None: ...

    def search(
        self, query_vector: tuple[float, ...], limit: int
    ) -> tuple[tuple[str, float], ...]: ...
