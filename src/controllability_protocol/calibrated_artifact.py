"""Strict artifacts for the card-free calibrated kernel contract only."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from .calibrated import evaluate_isolated_kernel
from .provenance import verify_next_hypothesis_preregistration


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _evaluate(preregistration_path: Path) -> dict[str, object]:
    verify_next_hypothesis_preregistration(preregistration_path)
    preregistration = json.loads(preregistration_path.read_text(encoding="utf-8"))
    return evaluate_isolated_kernel(preregistration["seeds"], preregistration["trials_per_seed"])


def run(preregistration_path: Path, root: Path) -> int:
    """Write a card-free contract artifact; it is not a regular hypothesis run."""
    root.mkdir(parents=True, exist_ok=False)
    (root / "preregistration.json").write_bytes(preregistration_path.read_bytes())
    (root / "evidence.json").write_bytes(_canonical(_evaluate(preregistration_path)))
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
              for name in ("preregistration.json", "evidence.json")}
    (root / "completion.json").write_bytes(_canonical({"status": "card_free_kernel_contract_completed", "hashes": hashes}))
    return 0


def verify(root: Path) -> int:
    completion = json.loads((root / "completion.json").read_text(encoding="utf-8"))
    if completion.get("status") != "card_free_kernel_contract_completed" or set(completion.get("hashes", {})) != {"preregistration.json", "evidence.json"}:
        raise ValueError("invalid calibrated completion")
    for name, digest in completion["hashes"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError("calibrated hash mismatch")
    expected = _evaluate(root / "preregistration.json")
    if json.loads((root / "evidence.json").read_text(encoding="utf-8")) != expected:
        raise ValueError("calibrated evidence mismatch")
    return 0


def replay(root: Path) -> int:
    verify(root)
    with tempfile.TemporaryDirectory(dir=root.parent) as directory:
        replay_root = Path(directory) / "replay"
        run(root / "preregistration.json", replay_root)
        if (root / "evidence.json").read_bytes() != (replay_root / "evidence.json").read_bytes():
            raise ValueError("calibrated replay mismatch")
    return 0
