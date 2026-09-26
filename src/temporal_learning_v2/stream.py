"""Bounded canonical JSONL writers for v2 evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .evidence import canonical_public_line


class PublicJsonlWriter:
    def __init__(self, path: Path) -> None:
        self._stream = path.open("x", encoding="utf-8", newline="\n")
        self._hash = hashlib.sha256()
        self.rows = 0

    def write(self, row: dict[str, object]) -> None:
        encoded = canonical_public_line(row).encode("utf-8")
        self._stream.write(encoded.decode("utf-8"))
        self._hash.update(encoded)
        self.rows += 1

    def close(self) -> dict[str, object]:
        self._stream.close()
        return {"row_count": self.rows, "sha256": self._hash.hexdigest()}


class RestrictedAuditJsonlWriter:
    def __init__(self, path: Path) -> None:
        self._stream = path.open("x", encoding="utf-8", newline="\n")
        self._hash = hashlib.sha256(); self.rows = 0

    def write(self, row: dict[str, object]) -> None:
        required = {"phase", "seed", "checkpoint", "condition", "model", "episode", "step", "state_before"}
        if set(row) != required or row["phase"] not in ("training", "evaluation") or row["state_before"] not in ("G", "B"):
            raise ValueError("invalid restricted audit row")
        encoded = (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        self._stream.write(encoded.decode("utf-8")); self._hash.update(encoded); self.rows += 1

    def close(self) -> dict[str, object]:
        self._stream.close(); return {"row_count": self.rows, "sha256": self._hash.hexdigest()}
