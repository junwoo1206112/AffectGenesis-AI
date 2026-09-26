"""Package-wide immutable source identity for v2 evidence."""
from __future__ import annotations

import hashlib
from pathlib import Path


def source_hashes(root: Path | None = None) -> dict[str, str]:
    source_root = (Path(__file__).resolve().parents[1] if root is None else root).resolve()
    selected = (source_root / "temporal_learning_v2", source_root / "temporal_learning", source_root / "temporal_experience")
    hashes: dict[str, str] = {}
    for package in selected:
        for path in sorted(package.rglob("*.py")):
            if not path.is_file() or path.is_symlink():
                raise ValueError("invalid source identity path")
            hashes[path.relative_to(source_root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not hashes:
        raise ValueError("missing source identity")
    return hashes
