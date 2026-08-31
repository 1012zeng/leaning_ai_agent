"""Parser, chunk, model invariant, identifier, and config validation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag_lab.config import LabConfig, load_config
from rag_lab.ids import derived_id, hash_values, profile_config_hash, source_document_id
from rag_lab.ingestion import MarkdownIngestion
from rag_lab.models import (
    EmbeddingRecord,
    IngestionCommand,
    ProfileRef,
    RetrievalQuery,
    SourceInput,
    Span,
    StageResult,
)
from rag_lab.text import lexical_overlap, normalize_text, parse_front_matter, token_spans, tokens


def _command(config: LabConfig, *items: SourceInput) -> IngestionCommand:
    return IngestionCommand(
        request_id="0198f900-0a10-7420-88f8-c9bc9876a610",
        idempotency_key="test-ingestion",
        tenant_id=config.tenant_id,
        connector_id="tests",
        items=items,
        parser_profile=config.parser_profile,
        chunk_profile=config.chunk_profile,
        state_effective_at=config.state_effective_at,
    )


def test_structure_aware_ingestion_preserves_spans_and_metadata(config: LabConfig) -> None:
    source = SourceInput(
        "recipe.md",
        "repo://test/recipe.md",
        "recipe",
        "text/markdown",
        b"---\ncategory: soup\n---\n# Soup\n\n## Steps\nBoil water.",
        {},
    )
    result = MarkdownIngestion(20, 2, strict_utf8=True).ingest(_command(config, source))
    assert result.status == "success"
    assert result.data is not None
    report = result.data
    assert report.source_documents[0].source_metadata["category"] == "soup"
    parsed = report.parsed_documents[0]
    assert len(parsed.elements) == 2
    assert [chunk.ordinal for chunk in report.chunks] == list(range(len(report.chunks)))
    for chunk in report.chunks:
        span = chunk.document_char_span
        assert parsed.text[span.start : span.end] == chunk.text


def test_ingestion_partial_success_and_lenient_recovery(config: LabConfig) -> None:
    good = SourceInput("good.md", "repo://good", "good", "text/markdown", b"# Good", {})
    empty = SourceInput("empty.md", "repo://empty", "empty", "text/markdown", b" \n", {})
    partial = MarkdownIngestion(20, 0, strict_utf8=True).ingest(_command(config, good, empty))
    assert partial.status == "partial_success"
    assert partial.data is not None
    assert partial.data.quarantined_count == 1

    malformed = SourceInput("bad.md", "repo://bad", "bad", "text/markdown", b"# A\n\xffvalue", {})
    recovered = MarkdownIngestion(20, 0, strict_utf8=False).ingest(_command(config, malformed))
    assert recovered.status == "success"
    assert recovered.data is not None
    assert recovered.data.parsed_documents[0].replacement_char_count == 1
    assert recovered.data.parsed_documents[0].parse_warnings == ("DECODE_REPLACEMENT_USED",)


def test_text_helpers_cover_restricted_front_matter() -> None:
    metadata, body = parse_front_matter("---\nkind: guide\n---\n# Body")
    assert metadata == {"kind": "guide"}
    assert body == "# Body"
    assert parse_front_matter("plain") == ({}, "plain")
    with pytest.raises(ValueError, match="closing delimiter"):
        parse_front_matter("---\nkind: guide")
    with pytest.raises(ValueError, match="key: value"):
        parse_front_matter("---\nbroken\n---\nbody")
    assert normalize_text(" a  \r\n b \r") == "a\n b"
    assert tokens("RAG检索") == ("rag", "检", "索")
    assert token_spans("A中") == ((0, 1), (1, 2))
    assert lexical_overlap("番茄 鸡蛋", "番茄") > 0
    assert lexical_overlap("🙂", "番茄") == 0


def test_ids_are_length_prefixed_and_profile_sensitive() -> None:
    assert hash_values("ab", "c") != hash_values("a", "bc")
    assert derived_id("chk", "same") == derived_id("chk", "same")
    assert source_document_id("a", "b", "c") != source_document_id("a", "bc", "")
    first = profile_config_hash({"a": 1, "b": 2})
    second = profile_config_hash({"b": 2, "a": 1})
    assert first == second


def test_model_invariants_reject_invalid_shapes(config: LabConfig) -> None:
    with pytest.raises(ValueError, match="span"):
        Span(2, 2)
    with pytest.raises(ValueError, match="config_hash"):
        ProfileRef("profile", "1.0.0", "short")
    with pytest.raises(ValueError, match="profile_version"):
        ProfileRef("profile", "latest", "sha256:" + "a" * 64)
    with pytest.raises(ValueError, match="vector length"):
        EmbeddingRecord(
            "1.0.0",
            "emb_x",
            "chk_x",
            "sv_x",
            config.embedding_profile,
            "hash",
            2,
            "float32",
            True,
            (1.0,),
        )
    with pytest.raises(ValueError, match="top_k"):
        RetrievalQuery(
            "1.0.0",
            "query",
            "tenant",
            "question",
            "question",
            "zh-CN",
            {},
            0,
            config.retrieval_profile,
            "index",
        )
    with pytest.raises(ValueError, match="requires problem"):
        StageResult[object]("request", "failed")


def test_config_rejects_wrong_schema_and_missing_values(config: LabConfig, tmp_path: Path) -> None:
    source_path = config.project_root / "configs/offline.json"
    raw = json.loads(source_path.read_text(encoding="utf-8"))
    raw["schema_version"] = "2.0.0"
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_config(bad_path)


def test_config_rejects_path_escape_and_non_finite_number(
    config: LabConfig, tmp_path: Path
) -> None:
    source_path = config.project_root / "configs/offline.json"
    raw = json.loads(source_path.read_text(encoding="utf-8"))
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    escape_path = config_dir / "escape.json"
    raw["corpus_dir"] = "../outside"
    escape_path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="project root"):
        load_config(escape_path)

    raw["corpus_dir"] = "data/corpus"
    raw["retrieval"]["min_dense_score"] = float("nan")
    non_finite_path = config_dir / "non-finite.json"
    non_finite_path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="finite"):
        load_config(non_finite_path)
