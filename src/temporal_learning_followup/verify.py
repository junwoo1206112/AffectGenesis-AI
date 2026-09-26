"""Read-only structural verification for follow-up public evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from temporal_learning_v2.evidence import canonical_public_line

from .checks import derive_checks
from .config import canonical_json
from .runner import run_full


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError("expected JSON object")
    return value


def _verify_legacy(root: Path) -> int:
    public = root / "public"
    completion, manifest, metrics, checks = (_load(public / name) for name in ("completion.json", "manifest.json", "metrics.json", "checks.json"))
    if completion.get("status") != "completed" or manifest.get("artifact_schema") != "temporal-learning-followup-1":
        raise ValueError("invalid completion or artifact schema")
    config = manifest.get("config")
    if type(config) is not dict or manifest.get("config_hash") != hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest():
        raise ValueError("invalid manifest configuration")
    expected = completion.get("public_hashes")
    if type(expected) is not dict or any(hashlib.sha256((public / name).read_bytes()).hexdigest() != digest for name, digest in expected.items()):
        raise ValueError("public hash mismatch")
    if metrics.get("schema") != "temporal-learning-followup-1-metrics" or metrics.get("seed_order") != config.get("seeds"):
        raise ValueError("invalid metrics schema")
    if checks != derive_checks(config, metrics.get("scores")):
        raise ValueError("checks do not match scores")
    return 0


def _rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if canonical_public_line(row).rstrip("\n") != line:
            raise ValueError("noncanonical public row")
        rows.append(row)
    return rows


def _verify_v2(root: Path) -> int:
    public = root / "public"
    if (root / "failure.json").exists() or {path.name for path in public.iterdir()} != {"training.jsonl", "episodes.jsonl", "checkpoints.json", "metrics.json", "checks.json", "manifest.json", "completion.json"}:
        raise ValueError("invalid followup-2 layout")
    manifest = _load(public / "manifest.json"); completion = _load(public / "completion.json")
    config = manifest.get("config")
    if (manifest.get("artifact_schema") != "temporal-learning-followup-2" or type(config) is not dict
            or manifest.get("config_hash") != hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest()
            or completion.get("status") != "completed"):
        raise ValueError("invalid followup-2 manifest")
    expected = {"training.jsonl", "episodes.jsonl", "checkpoints.json", "metrics.json", "checks.json", "manifest.json"}
    if set(completion.get("public_hashes", {})) != expected:
        raise ValueError("invalid completion")
    for name, digest in completion["public_hashes"].items():
        if not (public / name).is_file() or (public / name).is_symlink() or hashlib.sha256((public / name).read_bytes()).hexdigest() != digest:
            raise ValueError("public hash mismatch")
    training, episodes = _rows(public / "training.jsonl"), _rows(public / "episodes.jsonl")
    if len(training) != len(config["seeds"]) * config["train_episodes"] * 30 or len(episodes) != len(config["seeds"]) * len(config["models"]) * config["evaluation_episodes"] * 30:
        raise ValueError("invalid public row count")
    for index, row in enumerate(training):
        step = index % 30
        if set(row) != {"seed", "episode", "step", "remaining", "action", "feedback", "prior_try_success", "scalar_before", "scalar_after", "context_after", "scalar_neutral"} or row["step"] != step or row["remaining"] != 30 - step:
            raise ValueError("invalid training row")
    scores = {str(point): {config["held_out_condition"]: {model: [] for model in config["models"]}} for point in config["checkpoints"]}
    cursor = 0
    for seed in config["seeds"]:
        for model in config["models"]:
            total = 0.0
            for episode in range(config["evaluation_episodes"]):
                group = episodes[cursor:cursor + 30]; cursor += 30
                if len(group) != 30 or any((row.get("checkpoint"), row.get("condition"), row.get("model"), row.get("seed"), row.get("episode"), row.get("step"), row.get("remaining")) != (config["train_episodes"], config["held_out_condition"], model, seed, 100_000 + episode, step, 30 - step) for step, row in enumerate(group)):
                    raise ValueError("invalid evaluation order")
                total += sum(float(row["feedback"]["reward"]) for row in group)
            scores[str(config["train_episodes"])][config["held_out_condition"]][model].append(total / (config["evaluation_episodes"] * 30))
    metrics, checks = _load(public / "metrics.json"), _load(public / "checks.json")
    if metrics.get("schema") != "temporal-learning-followup-2-metrics" or metrics.get("seed_order") != config["seeds"] or metrics.get("scores") != scores or checks != derive_checks(config, scores):
        raise ValueError("derived evidence mismatch")
    return 0


def verify_artifact(root: Path) -> int:
    manifest = _load(root / "public" / "manifest.json")
    return _verify_v2(root) if manifest.get("artifact_schema") == "temporal-learning-followup-2" else _verify_legacy(root)


def verify_audit(root: Path) -> int:
    _verify_v2(root)
    manifest = _load(root / "public" / "manifest.json"); commitment = manifest.get("restricted_audit")
    path = root / "restricted_audit" / "audit.jsonl"
    if (type(commitment) is not dict or commitment.get("schema") != "temporal-learning-followup-2-restricted-audit-1"
            or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != commitment.get("sha256")):
        raise ValueError("invalid restricted audit")
    audit = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    training, episodes = _rows(root / "public" / "training.jsonl"), _rows(root / "public" / "episodes.jsonl")
    public = []
    for seed in manifest["config"]["seeds"]:
        public.extend(row for row in training if row["seed"] == seed)
        public.extend(row for row in episodes if row["seed"] == seed)
    if len(audit) != len(public) or len(audit) != commitment.get("row_count"):
        raise ValueError("audit row count")
    for entry, row in zip(audit, public):
        phase = "evaluation" if "model" in row else "training"
        expected = (phase, row.get("checkpoint"), row.get("condition", "train"), row.get("model"), row["seed"], row["episode"], row["step"])
        if set(entry) != {"phase", "checkpoint", "condition", "model", "seed", "episode", "step", "state_before"} or entry.get("state_before") not in ("G", "B") or tuple(entry.get(key) for key in ("phase", "checkpoint", "condition", "model", "seed", "episode", "step")) != expected:
            raise ValueError("audit join mismatch")
    return 0


def replay_artifact(root: Path) -> int:
    verify_audit(root)
    config = _load(root / "public" / "manifest.json")["config"]
    with TemporaryDirectory() as directory:
        replay = Path(directory) / "replay"; run_full(config, replay)
        for name in ("training.jsonl", "episodes.jsonl", "checkpoints.json", "metrics.json", "checks.json"):
            if (root / "public" / name).read_bytes() != (replay / "public" / name).read_bytes():
                raise ValueError("replay mismatch")
        if (root / "restricted_audit" / "audit.jsonl").read_bytes() != (replay / "restricted_audit" / "audit.jsonl").read_bytes():
            raise ValueError("replay mismatch")
    return 0
