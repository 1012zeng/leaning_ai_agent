"""Deterministic and interaction identifier helpers."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
import uuid
from collections.abc import Mapping
from datetime import datetime

COURSE_NAMESPACE = uuid.UUID("7d25f31f-ea2c-4d15-9f93-dedfe151873e")


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    """Hash UTF-8 text."""

    return sha256_bytes(value.encode("utf-8"))


def hash_values(*values: object) -> str:
    """Hash values with length-prefix encoding to avoid ambiguous concatenation."""

    digest = hashlib.sha256()
    for value in values:
        encoded = str(value).encode("utf-8")
        digest.update(str(len(encoded)).encode("ascii"))
        digest.update(b":")
        digest.update(encoded)
    return digest.hexdigest()


def derived_id(prefix: str, *values: object) -> str:
    """Build a contract-style deterministic derived identifier."""

    return f"{prefix}_{hash_values(*values)[:32]}"


def source_document_id(tenant_id: str, connector_id: str, external_source_id: str) -> str:
    """Build the stable logical source ID using a tenant-scoped UUIDv5 namespace."""

    tenant_namespace = uuid.uuid5(COURSE_NAMESPACE, tenant_id)
    value = f"{connector_id}\n{external_source_id}"
    return f"src_{uuid.uuid5(tenant_namespace, value)}"


def profile_config_hash(config: Mapping[str, object]) -> str:
    """Hash a profile's immutable canonical JSON configuration."""

    canonical = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{sha256_text(canonical)}"


def uuid7() -> str:
    """Create a UUIDv7 compatible identifier on Python versions before uuid.uuid7."""

    timestamp_ms = time.time_ns() // 1_000_000
    random_bytes = bytearray(secrets.token_bytes(10))
    value = bytearray(timestamp_ms.to_bytes(6, "big") + random_bytes)
    value[6] = (value[6] & 0x0F) | 0x70
    value[8] = (value[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(value)))


def deterministic_uuid7(occurred_at: str, *seed_values: object) -> str:
    """Derive a stable UUIDv7 for replaying the same idempotent logical event."""

    parsed = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
    timestamp_ms = int(parsed.timestamp() * 1000)
    random_part = bytearray(hashlib.sha256(hash_values(*seed_values).encode("ascii")).digest()[:10])
    value = bytearray(timestamp_ms.to_bytes(6, "big") + random_part)
    value[6] = (value[6] & 0x0F) | 0x70
    value[8] = (value[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(value)))


def trace_id() -> str:
    """Create a non-zero W3C TraceId."""

    value = secrets.token_hex(16)
    return value if int(value, 16) else "1".zfill(32)


def span_id() -> str:
    """Create a non-zero W3C SpanId."""

    value = secrets.token_hex(8)
    return value if int(value, 16) else "1".zfill(16)
