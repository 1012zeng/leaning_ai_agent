"""Transport-independent domain models from MUJI-19 contract version 1.0.0."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Generic, Literal, TypeVar, cast

SchemaVersion = Literal["1.0.0"]
StageName = Literal[
    "ingestion", "indexing", "retrieval", "rerank", "context", "generation", "evaluation"
]
StageStatus = Literal["success", "partial_success", "failed"]
ItemStatus = Literal["created", "updated", "unchanged", "failed", "quarantined"]
EventType = Literal["stage_started", "stage_completed", "stage_failed", "retried", "fallback"]
TraceStatus = Literal["ok", "error", "degraded"]
Scalar = str | int | float | bool | None
T = TypeVar("T")
V = TypeVar("V")


def frozen_mapping(value: Mapping[str, V]) -> Mapping[str, V]:
    """Return a defensive, read-only shallow copy of scalar or tuple values."""

    return MappingProxyType(dict(value))


def deep_frozen_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    """Recursively freeze JSON-like mappings and arrays."""

    def freeze(item: object) -> object:
        if isinstance(item, Mapping):
            string_items = {str(key): freeze(child) for key, child in item.items()}
            return MappingProxyType(string_items)
        if isinstance(item, list | tuple):
            return tuple(freeze(child) for child in item)
        return item

    return cast(Mapping[str, object], freeze(value))


def _require_nonempty(value: str, name: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be empty")


def _require_finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class ProfileRef:
    """Immutable identity of an algorithm or adapter configuration."""

    profile_id: str
    profile_version: str
    config_hash: str

    def __post_init__(self) -> None:
        _require_nonempty(self.profile_id, "profile_id")
        if re.fullmatch(r"\d+\.\d+\.\d+", self.profile_version) is None:
            raise ValueError("profile_version must be SemVer major.minor.patch")
        if re.fullmatch(r"sha256:[0-9a-f]{64}", self.config_hash) is None:
            raise ValueError("config_hash must be sha256 plus 64 lowercase hex characters")

    @property
    def identity(self) -> str:
        """Return the stable profile identity used by derived IDs."""

        return f"{self.profile_id}@{self.profile_version}:{self.config_hash}"


@dataclass(frozen=True, slots=True)
class Span:
    """Half-open Unicode code-point interval."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError("span must satisfy 0 <= start < end")


@dataclass(frozen=True, slots=True)
class Element:
    """Structure-aware parsed document element."""

    element_id: str
    kind: str
    text_span: Span
    section_path: tuple[str, ...]
    page: int | None = None


@dataclass(frozen=True, slots=True)
class WarningRecord:
    """Stable machine-readable non-fatal stage warning."""

    code: str
    stage: StageName
    detail: str
    item_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ProblemDetails:
    """RFC 9457-compatible structured failure without stack or secret data."""

    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    stage: StageName
    retryable: bool
    item_ref: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "item_ref", frozen_mapping(self.item_ref))


@dataclass(frozen=True, slots=True)
class ItemResult:
    """Per-item outcome for batch-capable stages."""

    item_key: str
    status: ItemStatus
    output_refs: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    outcome_codes: tuple[str, ...] = ()
    problem: ProblemDetails | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_refs", frozen_mapping(self.output_refs))


@dataclass(frozen=True, slots=True)
class StageResult(Generic[T]):
    """Uniform success, partial success, or failure envelope."""

    request_id: str
    status: StageStatus
    data: T | None = None
    item_results: tuple[ItemResult, ...] = ()
    warnings: tuple[WarningRecord, ...] = ()
    problem: ProblemDetails | None = None

    def __post_init__(self) -> None:
        if self.status == "failed" and self.problem is None:
            raise ValueError("failed StageResult requires problem")
        if self.status == "success" and self.problem is not None:
            raise ValueError("successful StageResult cannot carry top-level problem")


@dataclass(frozen=True, slots=True)
class SourceInput:
    """Local connector fact supplied to ingestion."""

    external_source_id: str
    source_uri: str
    display_name: str
    media_type: str
    content: bytes
    source_metadata: Mapping[str, Scalar]

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_metadata", frozen_mapping(self.source_metadata))


@dataclass(frozen=True, slots=True)
class IngestionCommand:
    """Input to the ingestion port."""

    request_id: str
    idempotency_key: str
    tenant_id: str
    connector_id: str
    items: tuple[SourceInput, ...]
    parser_profile: ProfileRef
    chunk_profile: ProfileRef
    state_effective_at: str


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """Immutable logical-source content and lifecycle snapshot."""

    schema_version: SchemaVersion
    source_document_id: str
    source_version_id: str
    source_state_id: str
    state_effective_at: str
    tenant_id: str
    connector_id: str
    external_source_id: str
    source_uri: str
    display_name: str
    media_type: str
    byte_size: int
    content_sha256: str
    blob_uri: str
    source_metadata: Mapping[str, Scalar]
    lifecycle_state: Literal["active", "tombstoned"] = "active"

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_metadata", frozen_mapping(self.source_metadata))


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Deterministic result of parsing an exact source version."""

    schema_version: SchemaVersion
    parsed_document_id: str
    source_document_id: str
    source_version_id: str
    parser_profile: ProfileRef
    detected_charset: str
    replacement_char_count: int
    text: str
    text_sha256: str
    elements: tuple[Element, ...]
    parse_warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Chunk:
    """Smallest retrievable content unit derived from a parsed document."""

    schema_version: SchemaVersion
    chunk_id: str
    parsed_document_id: str
    source_document_id: str
    source_version_id: str
    chunk_profile: ProfileRef
    ordinal: int
    text: str
    text_sha256: str
    document_char_span: Span
    token_count: int
    section_path: tuple[str, ...]
    page_refs: tuple[int, ...] = ()
    parent_chunk_id: str | None = None

    def __post_init__(self) -> None:
        if self.token_count <= 0:
            raise ValueError("chunk token_count must be positive")


@dataclass(frozen=True, slots=True)
class IngestionReport:
    """Objects and counters produced by ingestion."""

    source_documents: tuple[SourceDocument, ...]
    parsed_documents: tuple[ParsedDocument, ...]
    chunks: tuple[Chunk, ...]
    item_results: tuple[ItemResult, ...]
    discovered_count: int
    created_count: int
    unchanged_count: int
    quarantined_count: int
    failed_count: int
    duplicate_content_groups: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True, slots=True)
class EmbeddingRecord:
    """Vector derived from a chunk under an immutable embedding profile."""

    schema_version: SchemaVersion
    embedding_id: str
    chunk_id: str
    source_version_id: str
    embedding_profile: ProfileRef
    input_sha256: str
    dimension: int
    dtype: Literal["float32", "float16", "int8"]
    normalized: bool
    vector: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.dimension <= 0 or len(self.vector) != self.dimension:
            raise ValueError("embedding vector length must equal positive dimension")
        for value in self.vector:
            _require_finite(value, "embedding value")


@dataclass(frozen=True, slots=True)
class IndexManifest:
    """Immutable vector index build manifest."""

    schema_version: SchemaVersion
    index_id: str
    index_build_id: str
    tenant_id: str
    corpus_version: str
    chunk_profile: ProfileRef
    embedding_profile: ProfileRef
    dimension: int
    metric: Literal["cosine"]
    filterable_fields: Mapping[str, str]
    source_version_ids: tuple[str, ...]
    expected_chunk_count: int
    indexed_chunk_count: int
    failed_chunk_count: int
    coverage: float
    content_checksum: str
    state: Literal["staging", "partial", "ready"]

    def __post_init__(self) -> None:
        object.__setattr__(self, "filterable_fields", frozen_mapping(self.filterable_fields))


@dataclass(frozen=True, slots=True)
class IndexBuildCommand:
    """Input to the indexing port."""

    request_id: str
    idempotency_key: str
    index_build_id: str
    tenant_id: str
    corpus_version: str
    chunk_ids: tuple[str, ...]
    embedding_profile: ProfileRef
    index_profile: ProfileRef
    index_id: str
    dimension: int
    filterable_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndexBuildReport:
    """Manifest and exact embedding references produced by indexing."""

    manifest: IndexManifest
    embedding_refs: tuple[str, ...]
    item_results: tuple[ItemResult, ...]


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """Logical retrieval request preserving original and normalized text."""

    schema_version: SchemaVersion
    query_id: str
    tenant_id: str
    original_text: str
    normalized_text: str
    locale: str
    filters: Mapping[str, object]
    top_k: int
    retrieval_profile: ProfileRef
    index_id: str
    rewrite_steps: tuple[Mapping[str, object], ...] = ()

    def __post_init__(self) -> None:
        _require_nonempty(self.original_text, "original_text")
        _require_nonempty(self.normalized_text, "normalized_text")
        if not 1 <= self.top_k <= 100:
            raise ValueError("top_k must be between 1 and 100")
        object.__setattr__(self, "filters", deep_frozen_mapping(self.filters))
        object.__setattr__(
            self,
            "rewrite_steps",
            tuple(deep_frozen_mapping(step) for step in self.rewrite_steps),
        )


@dataclass(frozen=True, slots=True)
class Candidate:
    """One raw retrieval-channel observation for a chunk."""

    schema_version: SchemaVersion
    candidate_id: str
    query_id: str
    chunk_id: str
    source_version_id: str
    index_id: str
    retrieval_channel: str
    raw_score: float
    score_semantics: Literal["higher_better", "lower_better"]
    score_kind: str
    channel_rank: int
    normalized_score: float | None = None

    def __post_init__(self) -> None:
        _require_finite(self.raw_score, "raw_score")
        if self.channel_rank < 1:
            raise ValueError("channel_rank must start at 1")


@dataclass(frozen=True, slots=True)
class CandidateSet:
    """All channel-specific candidates for one query and index."""

    query_id: str
    index_id: str
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True, slots=True)
class RerankCommand:
    """Input to the rerank port; immutable candidates resolve by ID."""

    request_id: str
    idempotency_key: str
    query_id: str
    candidate_ids: tuple[str, ...]
    rerank_profile: ProfileRef
    limit: int


@dataclass(frozen=True, slots=True)
class RankedHit:
    """Fused and reranked global hit retaining candidate evidence."""

    schema_version: SchemaVersion
    ranked_hit_id: str
    query_id: str
    chunk_id: str
    source_document_id: str
    source_version_id: str
    candidate_ids: tuple[str, ...]
    rank: int
    final_score: float
    score_components: Mapping[str, float]
    rerank_profile: ProfileRef
    eligible_for_context: bool
    decision_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "score_components", frozen_mapping(self.score_components))


@dataclass(frozen=True, slots=True)
class RankedHitSet:
    """Globally ordered hits and profile-defined confidence."""

    query_id: str
    hits: tuple[RankedHit, ...]
    confidence: float
    degraded: bool = False


@dataclass(frozen=True, slots=True)
class ContextAssemblyCommand:
    """Input to context assembly using immutable hit IDs."""

    request_id: str
    idempotency_key: str
    query_id: str
    ranked_hit_ids: tuple[str, ...]
    assembly_profile: ProfileRef
    token_budget: int


@dataclass(frozen=True, slots=True)
class SelectedHit:
    """Rendered hit reference inside a context bundle."""

    ranked_hit_id: str
    chunk_id: str
    render_order: int
    rendered_text_sha256: str


@dataclass(frozen=True, slots=True)
class ContextBundle:
    """Frozen, budgeted evidence passed to generation."""

    schema_version: SchemaVersion
    context_bundle_id: str
    query_id: str
    assembly_profile: ProfileRef
    token_budget: int
    token_count: int
    selected_hits: tuple[SelectedHit, ...]
    rendered_context: str
    context_sha256: str
    warnings: tuple[WarningRecord, ...]


@dataclass(frozen=True, slots=True)
class GenerationCommand:
    """Input to generation using a frozen context bundle ID."""

    request_id: str
    idempotency_key: str
    answer_id: str
    query_id: str
    context_bundle_id: str
    generator_profile: ProfileRef


@dataclass(frozen=True, slots=True)
class Claim:
    """Factual span in an answer and its supporting citations."""

    claim_id: str
    text_span: Span
    citation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Citation:
    """Validated relationship between an answer claim and frozen chunk quote."""

    schema_version: SchemaVersion
    citation_id: str
    answer_id: str
    claim_ids: tuple[str, ...]
    ranked_hit_id: str
    chunk_id: str
    source_document_id: str
    source_version_id: str
    quote: str
    chunk_char_span: Span
    quote_sha256: str
    source_locator: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_locator", deep_frozen_mapping(self.source_locator))


@dataclass(frozen=True, slots=True)
class Answer:
    """Cited answer or explicit insufficient-evidence result."""

    schema_version: SchemaVersion
    answer_id: str
    query_id: str
    context_bundle_id: str
    outcome: Literal["answered", "insufficient_evidence"]
    text: str
    claims: tuple[Claim, ...]
    citation_ids: tuple[str, ...]
    generator_profile: ProfileRef
    finish_reason: Literal["stop", "length", "abstain"]


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Generated answer and separately validated citations."""

    answer: Answer
    citations: tuple[Citation, ...]


@dataclass(frozen=True, slots=True)
class TraceEvent:
    """Append-only stage observation referencing domain objects only by ID."""

    schema_version: SchemaVersion
    event_id: str
    trace_id: str
    span_id: str
    sequence: int
    stage: StageName
    event_type: EventType
    occurred_at: str
    status: TraceStatus
    input_refs: Mapping[str, tuple[str, ...]]
    output_refs: Mapping[str, tuple[str, ...]]
    metrics: Mapping[str, int | float]
    attributes: Mapping[str, str]
    parent_span_id: str | None = None
    problem: ProblemDetails | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_refs", frozen_mapping(self.input_refs))
        object.__setattr__(self, "output_refs", frozen_mapping(self.output_refs))
        object.__setattr__(self, "metrics", frozen_mapping(self.metrics))
        object.__setattr__(self, "attributes", frozen_mapping(self.attributes))
