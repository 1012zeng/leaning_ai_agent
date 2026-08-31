"""Deterministic extractive generation with mandatory citation validation."""

from __future__ import annotations

from rag_lab.errors import problem
from rag_lab.ids import derived_id, sha256_text
from rag_lab.models import (
    Answer,
    Citation,
    Claim,
    GenerationCommand,
    GenerationResult,
    Span,
    StageResult,
)
from rag_lab.snapshot import PipelineSnapshot


class ExtractiveGroundedGenerator:
    """Offline fixture generator that exposes grounding instead of simulating an LLM."""

    def __init__(self, snapshot: PipelineSnapshot, max_claim_chars: int) -> None:
        self._snapshot = snapshot
        self._max_claim_chars = max_claim_chars

    def generate(self, command: GenerationCommand) -> StageResult[GenerationResult]:
        """Create extractive claims, validate quote spans, or explicitly abstain."""

        bundle = self._snapshot.context_bundles.get(command.context_bundle_id)
        if bundle is None or bundle.query_id != command.query_id:
            missing = problem(
                "CONTRACT_VALIDATION_ERROR",
                "generation",
                "Context bundle reference does not exist",
                "Generation requires a frozen bundle from the same query snapshot.",
                400,
            )
            return StageResult(command.request_id, "failed", problem=missing)
        if not bundle.selected_hits:
            answer = Answer(
                schema_version="1.0.0",
                answer_id=command.answer_id,
                query_id=command.query_id,
                context_bundle_id=command.context_bundle_id,
                outcome="insufficient_evidence",
                text="证据不足，无法回答该问题。",
                claims=(),
                citation_ids=(),
                generator_profile=command.generator_profile,
                finish_reason="abstain",
            )
            return StageResult(command.request_id, "success", data=GenerationResult(answer, ()))
        quote_records: list[tuple[str, str, int, int]] = []
        for selected in bundle.selected_hits[:2]:
            chunk = self._snapshot.chunks[selected.chunk_id]
            quote = self._meaningful_quote(chunk.text)
            start = chunk.text.find(quote)
            if start < 0:
                mismatch = problem(
                    "CITATION_SPAN_MISMATCH",
                    "generation",
                    "Citation quote is not present in the frozen chunk",
                    "The extractive adapter produced a quote that failed span validation.",
                    422,
                    item_ref={"chunk_id": chunk.chunk_id},
                )
                return StageResult(command.request_id, "failed", problem=mismatch)
            quote_records.append((selected.ranked_hit_id, quote, start, start + len(quote)))
        lines = [
            f"证据 {index}：{record[1]}" for index, record in enumerate(quote_records, start=1)
        ]
        answer_text = "\n".join(lines)
        claims: list[Claim] = []
        citations: list[Citation] = []
        search_from = 0
        for index, (ranked_hit_id, quote, start, end) in enumerate(quote_records, start=1):
            answer_start = answer_text.find(quote, search_from)
            answer_end = answer_start + len(quote)
            search_from = answer_end
            claim_id = derived_id("clm", command.answer_id, index, answer_start, answer_end)
            hit = self._snapshot.ranked_hits[ranked_hit_id]
            chunk = self._snapshot.chunks[hit.chunk_id]
            source = self._snapshot.source_for_chunk(chunk)
            quote_hash = sha256_text(quote)
            citation_id = derived_id(
                "cit", command.answer_id, claim_id, chunk.chunk_id, start, end, quote_hash
            )
            claims.append(Claim(claim_id, Span(answer_start, answer_end), (citation_id,)))
            citations.append(
                Citation(
                    schema_version="1.0.0",
                    citation_id=citation_id,
                    answer_id=command.answer_id,
                    claim_ids=(claim_id,),
                    ranked_hit_id=ranked_hit_id,
                    chunk_id=chunk.chunk_id,
                    source_document_id=source.source_document_id,
                    source_version_id=source.source_version_id,
                    quote=quote,
                    chunk_char_span=Span(start, end),
                    quote_sha256=quote_hash,
                    source_locator={
                        "display_name": source.display_name,
                        "section_path": list(chunk.section_path),
                        "pages": list(chunk.page_refs),
                    },
                )
            )
        answer = Answer(
            schema_version="1.0.0",
            answer_id=command.answer_id,
            query_id=command.query_id,
            context_bundle_id=command.context_bundle_id,
            outcome="answered",
            text=answer_text,
            claims=tuple(claims),
            citation_ids=tuple(citation.citation_id for citation in citations),
            generator_profile=command.generator_profile,
            finish_reason="stop",
        )
        return StageResult(
            command.request_id,
            "success",
            data=GenerationResult(answer, tuple(citations)),
        )

    def _meaningful_quote(self, text: str) -> str:
        paragraphs = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        value = max(paragraphs, key=len) if paragraphs else text.strip()
        return value[: self._max_claim_chars]
