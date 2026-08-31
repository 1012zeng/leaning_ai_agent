"""In-memory immutable-object registry for transport-independent ID-only ports."""

from __future__ import annotations

from dataclasses import dataclass, field

from rag_lab.models import (
    Candidate,
    Chunk,
    ContextBundle,
    ParsedDocument,
    RankedHit,
    RetrievalQuery,
    SourceDocument,
)


@dataclass(slots=True)
class PipelineSnapshot:
    """Resolve immutable objects by ID for one pipeline execution."""

    sources: dict[str, SourceDocument] = field(default_factory=dict)
    parsed_documents: dict[str, ParsedDocument] = field(default_factory=dict)
    chunks: dict[str, Chunk] = field(default_factory=dict)
    queries: dict[str, RetrievalQuery] = field(default_factory=dict)
    candidates: dict[str, Candidate] = field(default_factory=dict)
    ranked_hits: dict[str, RankedHit] = field(default_factory=dict)
    context_bundles: dict[str, ContextBundle] = field(default_factory=dict)

    def add_ingestion(
        self,
        sources: tuple[SourceDocument, ...],
        parsed_documents: tuple[ParsedDocument, ...],
        chunks: tuple[Chunk, ...],
    ) -> None:
        """Register one ingestion result without mutating domain objects."""

        self.sources.update((item.source_document_id, item) for item in sources)
        self.parsed_documents.update((item.parsed_document_id, item) for item in parsed_documents)
        self.chunks.update((item.chunk_id, item) for item in chunks)

    def source_for_chunk(self, chunk: Chunk) -> SourceDocument:
        """Resolve the exact source snapshot referenced by a chunk."""

        source = self.sources.get(chunk.source_document_id)
        if source is None or source.source_version_id != chunk.source_version_id:
            raise KeyError(chunk.source_document_id)
        return source
