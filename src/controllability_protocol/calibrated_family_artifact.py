"""Strict temporary artifacts for an approved non-text calibrated signal family."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from .calibrated import evaluate_isolated_kernel, summarize_calibrated_evidence
from .provenance import verify_calibrated_card_family, verify_next_hypothesis_preregistration


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _expected(preregistration_path: Path, family_path: Path, source_review_path: Path) -> dict[str, object]:
    verify_next_hypothesis_preregistration(preregistration_path)
    verify_calibrated_card_family(family_path, source_review_path)
    preregistration = json.loads(preregistration_path.read_text(encoding="utf-8"))
    evidence = evaluate_isolated_kernel(preregistration["seeds"], preregistration["trials_per_seed"])
    if "ci95_multiplier" in preregistration["acceptance"]:
        evidence["criterion"] = summarize_calibrated_evidence(evidence, preregistration["acceptance"])
    evidence["family_sha256"] = hashlib.sha256(family_path.read_bytes()).hexdigest()
    evidence["source_review_sha256"] = hashlib.sha256(source_review_path.read_bytes()).hexdigest()
    return evidence


def run(preregistration_path: Path, family_path: Path, source_review_path: Path, root: Path) -> int:
    root.mkdir(parents=True, exist_ok=False)
    (root / "preregistration.json").write_bytes(preregistration_path.read_bytes())
    (root / "family.json").write_bytes(family_path.read_bytes())
    (root / "source_review.json").write_bytes(source_review_path.read_bytes())
    (root / "evidence.json").write_bytes(_canonical(_expected(preregistration_path, family_path, source_review_path)))
    names = ("preregistration.json", "family.json", "source_review.json", "evidence.json")
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
    (root / "completion.json").write_bytes(_canonical({"status": "isolated_calibrated_family_contract_completed", "hashes": hashes}))
    return 0


def verify(root: Path) -> int:
    completion = json.loads((root / "completion.json").read_text(encoding="utf-8"))
    names = {"preregistration.json", "family.json", "source_review.json", "evidence.json"}
    if completion.get("status") != "isolated_calibrated_family_contract_completed" or set(completion.get("hashes", {})) != names:
        raise ValueError("invalid calibrated family completion")
    for name, digest in completion["hashes"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError("calibrated family hash mismatch")
    expected = _expected(root / "preregistration.json", root / "family.json", root / "source_review.json")
    if json.loads((root / "evidence.json").read_text(encoding="utf-8")) != expected:
        raise ValueError("calibrated family evidence mismatch")
    return 0


def replay(root: Path) -> int:
    verify(root)
    with tempfile.TemporaryDirectory(dir=root.parent) as directory:
        replay_root = Path(directory) / "replay"
        run(root / "preregistration.json", root / "family.json", root / "source_review.json", replay_root)
        if (root / "evidence.json").read_bytes() != (replay_root / "evidence.json").read_bytes():
            raise ValueError("calibrated family replay mismatch")
    return 0
