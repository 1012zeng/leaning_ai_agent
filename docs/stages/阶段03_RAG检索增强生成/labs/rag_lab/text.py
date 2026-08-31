"""Deterministic text normalization and tokenization helpers."""

from __future__ import annotations

import re

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+|[\u3400-\u4dbf\u4e00-\u9fff]")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
CHUNK_MARKER = re.compile(r"^<!-- chunk: ([a-z0-9][a-z0-9-]*) -->\s*$", re.MULTILINE)


def normalize_text(value: str) -> str:
    """Normalize line endings and remove trailing horizontal whitespace."""

    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in normalized.split("\n")).strip()


def tokens(value: str) -> tuple[str, ...]:
    """Tokenize Latin words and individual CJK code points for offline teaching."""

    return tuple(match.group(0).lower() for match in TOKEN_PATTERN.finditer(value))


def token_spans(value: str) -> tuple[tuple[int, int], ...]:
    """Return code-point spans for the deterministic tokenizer."""

    return tuple((match.start(), match.end()) for match in TOKEN_PATTERN.finditer(value))


def lexical_overlap(left: str, right: str) -> float:
    """Compute a bounded token-set overlap used by the offline reranker."""

    left_tokens = set(tokens(left))
    right_tokens = set(tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens)


def chunk_marker_boundaries(text: str) -> tuple[tuple[str, int, int], ...] | None:
    """Return ``(chunk_key, start, end)`` for each ``<!-- chunk: ... -->`` marker.

    Returns ``None`` when the document carries no explicit markers, so callers can
    fall back to structure-aware heading boundaries. Chunk starts are left-trimmed so
    chunk text begins at the heading that follows each marker.
    """

    markers = list(CHUNK_MARKER.finditer(text))
    if not markers:
        return None
    boundaries: list[tuple[str, int, int]] = []
    for index, marker in enumerate(markers):
        start = marker.end()
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        start = _find_heading_start(text, start)
        chunk_key = marker.group(1)
        boundaries.append((chunk_key, start, end))
    return tuple(boundaries)


def _find_heading_start(text: str, position: int) -> int:
    index = position
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def parse_front_matter(value: str) -> tuple[dict[str, str], str]:
    """Parse the intentionally restricted scalar YAML front matter used by fixtures."""

    if not value.startswith("---\n"):
        return {}, value
    end = value.find("\n---\n", 4)
    if end < 0:
        raise ValueError("front matter is missing closing delimiter")
    metadata: dict[str, str] = {}
    for line in value[4:end].splitlines():
        key, separator, raw_value = line.partition(":")
        if not separator or not key.strip() or not raw_value.strip():
            raise ValueError("front matter only supports non-empty key: value scalars")
        metadata[key.strip()] = raw_value.strip()
    return metadata, value[end + 5 :]
