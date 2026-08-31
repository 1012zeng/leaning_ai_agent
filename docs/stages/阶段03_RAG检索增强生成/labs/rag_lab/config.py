"""Validated JSON configuration and immutable profile identities."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from rag_lab.ids import profile_config_hash
from rag_lab.models import ProfileRef, deep_frozen_mapping


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{name} must be a JSON object")
    return cast(dict[str, object], value)


def _string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _integer(data: dict[str, object], key: str, minimum: int = 0) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{key} must be an integer >= {minimum}")
    return value


def _number(data: dict[str, object], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{key} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{key} must be finite")
    return result


def _boolean(data: dict[str, object], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be boolean")
    return value


def _profile(data: dict[str, object]) -> ProfileRef:
    profile_id = _string(data, "profile_id")
    profile_version = _string(data, "profile_version")
    immutable_config = {
        key: value for key, value in data.items() if key not in {"profile_id", "profile_version"}
    }
    return ProfileRef(profile_id, profile_version, profile_config_hash(immutable_config))


def _resolve_within(project_root: Path, raw_path: str, name: str) -> Path:
    resolved = (project_root / raw_path).resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError as error:
        raise ValueError(f"{name} must stay inside the labs project root") from error
    return resolved


@dataclass(frozen=True, slots=True)
class LabConfig:
    """Complete validated settings for the deterministic offline pipeline."""

    project_root: Path
    tenant_id: str
    connector_id: str
    state_effective_at: str
    corpus_dir: Path
    output_dir: Path
    parser_profile: ProfileRef
    strict_utf8: bool
    chunk_profile: ProfileRef
    max_chunk_tokens: int
    overlap_tokens: int
    embedding_profile: ProfileRef
    embedding_dimension: int
    embedding_normalized: bool
    index_profile: ProfileRef
    index_id: str
    corpus_version: str
    filterable_fields: tuple[str, ...]
    retrieval_profile: ProfileRef
    top_k_per_channel: int
    min_dense_score: float
    rerank_profile: ProfileRef
    rrf_k: int
    lexical_weight: float
    min_context_score: float
    rerank_timeout_ms: int
    allow_rerank_fallback: bool
    rerank_limit: int
    context_profile: ProfileRef
    token_budget: int
    generator_profile: ProfileRef
    max_claim_chars: int
    query_id: str
    answer_id: str
    query_text: str
    locale: str
    filters: Mapping[str, object]
    query_top_k: int
    max_attempts: int
    timeout_ms: int
    base_delay_ms: int


def load_config(path: Path) -> LabConfig:
    """Load a UTF-8 JSON config and derive immutable profile hashes."""

    raw = cast(object, json.loads(path.read_text(encoding="utf-8")))
    root = _mapping(raw, "config")
    if _string(root, "schema_version") != "1.0.0":
        raise ValueError("only config schema_version 1.0.0 is supported")
    parser = _mapping(root.get("parser"), "parser")
    chunk = _mapping(root.get("chunk"), "chunk")
    embedding = _mapping(root.get("embedding"), "embedding")
    index = _mapping(root.get("index"), "index")
    retrieval = _mapping(root.get("retrieval"), "retrieval")
    rerank = _mapping(root.get("rerank"), "rerank")
    context = _mapping(root.get("context"), "context")
    generator = _mapping(root.get("generator"), "generator")
    query = _mapping(root.get("query"), "query")
    resilience = _mapping(root.get("resilience"), "resilience")
    fields = index.get("filterable_fields")
    if not isinstance(fields, list) or not all(isinstance(value, str) for value in fields):
        raise ValueError("filterable_fields must be an array of strings")
    filters = _mapping(query.get("filters"), "filters")
    project_root = path.resolve().parent.parent
    return LabConfig(
        project_root=project_root,
        tenant_id=_string(root, "tenant_id"),
        connector_id=_string(root, "connector_id"),
        state_effective_at=_string(root, "state_effective_at"),
        corpus_dir=_resolve_within(project_root, _string(root, "corpus_dir"), "corpus_dir"),
        output_dir=_resolve_within(project_root, _string(root, "output_dir"), "output_dir"),
        parser_profile=_profile(parser),
        strict_utf8=_boolean(parser, "strict_utf8"),
        chunk_profile=_profile(chunk),
        max_chunk_tokens=_integer(chunk, "max_tokens", 1),
        overlap_tokens=_integer(chunk, "overlap_tokens"),
        embedding_profile=_profile(embedding),
        embedding_dimension=_integer(embedding, "dimension", 1),
        embedding_normalized=_boolean(embedding, "normalized"),
        index_profile=_profile(index),
        index_id=_string(index, "index_id"),
        corpus_version=_string(index, "corpus_version"),
        filterable_fields=tuple(cast(list[str], fields)),
        retrieval_profile=_profile(retrieval),
        top_k_per_channel=_integer(retrieval, "top_k_per_channel", 1),
        min_dense_score=_number(retrieval, "min_dense_score"),
        rerank_profile=_profile(rerank),
        rrf_k=_integer(rerank, "rrf_k", 1),
        lexical_weight=_number(rerank, "lexical_weight"),
        min_context_score=_number(rerank, "min_context_score"),
        rerank_timeout_ms=_integer(rerank, "timeout_ms", 1),
        allow_rerank_fallback=_boolean(rerank, "allow_fallback"),
        rerank_limit=_integer(rerank, "limit", 1),
        context_profile=_profile(context),
        token_budget=_integer(context, "token_budget", 1),
        generator_profile=_profile(generator),
        max_claim_chars=_integer(generator, "max_claim_chars", 1),
        query_id=_string(query, "query_id"),
        answer_id=_string(query, "answer_id"),
        query_text=_string(query, "text"),
        locale=_string(query, "locale"),
        filters=deep_frozen_mapping(filters),
        query_top_k=_integer(query, "top_k", 1),
        max_attempts=_integer(resilience, "max_attempts", 1),
        timeout_ms=_integer(resilience, "timeout_ms", 1),
        base_delay_ms=_integer(resilience, "base_delay_ms"),
    )
