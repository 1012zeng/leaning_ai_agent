"""Local Markdown parser and structure-aware chunker."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from typing import Literal

from rag_lab.errors import problem
from rag_lab.ids import (
    derived_id,
    deterministic_uuid7,
    sha256_bytes,
    sha256_text,
    source_document_id,
)
from rag_lab.models import (
    Chunk,
    Element,
    IngestionCommand,
    IngestionReport,
    ItemResult,
    ParsedDocument,
    SourceDocument,
    Span,
    StageResult,
)
from rag_lab.text import (
    HEADING_PATTERN,
    chunk_marker_boundaries,
    normalize_text,
    parse_front_matter,
    token_spans,
    tokens,
)


class MarkdownIngestion:
    """Deterministic local ingestion with per-item isolation."""

    def __init__(self, max_chunk_tokens: int, overlap_tokens: int, *, strict_utf8: bool) -> None:
        self._max_chunk_tokens = max_chunk_tokens
        self._overlap_tokens = overlap_tokens
        self._strict_utf8 = strict_utf8

    def ingest(
        self,
        command: IngestionCommand,
        known_versions: Mapping[str, str] | None = None,
    ) -> StageResult[IngestionReport]:
        """Parse and structure-chunk every source, preserving partial outcomes.

        When ``known_versions`` maps ``external_source_id`` to the ``source_version_id``
        produced by a prior ingestion under the same idempotency key, unchanged content
        is reported as ``unchanged`` instead of ``created``. Because all identifiers are
        derived from the content and profile, re-ingesting identical bytes yields the same
        deterministic IDs, so the operation is idempotent.
        """

        prior: Mapping[str, str] = known_versions or {}
        sources: list[SourceDocument] = []
        parsed_documents: list[ParsedDocument] = []
        chunks: list[Chunk] = []
        item_results: list[ItemResult] = []
        content_groups: defaultdict[str, list[str]] = defaultdict(list)
        unchanged_count = 0
        for item in sorted(command.items, key=lambda value: value.external_source_id):
            source = self._source_document(command, item)
            sources.append(source)
            content_groups[source.content_sha256].append(source.source_document_id)
            try:
                parsed = self._parse(source, item.content, command)
                item_chunks = self._chunk(parsed, command)
            except UnicodeDecodeError:
                item_problem = problem(
                    "DECODE_ERROR",
                    "ingestion",
                    "Source bytes are not valid UTF-8",
                    "The strict parser rejected the source bytes.",
                    422,
                    item_ref={"source_document_id": source.source_document_id},
                )
                item_results.append(
                    ItemResult(item.external_source_id, "quarantined", problem=item_problem)
                )
                continue
            except ValueError as error:
                code = str(error)
                if code not in {"EMPTY_DOCUMENT", "CHUNK_TOO_LARGE"}:
                    code = "CONTRACT_VALIDATION_ERROR"
                item_problem = problem(
                    code,
                    "ingestion",
                    "Source could not be converted to contract objects",
                    "The source violated parser or chunk profile constraints.",
                    422,
                    item_ref={"source_document_id": source.source_document_id},
                )
                item_results.append(
                    ItemResult(item.external_source_id, "quarantined", problem=item_problem)
                )
                continue
            parsed_documents.append(parsed)
            chunks.extend(item_chunks)
            output_refs = {
                "source_document_ids": (source.source_document_id,),
                "parsed_document_ids": (parsed.parsed_document_id,),
                "chunk_ids": tuple(chunk.chunk_id for chunk in item_chunks),
            }
            if prior.get(item.external_source_id) == source.source_version_id:
                item_results.append(ItemResult(item.external_source_id, "unchanged", output_refs=output_refs))
                unchanged_count += 1
            else:
                item_results.append(ItemResult(item.external_source_id, "created", output_refs=output_refs))
        duplicate_groups = tuple(
            tuple(sorted(group)) for group in content_groups.values() if len(group) > 1
        )
        quarantined_count = sum(item.status == "quarantined" for item in item_results)
        failed_count = sum(item.status == "failed" for item in item_results)
        created_count = sum(item.status == "created" for item in item_results)
        report = IngestionReport(
            source_documents=tuple(sources),
            parsed_documents=tuple(parsed_documents),
            chunks=tuple(chunks),
            item_results=tuple(item_results),
            discovered_count=len(command.items),
            created_count=created_count,
            unchanged_count=unchanged_count,
            quarantined_count=quarantined_count,
            failed_count=failed_count,
            duplicate_content_groups=duplicate_groups,
        )
        if created_count and (quarantined_count or failed_count):
            status: Literal["success", "partial_success", "unchanged"] = "partial_success"
        elif created_count:
            status = "success"
        elif unchanged_count and not (quarantined_count or failed_count):
            status = "success"
        else:
            top_problem = problem(
                "EMPTY_DOCUMENT",
                "ingestion",
                "No source produced retrievable content",
                "Every source item was quarantined or failed.",
                422,
            )
            return StageResult(
                command.request_id,
                "failed",
                data=report,
                item_results=tuple(item_results),
                problem=top_problem,
            )
        return StageResult(
            command.request_id, status, data=report, item_results=tuple(item_results)
        )

    @staticmethod
    def _source_document(command: IngestionCommand, item: object) -> SourceDocument:
        from rag_lab.models import SourceInput

        if not isinstance(item, SourceInput):
            raise TypeError("ingestion item must be SourceInput")
        digest = sha256_bytes(item.content)
        metadata = dict(item.source_metadata)
        try:
            front_matter, _ = parse_front_matter(item.content.decode("utf-8", errors="replace"))
        except ValueError:
            front_matter = {}
        metadata.update(front_matter)
        source_id = source_document_id(
            command.tenant_id, command.connector_id, item.external_source_id
        )
        return SourceDocument(
            schema_version="1.0.0",
            source_document_id=source_id,
            source_version_id=f"sv_{digest[:32]}",
            source_state_id=deterministic_uuid7(
                command.state_effective_at, source_id, f"sv_{digest[:32]}", "active"
            ),
            state_effective_at=command.state_effective_at,
            tenant_id=command.tenant_id,
            connector_id=command.connector_id,
            external_source_id=item.external_source_id,
            source_uri=item.source_uri,
            display_name=item.display_name,
            media_type=item.media_type,
            byte_size=len(item.content),
            content_sha256=digest,
            blob_uri=f"blob://sha256/{digest}",
            source_metadata=metadata,
        )

    def _parse(
        self, source: SourceDocument, content: bytes, command: IngestionCommand
    ) -> ParsedDocument:
        errors = "strict" if self._strict_utf8 else "replace"
        decoded = content.decode("utf-8", errors=errors)
        replacement_count = decoded.count("\ufffd")
        _, body = parse_front_matter(decoded)
        normalized = normalize_text(body)
        if not normalized.strip():
            raise ValueError("EMPTY_DOCUMENT")
        parsed_id = derived_id("pd", source.source_version_id, command.parser_profile.identity)
        elements: list[Element] = []
        for ordinal, match in enumerate(HEADING_PATTERN.finditer(normalized)):
            elements.append(
                Element(
                    element_id=derived_id("el", parsed_id, ordinal, match.start(), match.end()),
                    kind="heading",
                    text_span=Span(match.start(), match.end()),
                    section_path=(match.group(2).strip(),),
                )
            )
        warnings = ("DECODE_REPLACEMENT_USED",) if replacement_count else ()
        return ParsedDocument(
            schema_version="1.0.0",
            parsed_document_id=parsed_id,
            source_document_id=source.source_document_id,
            source_version_id=source.source_version_id,
            parser_profile=command.parser_profile,
            detected_charset="utf-8",
            replacement_char_count=replacement_count,
            text=normalized,
            text_sha256=sha256_text(normalized),
            elements=tuple(elements),
            parse_warnings=warnings,
        )

    def _chunk(self, parsed: ParsedDocument, command: IngestionCommand) -> tuple[Chunk, ...]:
        markers = chunk_marker_boundaries(parsed.text)
        if markers is not None:
            return self._chunk_by_markers(parsed, command, markers)
        boundaries = self._section_boundaries(parsed.text)
        chunks: list[Chunk] = []
        for start, end, section_path in boundaries:
            for part_start, part_end in self._split_to_budget(parsed.text, start, end):
                text = parsed.text[part_start:part_end]
                count = len(tokens(text))
                if count > self._max_chunk_tokens or len(text.encode("utf-8")) > 65_536:
                    raise ValueError("CHUNK_TOO_LARGE")
                ordinal = len(chunks)
                text_hash = sha256_text(text)
                chunk_id = derived_id(
                    "chk",
                    parsed.parsed_document_id,
                    command.chunk_profile.identity,
                    ordinal,
                    part_start,
                    part_end,
                    text_hash,
                )
                chunks.append(
                    Chunk(
                        schema_version="1.0.0",
                        chunk_id=chunk_id,
                        parsed_document_id=parsed.parsed_document_id,
                        source_document_id=parsed.source_document_id,
                        source_version_id=parsed.source_version_id,
                        chunk_profile=command.chunk_profile,
                        ordinal=ordinal,
                        text=text,
                        text_sha256=text_hash,
                        document_char_span=Span(part_start, part_end),
                        token_count=count,
                        section_path=section_path,
                    )
                )
        if not chunks:
            raise ValueError("EMPTY_DOCUMENT")
        return tuple(chunks)

    @staticmethod
    def _section_boundaries(text: str) -> tuple[tuple[int, int, tuple[str, ...]], ...]:
        headings = list(HEADING_PATTERN.finditer(text))
        if not headings:
            return ((0, len(text), ()),)
        sections: list[tuple[int, int, tuple[str, ...]]] = []
        path: list[str] = []
        if headings[0].start() > 0 and text[: headings[0].start()].strip():
            sections.append((0, headings[0].start(), ()))
        for index, heading in enumerate(headings):
            level = len(heading.group(1))
            path = path[: level - 1]
            path.append(heading.group(2).strip())
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            sections.append((heading.start(), end, tuple(path)))
        return tuple(sections)

    def _chunk_by_markers(
        self,
        parsed: ParsedDocument,
        command: IngestionCommand,
        markers: tuple[tuple[str, int, int], ...],
    ) -> tuple[Chunk, ...]:
        """Chunk a document at explicit ``<!-- chunk: ... -->`` markers.

        Each marker-delimited region must begin with an H2 heading. The section path is
        built from the document H1 title plus that H2 heading, matching the eval dataset's
        chunk catalog so chunk identities line up with the eval manifest.
        """

        title_match = re.search(r"^# ([^\n]+)", parsed.text, flags=re.MULTILINE)
        title = title_match.group(1).strip() if title_match else None
        chunks: list[Chunk] = []
        for ordinal, (chunk_key, start, end) in enumerate(markers):
            text = parsed.text[start:end].strip()
            if not text:
                raise ValueError("EMPTY_DOCUMENT")
            heading_match = re.match(r"## ([^\n]+)", text)
            if heading_match is None:
                raise ValueError(f"chunk {chunk_key!r} must start with an H2 heading")
            section_path = tuple(part for part in (title, heading_match.group(1).strip()) if part)
            count = len(tokens(text))
            if count > self._max_chunk_tokens or len(text.encode("utf-8")) > 65_536:
                raise ValueError("CHUNK_TOO_LARGE")
            text_hash = sha256_text(text)
            chunk_id = derived_id(
                "chk",
                parsed.parsed_document_id,
                command.chunk_profile.identity,
                ordinal,
                start,
                end,
                text_hash,
            )
            chunks.append(
                Chunk(
                    schema_version="1.0.0",
                    chunk_id=chunk_id,
                    parsed_document_id=parsed.parsed_document_id,
                    source_document_id=parsed.source_document_id,
                    source_version_id=parsed.source_version_id,
                    chunk_profile=command.chunk_profile,
                    ordinal=ordinal,
                    text=text,
                    text_sha256=text_hash,
                    document_char_span=Span(start, end),
                    token_count=count,
                    section_path=section_path,
                )
            )
        if not chunks:
            raise ValueError("EMPTY_DOCUMENT")
        return tuple(chunks)

    def _split_to_budget(self, text: str, start: int, end: int) -> tuple[tuple[int, int], ...]:
        spans = token_spans(text[start:end])
        if len(spans) <= self._max_chunk_tokens:
            return ((start, end),)
        result: list[tuple[int, int]] = []
        cursor = 0
        while cursor < len(spans):
            window = spans[cursor : cursor + self._max_chunk_tokens]
            part_start = start + window[0][0]
            part_end = start + window[-1][1]
            result.append((part_start, part_end))
            if cursor + self._max_chunk_tokens >= len(spans):
                break
            cursor += max(1, self._max_chunk_tokens - self._overlap_tokens)
        return tuple(result)
