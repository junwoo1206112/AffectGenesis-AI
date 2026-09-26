"""Public evidence boundary checks for v2."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import json


FORBIDDEN_PUBLIC_KEYS = frozenset({"audit", "state", "hidden", "tape", "digest", "uniform", "u"})
FORBIDDEN_PUBLIC_VALUES = frozenset({"G", "B"})


def reject_hidden(value: object) -> None:
    """Reject recursively embedded audit fields before writing public JSONL."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            if type(key) is not str or key.lower() in FORBIDDEN_PUBLIC_KEYS:
                raise ValueError("hidden field in public evidence")
            reject_hidden(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            reject_hidden(child)
    elif isinstance(value, str) and value in FORBIDDEN_PUBLIC_VALUES:
        raise ValueError("hidden value in public evidence")


def canonical_public_line(row: Mapping[str, object]) -> str:
    reject_hidden(row)
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
