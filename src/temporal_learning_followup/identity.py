"""Source identity for the isolated follow-up evidence contract."""
from __future__ import annotations

import hashlib
from pathlib import Path


def source_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    selected = (root / "temporal_learning_followup", root / "temporal_learning", root / "temporal_experience")
    result: dict[str, str] = {}
    for package in selected:
        for path in sorted(package.rglob("*.py")):
            if not path.is_file() or path.is_symlink():
                raise ValueError("invalid follow-up source path")
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result
