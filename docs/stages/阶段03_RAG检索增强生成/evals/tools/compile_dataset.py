from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0.0"
DATASET_ID = "rag_course_cooking"
CORPUS_VERSION = "corpus-1.0.0"
ANNOTATION = {
    "method": "agent_assisted_manual_curation",
    "guideline_version": "1.0.0",
    "adjudication_status": "accepted_for_course_review",
    "truth_basis": "synthetic_corpus_exact",
}
CHUNK_MARKER = re.compile(r"<!-- chunk: ([a-z0-9][a-z0-9-]*) -->")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def jsonl_bytes(records: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(canonical_json(record) for record in records)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line.strip():
            continue
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: each JSONL row must be an object")
        rows.append(value)
    return rows


def profile_ref(profile_id: str, profile_version: str, config: dict[str, Any]) -> dict[str, str]:
    config_hash = sha256_bytes(
        json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )
    return {
        "profile_id": profile_id,
        "profile_version": profile_version,
        "config_hash": f"sha256:{config_hash}",
    }


PARSER_PROFILE = profile_ref(
    "parser.markdown_identity",
    "1.0.0",
    {"encoding": "utf-8", "newline": "preserve", "normalization": "none"},
)
CHUNK_PROFILE = profile_ref(
    "chunk.marker_sections",
    "1.0.0",
    {
        "marker_pattern": "<!-- chunk: <chunk-key> -->",
        "tokenizer": "unicode_non_whitespace_codepoint",
        "max_chunk_tokens": 4096,
        "trim_outer_whitespace": True,
    },
)


def identity_text(profile: dict[str, str]) -> str:
    return "@".join(
        [profile["profile_id"], profile["profile_version"], profile["config_hash"]]
    )


def derive_id(prefix: str, *values: object) -> str:
    encoded_parts: list[bytes] = []
    for value in values:
        raw = str(value).encode("utf-8")
        encoded_parts.extend([str(len(raw)).encode("ascii"), b":", raw])
    return prefix + sha256_bytes(b"".join(encoded_parts))[:32]


def stable_uuid7(timestamp_text: str, seed: str) -> str:
    timestamp = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00"))
    milliseconds = int(timestamp.timestamp() * 1000)
    if not 0 <= milliseconds < 1 << 48:
        raise ValueError(f"timestamp outside UUIDv7 range: {timestamp_text}")
    random_bits = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest()[:10], "big")
    rand_a = (random_bits >> 62) & 0xFFF
    rand_b = random_bits & ((1 << 62) - 1)
    value = (milliseconds << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return str(uuid.UUID(int=value))


def source_ids(
    namespace: uuid.UUID, connector_id: str, external_source_id: str, content: bytes
) -> tuple[str, str]:
    source_document_id = "src_" + str(
        uuid.uuid5(namespace, f"{connector_id}\n{external_source_id}")
    )
    source_version_id = "sv_" + sha256_bytes(content)[:32]
    return source_document_id, source_version_id


def _trimmed_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def parse_chunks(
    text: str,
    source_document_id: str,
    source_version_id: str,
) -> list[dict[str, Any]]:
    markers = list(CHUNK_MARKER.finditer(text))
    if not markers:
        raise ValueError("corpus document has no explicit chunk marker")

    title_match = re.search(r"^# ([^\n]+)", text, flags=re.MULTILINE)
    if title_match is None:
        raise ValueError("corpus document has no H1 title")
    title = title_match.group(1).strip()
    parsed_document_id = derive_id(
        "pd_", source_version_id, identity_text(PARSER_PROFILE)
    )
    records: list[dict[str, Any]] = []
    for ordinal, marker in enumerate(markers):
        start = marker.end()
        end = markers[ordinal + 1].start() if ordinal + 1 < len(markers) else len(text)
        start, end = _trimmed_span(text, start, end)
        chunk_text = text[start:end]
        heading_match = re.match(r"## ([^\n]+)", chunk_text)
        if heading_match is None:
            raise ValueError(f"chunk {marker.group(1)!r} must start with an H2 heading")
        text_hash = sha256_bytes(chunk_text.encode("utf-8"))
        chunk_id = derive_id(
            "chk_",
            parsed_document_id,
            identity_text(CHUNK_PROFILE),
            ordinal,
            start,
            end,
            text_hash,
        )
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "chunk_key": marker.group(1),
                "chunk_id": chunk_id,
                "parsed_document_id": parsed_document_id,
                "source_document_id": source_document_id,
                "source_version_id": source_version_id,
                "chunk_profile": CHUNK_PROFILE,
                "ordinal": ordinal,
                "text": chunk_text,
                "text_sha256": text_hash,
                "document_char_span": {"start": start, "end": end},
                "token_count": sum(not character.isspace() for character in chunk_text),
                "section_path": [title, heading_match.group(1).strip()],
                "page_refs": [],
            }
        )
    return records


def build_corpus(dataset_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_config = load_json(dataset_dir / "authoring" / "sources.json")
    namespace = uuid.UUID(source_config["dataset_namespace_uuid"])
    tenant_id = source_config["tenant_id"]
    connector_id = source_config["connector_id"]
    corpus: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    for source in source_config["sources"]:
        external_source_id = source["external_source_id"]
        content_path = dataset_dir / external_source_id
        content = content_path.read_bytes()
        text = content.decode("utf-8")
        source_document_id, source_version_id = source_ids(
            namespace, connector_id, external_source_id, content
        )
        state_id = stable_uuid7(
            source["state_effective_at"], f"{source_document_id}\n{source_version_id}"
        )
        corpus.append(
            {
                "schema_version": SCHEMA_VERSION,
                "source_document_id": source_document_id,
                "source_version_id": source_version_id,
                "source_state_id": state_id,
                "state_effective_at": source["state_effective_at"],
                "tenant_id": tenant_id,
                "connector_id": connector_id,
                "external_source_id": external_source_id,
                "source_uri": f"repo://{external_source_id}",
                "display_name": source["display_name"],
                "media_type": "text/markdown",
                "byte_size": len(content),
                "content_sha256": sha256_bytes(content),
                "blob_uri": f"dataset://{DATASET_ID}/{dataset_dir.name}/{external_source_id}",
                "source_metadata": source["source_metadata"],
                "lifecycle_state": "active",
            }
        )
        chunks.extend(
            parse_chunks(text, source_document_id, source_version_id)
        )
    return corpus, chunks


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def build_cases(
    dataset_dir: Path,
    chunks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    chunk_by_key = {record["chunk_key"]: record for record in chunks}
    if len(chunk_by_key) != len(chunks):
        raise ValueError("chunk_key must be unique across the dataset")

    case_specs = load_jsonl(dataset_dir / "authoring" / "cases.jsonl")
    eval_cases: list[dict[str, Any]] = []
    ground_truth: list[dict[str, Any]] = []
    retrieval_labels: list[dict[str, Any]] = []
    for spec in case_specs:
        case_key = spec["case_key"]
        eval_case_id = derive_id("case_", DATASET_ID, case_key)
        all_chunk_keys = _unique(
            [label["chunk_key"] for label in spec["labels"]]
            + [
                key
                for claim in spec["ground_truth"]["required_claims"]
                for key in claim["evidence_chunk_keys"]
            ]
        )
        missing = [key for key in all_chunk_keys if key not in chunk_by_key]
        if missing:
            raise ValueError(f"{case_key}: unknown chunk keys: {missing}")

        source_document_ids = _unique(
            chunk_by_key[key]["source_document_id"] for key in all_chunk_keys
        )
        eval_cases.append(
            {
                "schema_version": SCHEMA_VERSION,
                "eval_case_id": eval_case_id,
                "dataset_id": DATASET_ID,
                "dataset_version": dataset_dir.name,
                "case_key": case_key,
                "split": spec["split"],
                "query": spec["query"],
                "category": spec["category"],
                "difficulty": spec["difficulty"],
                "primary_diagnostic_stage": spec["primary_diagnostic_stage"],
                "tags": _unique(spec["tags"]),
                "provenance": {
                    "authoring_method": ANNOTATION["method"],
                    "truth_basis": ANNOTATION["truth_basis"],
                    "source_chunk_keys": all_chunk_keys,
                    "source_document_ids": source_document_ids,
                    "review_rule_ids": [
                        "AR-SOURCE-01",
                        "AR-CLAIM-02",
                        "AR-NEGATIVE-03",
                        "AR-RESPONSE-04",
                    ],
                    "review_status": ANNOTATION["adjudication_status"],
                },
            }
        )

        truth = spec["ground_truth"]
        reference_citations: list[dict[str, Any]] = []
        for claim in truth["required_claims"]:
            for chunk_key in claim["evidence_chunk_keys"]:
                chunk = chunk_by_key[chunk_key]
                quote = chunk["text"]
                reference_citations.append(
                    {
                        "claim_key": claim["claim_key"],
                        "source_document_id": chunk["source_document_id"],
                        "source_version_id": chunk["source_version_id"],
                        "chunk_id": chunk["chunk_id"],
                        "chunk_char_span": {"start": 0, "end": len(quote)},
                        "quote_sha256": sha256_bytes(quote.encode("utf-8")),
                    }
                )
        ground_truth.append(
            {
                "schema_version": SCHEMA_VERSION,
                "eval_case_id": eval_case_id,
                "dataset_id": DATASET_ID,
                "dataset_version": dataset_dir.name,
                "reference_answer": truth["reference_answer"],
                "required_claims": [
                    {"claim_key": claim["claim_key"], "text": claim["text"]}
                    for claim in truth["required_claims"]
                ],
                "unacceptable_claims": truth["unacceptable_claims"],
                "allow_abstain": truth["allow_abstain"],
                "expected_response_mode": truth["expected_response_mode"],
                "reference_citations": reference_citations,
                "annotation": ANNOTATION,
            }
        )

        for label in spec["labels"]:
            chunk = chunk_by_key[label["chunk_key"]]
            retrieval_labels.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "eval_case_id": eval_case_id,
                    "dataset_id": DATASET_ID,
                    "dataset_version": dataset_dir.name,
                    "source_document_id": chunk["source_document_id"],
                    "source_version_id": chunk["source_version_id"],
                    "chunk_id": chunk["chunk_id"],
                    "relevance_grade": label["relevance_grade"],
                    "supports_claim_keys": label["supports_claim_keys"],
                    "label_role": label["label_role"],
                    "annotation": ANNOTATION,
                }
            )
    return eval_cases, ground_truth, retrieval_labels


def _record_count(path: str, data: bytes) -> int | None:
    if path.endswith(".jsonl"):
        return sum(1 for line in data.splitlines() if line.strip())
    return None


def _manifest_files(dataset_dir: Path, outputs: dict[str, bytes]) -> list[dict[str, Any]]:
    source_files = [
        dataset_dir / "authoring" / "sources.json",
        dataset_dir / "authoring" / "cases.jsonl",
        *sorted((dataset_dir / "corpus" / "documents").rglob("*.md")),
    ]
    record_types = {
        "corpus.jsonl": "SourceDocument",
        "chunks.jsonl": "Chunk",
        "eval_cases.jsonl": "EvalCaseCore",
        "ground_truth.jsonl": "GroundTruthRecord",
        "retrieval_labels.jsonl": "RetrievalLabel",
        "authoring/sources.json": "SourceAuthoringConfig",
        "authoring/cases.jsonl": "EvalCaseAuthoringSpec",
    }
    entries: list[dict[str, Any]] = []
    all_files: dict[str, bytes] = dict(outputs)
    for source_file in source_files:
        relative = source_file.relative_to(dataset_dir).as_posix()
        all_files[relative] = source_file.read_bytes()
    for relative, data in sorted(all_files.items()):
        entry: dict[str, Any] = {
            "path": relative,
            "record_type": record_types.get(relative, "CorpusBlob"),
            "bytes": len(data),
            "sha256": sha256_bytes(data),
        }
        records = _record_count(relative, data)
        if records is not None:
            entry["records"] = records
        entries.append(entry)
    return entries


def build_release(dataset_dir: Path) -> dict[str, bytes]:
    if dataset_dir.name != "1.0.0":
        raise ValueError("this compiler currently publishes dataset version 1.0.0")
    corpus, chunks = build_corpus(dataset_dir)
    eval_cases, ground_truth, retrieval_labels = build_cases(dataset_dir, chunks)
    released_chunks = [
        {key: value for key, value in chunk.items() if key != "chunk_key"}
        for chunk in chunks
    ]
    outputs = {
        "corpus.jsonl": jsonl_bytes(corpus),
        "chunks.jsonl": jsonl_bytes(released_chunks),
        "eval_cases.jsonl": jsonl_bytes(eval_cases),
        "ground_truth.jsonl": jsonl_bytes(ground_truth),
        "retrieval_labels.jsonl": jsonl_bytes(retrieval_labels),
    }
    statistics = {
        "cases": len(eval_cases),
        "sources": len(corpus),
        "chunks": len(released_chunks),
        "retrieval_labels": len(retrieval_labels),
        "by_category": dict(sorted(Counter(row["category"] for row in eval_cases).items())),
        "by_difficulty": dict(
            sorted(Counter(row["difficulty"] for row in eval_cases).items())
        ),
        "by_split": dict(sorted(Counter(row["split"] for row in eval_cases).items())),
        "by_primary_diagnostic_stage": dict(
            sorted(
                Counter(row["primary_diagnostic_stage"] for row in eval_cases).items()
            )
        ),
        "by_expected_response_mode": dict(
            sorted(
                Counter(row["expected_response_mode"] for row in ground_truth).items()
            )
        ),
    }
    source_version_checksum = sha256_bytes(
        ("\n".join(sorted(row["source_version_id"] for row in corpus)) + "\n").encode(
            "utf-8"
        )
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": DATASET_ID,
        "dataset_version": dataset_dir.name,
        "corpus_version": CORPUS_VERSION,
        "contract_major": 1,
        "status": "release_candidate",
        "language": "zh-CN",
        "license": "CC-BY-4.0",
        "files": _manifest_files(dataset_dir, outputs),
        "compatible_profiles": {
            "parser_profiles": [PARSER_PROFILE],
            "chunk_profiles": [CHUNK_PROFILE],
            "required_source_version_ids_checksum": f"sha256:{source_version_checksum}",
        },
        "schema_contract": "../../../schemas/dataset_records.schema.json",
        "metric_contract": "../../../metrics/metric_contract.json",
        "statistics": statistics,
        "provenance": {
            "corpus_kind": "synthetic_chinese_course_fixture",
            "authoring_method": ANNOTATION["method"],
            "truth_basis": ANNOTATION["truth_basis"],
            "automatic_llm_truth_imported": False,
        },
    }
    outputs["manifest.json"] = canonical_json(manifest)
    return outputs


def compare_release(dataset_dir: Path, outputs: dict[str, bytes]) -> list[str]:
    differences: list[str] = []
    for relative, expected in outputs.items():
        path = dataset_dir / relative
        if not path.exists():
            differences.append(f"missing generated file: {relative}")
        elif path.read_bytes() != expected:
            differences.append(f"stale generated file: {relative}")
    return differences


def write_release(dataset_dir: Path, outputs: dict[str, bytes]) -> None:
    for relative, data in outputs.items():
        path = dataset_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def default_dataset_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "datasets" / DATASET_ID / "1.0.0"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile the reviewed RAG evaluation authoring files into a frozen release."
    )
    parser.add_argument("--dataset", type=Path, default=default_dataset_dir())
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write generated release files")
    mode.add_argument("--check", action="store_true", help="check generated files (default)")
    args = parser.parse_args()
    dataset_dir = args.dataset.resolve()
    outputs = build_release(dataset_dir)
    if args.write:
        write_release(dataset_dir, outputs)
        print(f"wrote {len(outputs)} release files for {DATASET_ID}@{dataset_dir.name}")
        return 0
    differences = compare_release(dataset_dir, outputs)
    if differences:
        for difference in differences:
            print(f"ERROR: {difference}")
        return 1
    print(f"release is current: {DATASET_ID}@{dataset_dir.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
