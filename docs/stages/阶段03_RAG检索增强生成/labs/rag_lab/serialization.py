"""UTF-8 JSON and JSONL serialization for frozen contract objects."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, TypeAlias, cast

JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


def to_jsonable(value: object) -> JsonValue:
    """Convert dataclasses and immutable collections to JSON-compatible values."""

    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Path):
        return value.as_posix()
    if is_dataclass(value) and not isinstance(value, type):
        instance = cast(Any, value)
        return {item.name: to_jsonable(getattr(instance, item.name)) for item in fields(instance)}
    if isinstance(value, Mapping):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            result[key] = to_jsonable(item)
        return result
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [to_jsonable(item) for item in value]
    raise TypeError(f"unsupported JSON value type: {type(value).__name__}")


def dumps(value: object, *, indent: int | None = 2) -> str:
    """Serialize a value as stable UTF-8-friendly JSON text."""

    return json.dumps(
        to_jsonable(value), ensure_ascii=False, sort_keys=True, indent=indent, allow_nan=False
    )


def write_json(path: Path, value: object) -> None:
    """Write one JSON artifact with LF line endings."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{dumps(value)}\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, values: Sequence[object]) -> None:
    """Write append-only event-shaped values as one compact JSON object per line."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [dumps(value, indent=None) for value in values]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")
