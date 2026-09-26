"""Strict verification and verify-first replay for isolated v2 tiny artifacts."""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

from temporal_learning.learner import TemporalLearner
from temporal_learning.learner import Token
from temporal_experience import ExperimentAction, Feedback

from .episode import run_public_episode
from .evidence import canonical_public_line
from .checks import derive_checks, paired_deltas, render_report
from .config import canonical_json
from .diagnostics import learning_diagnostics, persistence_receipt, safety_evidence
from .runner import run_full


def verify_tiny(root: Path) -> int:
    public, completion_path = root / "public", root / "completion.json"
    if not public.is_dir() or (root / "failure.json").exists() or not completion_path.is_file():
        raise ValueError("invalid tiny artifact")
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    if completion.get("status") != "completed" or set(completion.get("public_hashes", {})) != {"manifest.json", "training.jsonl", "receipt.json"}:
        raise ValueError("invalid completion")
    for name, digest in completion["public_hashes"].items():
        path = public / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("public hash mismatch")
    manifest = json.loads((public / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("artifact_schema") != "temporal-learning-v2" or manifest.get("mode") != "tiny-e2e":
        raise ValueError("invalid manifest")
    lines = (public / "training.jsonl").read_text(encoding="utf-8").splitlines()
    if len(lines) != 30:
        raise ValueError("invalid row count")
    for step, line in enumerate(lines):
        row = json.loads(line)
        if canonical_public_line(row).rstrip("\n") != line or row.get("step") != step or row.get("remaining") != 30 - step:
            raise ValueError("invalid public row")
    return 0


def replay_tiny(root: Path) -> int:
    verify_tiny(root)
    manifest = json.loads((root / "public" / "manifest.json").read_text(encoding="utf-8"))
    expected = "".join(canonical_public_line(row) for row in run_public_episode(TemporalLearner(), "train", manifest["config"]["seeds"][0], 0, learn_counts=True, behavior=True))
    if (root / "public" / "training.jsonl").read_text(encoding="utf-8") != expected:
        raise ValueError("replay mismatch")
    return 0


def verify_tiny_audit(root: Path) -> int:
    verify_tiny(root)
    manifest = json.loads((root / "public" / "manifest.json").read_text(encoding="utf-8"))
    commitment = manifest.get("restricted_audit")
    path = root / "restricted_audit" / "audit.jsonl"
    if type(commitment) is not dict or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != commitment.get("sha256"):
        raise ValueError("invalid restricted audit")
    public = (root / "public" / "training.jsonl").read_text(encoding="utf-8").splitlines()
    audit = path.read_text(encoding="utf-8").splitlines()
    if len(public) != len(audit) or len(audit) != commitment.get("row_count"):
        raise ValueError("audit join mismatch")
    for line, audit_line in zip(public, audit):
        row, entry = json.loads(line), json.loads(audit_line)
        if (entry.get("phase"), entry.get("checkpoint"), entry.get("condition"), entry.get("model"), entry.get("seed"), entry.get("episode"), entry.get("step")) != ("training", None, "train", None, row["seed"], row["episode"], row["step"]):
            raise ValueError("audit join mismatch")
    return 0


FULL_FILES = frozenset({"manifest.json", "training.jsonl", "episodes.jsonl", "checkpoints.json", "metrics.json", "diagnostics.json", "checks.json", "report.md", "completion.json"})
REPLAY_CONTENT_FILES = FULL_FILES - {"manifest.json", "completion.json"}


def _file_receipt(path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    rows = 0
    with path.open("rb") as stream:
        for line in stream:
            if not line.endswith(b"\n") or line == b"\n":
                raise ValueError("invalid JSONL receipt")
            digest.update(line)
            rows += 1
    return {"row_count": rows, "sha256": digest.hexdigest()}


def _next_json(stream, error: str) -> tuple[dict, str]:
    line = stream.readline()
    if not line:
        raise ValueError(error)
    if not line.endswith("\n"):
        raise ValueError(error)
    return json.loads(line), line.rstrip("\n")


def _validate_public_episode(rows: list[dict], *, training: bool) -> None:
    """Check public row semantics independently of stored file hashes."""
    required = {"seed", "episode", "step", "remaining", "action", "feedback", "prior_try_success", "scalar_before", "scalar_after", "context_before", "context_after"}
    for step, row in enumerate(rows):
        base = row if training else {key: value for key, value in row.items() if key not in {"checkpoint", "condition", "model"}}
        if set(base) != required or base["step"] != step or base["remaining"] != 30 - step:
            raise ValueError("invalid public row")
        action = ExperimentAction(base["action"])
        feedback_data = base["feedback"]
        if set(feedback_data) != {"outcome", "reward", "terminal"}:
            raise ValueError("invalid public feedback")
        feedback = Feedback(action, feedback_data["outcome"], feedback_data["reward"], feedback_data["terminal"])
        if feedback.terminal != (step == 29) or not isinstance(base["context_before"], list) or not isinstance(base["context_after"], list) or len(base["context_before"]) != 2 or len(base["context_after"]) != 2:
            raise ValueError("invalid public context")
        before = tuple(Token(value) for value in base["context_before"])
        token = Token.TS if feedback.outcome == "success" else Token.TF if feedback.outcome == "failure" else Token.SD if action is ExperimentAction.SAFE else Token.RD
        if tuple(Token(value) for value in base["context_after"]) != (before[1], token):
            raise ValueError("invalid context transition")
        if training and action.value != __import__("temporal_learning_v2.episode", fromlist=["training_action"]).training_action(base["seed"], base["episode"], step).value:
            raise ValueError("invalid training action")


def _scores_from_episodes(config: dict[str, object], path: Path) -> dict[str, dict[str, dict[str, list[float]]]]:
    scores = {str(point): {condition: {model: [] for model in config["models"]} for condition in ("same_distribution", "test_A", "test_B")}
              for point in config["checkpoints"]}
    required = {"checkpoint", "condition", "model", "seed", "episode", "step", "remaining", "action", "feedback", "prior_try_success", "scalar_before", "scalar_after", "context_before", "context_after"}
    with path.open(encoding="utf-8", newline="") as stream:
        for seed in config["seeds"]:
            for point in config["checkpoints"]:
                for condition in ("same_distribution", "test_A", "test_B"):
                    for model in config["models"]:
                        total = 0.0
                        for episode in range(config["evaluation_episodes"]):
                            rows: list[dict] = []
                            for _ in range(30):
                                row, line = _next_json(stream, "missing evaluation episode")
                                if (set(row) != required or canonical_public_line(row).rstrip("\n") != line
                                        or (row["checkpoint"], row["condition"], row["model"], row["seed"], row["episode"])
                                        != (point, condition, model, seed, 100_000 + episode)):
                                    raise ValueError("invalid evaluation row")
                                rows.append(row)
                            _validate_public_episode(rows, training=False)
                            total += math.fsum(float(row["feedback"]["reward"]) for row in rows)
                        scores[str(point)][condition][model].append(total / (config["evaluation_episodes"] * 30))
        if stream.readline():
            raise ValueError("unexpected evaluation row")
    return scores


def verify_full(root: Path) -> int:
    public = root / "public"
    if not public.is_dir() or (root / "failure.json").exists() or {path.name for path in public.iterdir()} != FULL_FILES:
        raise ValueError("invalid full layout")
    if any(not path.is_file() or path.is_symlink() for path in public.iterdir()):
        raise ValueError("invalid full file")
    completion = json.loads((public / "completion.json").read_text(encoding="utf-8"))
    expected_names = FULL_FILES - {"completion.json"}
    if completion.get("status") != "completed" or set(completion.get("public_hashes", {})) != expected_names:
        raise ValueError("invalid full completion")
    for name, digest in completion["public_hashes"].items():
        if hashlib.sha256((public / name).read_bytes()).hexdigest() != digest:
            raise ValueError("full hash mismatch")
    manifest = json.loads((public / "manifest.json").read_text(encoding="utf-8"))
    config = manifest.get("config")
    if manifest.get("artifact_schema") != "temporal-learning-v2" or manifest.get("mode") != "full-v2" or not isinstance(config, dict):
        raise ValueError("invalid full manifest")
    if manifest.get("config_hash") != hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest():
        raise ValueError("invalid full config")
    with (public / "training.jsonl").open(encoding="utf-8", newline="") as stream:
        for seed in config["seeds"]:
            for episode in range(config["train_episodes"]):
                rows: list[dict] = []
                for _ in range(30):
                    row, _ = _next_json(stream, "missing training episode")
                    if (row.get("seed"), row.get("episode")) != (seed, episode):
                        raise ValueError("invalid training order")
                    rows.append(row)
                _validate_public_episode(rows, training=True)
        if stream.readline():
            raise ValueError("unexpected training row")
    checkpoints = json.loads((public / "checkpoints.json").read_text(encoding="utf-8"))
    if checkpoints.get("schema") != "temporal-learning-v2-checkpoints" or checkpoints.get("config_hash") != manifest["config_hash"] or set(checkpoints.get("by_seed", {})) != {str(seed) for seed in config["seeds"]}:
        raise ValueError("invalid checkpoints")
    for seed in config["seeds"]:
        for point in config["checkpoints"]:
            models = checkpoints["by_seed"][str(seed)].get(str(point), {})
            if set(models) != set(config["models"]): raise ValueError("missing checkpoint model")
            for checkpoint in models.values(): TemporalLearner.from_checkpoint(checkpoint, manifest["config_hash"])
    metrics = json.loads((public / "metrics.json").read_text(encoding="utf-8"))
    recomputed = _scores_from_episodes(config, public / "episodes.jsonl")
    if metrics.get("schema") != "temporal-learning-v2-metrics" or metrics.get("seed_order") != config["seeds"] or metrics.get("scores") != recomputed or metrics.get("reward_per_step") != recomputed or metrics.get("paired_deltas") != paired_deltas(config, recomputed):
        raise ValueError("metrics mismatch")
    evaluation_receipt = _file_receipt(public / "episodes.jsonl")
    reloaded = persistence_receipt(config, manifest["config_hash"], checkpoints["by_seed"])
    diagnostics = json.loads((public / "diagnostics.json").read_text(encoding="utf-8"))
    base_diagnostics = {"schema": "temporal-learning-v2-diagnostics",
                        "persistence": {"reloaded": reloaded, "evaluation": evaluation_receipt,
                                        "matches": reloaded == evaluation_receipt},
                        "safety": safety_evidence()}
    learning = None
    if "learning" in diagnostics:
        learning = learning_diagnostics(config, manifest["config_hash"], checkpoints["by_seed"])
        expected_diagnostics = {**base_diagnostics, "learning": learning}
    else:
        expected_diagnostics = base_diagnostics
    if diagnostics != expected_diagnostics:
        raise ValueError("diagnostics mismatch")
    checks = derive_checks(config, recomputed, persistence=diagnostics["persistence"]["matches"],
                           safety=diagnostics["safety"]["passes"], learning=learning)
    if json.loads((public / "checks.json").read_text(encoding="utf-8")) != checks or (public / "report.md").read_text(encoding="utf-8") != render_report(checks):
        raise ValueError("derived output mismatch")
    return 0


def replay_full(root: Path) -> int:
    verify_full(root)
    config = json.loads((root / "public" / "manifest.json").read_text(encoding="utf-8"))["config"]
    legacy_diagnostics = "learning" not in json.loads((root / "public" / "diagnostics.json").read_text(encoding="utf-8"))
    with TemporaryDirectory() as directory:
        regenerated = Path(directory) / "replay"
        run_full(config, regenerated, with_restricted_audit=(root / "restricted_audit").is_dir())
        compared_files = REPLAY_CONTENT_FILES - ({"diagnostics.json", "checks.json", "report.md"} if legacy_diagnostics else set())
        for name in compared_files:
            with (root / "public" / name).open("rb") as expected, (regenerated / "public" / name).open("rb") as actual:
                while True:
                    if expected.read(65_536) != actual.read(65_536):
                        raise ValueError("full replay mismatch")
                    if expected.tell() == (root / "public" / name).stat().st_size:
                        break
        if legacy_diagnostics:
            expected_diagnostics = json.loads((root / "public" / "diagnostics.json").read_text(encoding="utf-8"))
            actual_diagnostics = json.loads((regenerated / "public" / "diagnostics.json").read_text(encoding="utf-8"))
            actual_diagnostics.pop("learning", None)
            if expected_diagnostics != actual_diagnostics:
                raise ValueError("full replay mismatch")
            actual_metrics = json.loads((regenerated / "public" / "metrics.json").read_text(encoding="utf-8"))
            legacy_checks = derive_checks(config, actual_metrics["scores"],
                                          persistence=actual_diagnostics["persistence"]["matches"],
                                          safety=actual_diagnostics["safety"]["passes"])
            if (root / "public" / "checks.json").read_text(encoding="utf-8") != canonical_json(legacy_checks):
                raise ValueError("full replay mismatch")
            if (root / "public" / "report.md").read_text(encoding="utf-8") != render_report(legacy_checks):
                raise ValueError("full replay mismatch")
        expected_manifest = json.loads((root / "public" / "manifest.json").read_text(encoding="utf-8"))
        actual_manifest = json.loads((regenerated / "public" / "manifest.json").read_text(encoding="utf-8"))
        expected_manifest.pop("source_hashes", None)
        actual_manifest.pop("source_hashes", None)
        if expected_manifest != actual_manifest:
            raise ValueError("full replay mismatch")
        expected_completion = json.loads((root / "public" / "completion.json").read_text(encoding="utf-8"))
        actual_completion = json.loads((regenerated / "public" / "completion.json").read_text(encoding="utf-8"))
        for completion in (expected_completion, actual_completion):
            completion.get("public_hashes", {}).pop("manifest.json", None)
            if legacy_diagnostics:
                for name in ("diagnostics.json", "checks.json", "report.md"):
                    completion.get("public_hashes", {}).pop(name, None)
        if expected_completion != actual_completion:
            raise ValueError("full replay mismatch")
        if (root / "restricted_audit").is_dir() and (root / "restricted_audit" / "audit.jsonl").read_bytes() != (regenerated / "restricted_audit" / "audit.jsonl").read_bytes():
            raise ValueError("full replay mismatch")
    return 0


def verify_full_audit(root: Path) -> int:
    """Opt-in restricted audit verification; normal public verify stays blind."""
    verify_full(root)
    public = root / "public"
    manifest = json.loads((public / "manifest.json").read_text(encoding="utf-8"))
    commitment = manifest.get("restricted_audit")
    audit_path = root / "restricted_audit" / "audit.jsonl"
    if (type(commitment) is not dict or set(commitment) != {"schema", "file", "row_count", "sha256"}
            or commitment.get("schema") != "temporal-learning-v2-restricted-audit-1" or commitment.get("file") != "audit.jsonl"
            or not audit_path.is_file() or audit_path.is_symlink()
            or hashlib.sha256(audit_path.read_bytes()).hexdigest() != commitment.get("sha256")):
        raise ValueError("invalid full restricted audit")
    required = {"phase", "seed", "checkpoint", "condition", "model", "episode", "step", "state_before"}
    rows = 0
    def consume_group(groups: object, expected_seed: int, phase: str, audit: object) -> int:
        nonlocal rows
        try:
            actual_seed, lines = next(groups)
        except StopIteration as error:
            raise ValueError("full audit row count") from error
        if actual_seed != expected_seed:
            raise ValueError("full audit join mismatch")
        for line in lines:
            row = json.loads(line)
            audit_line = audit.readline()
            if not audit_line:
                raise ValueError("full audit row count")
            entry = json.loads(audit_line)
            join = (phase, row.get("checkpoint") if phase == "evaluation" else None,
                    row.get("condition") if phase == "evaluation" else "train",
                    row.get("model") if phase == "evaluation" else None,
                    row["seed"], row["episode"], row["step"])
            if set(entry) != required or entry.get("state_before") not in ("G", "B") or tuple(entry.get(key) for key in ("phase", "checkpoint", "condition", "model", "seed", "episode", "step")) != join:
                raise ValueError("full audit join mismatch")
            rows += 1
        return rows
    with audit_path.open(encoding="utf-8", newline="") as audit:
        with (public / "training.jsonl").open(encoding="utf-8", newline="") as training, (public / "episodes.jsonl").open(encoding="utf-8", newline="") as episodes:
            training_groups = itertools.groupby(training, key=lambda line: json.loads(line)["seed"])
            episode_groups = itertools.groupby(episodes, key=lambda line: json.loads(line)["seed"])
            for seed in manifest["config"]["seeds"]:
                consume_group(training_groups, seed, "training", audit)
                consume_group(episode_groups, seed, "evaluation", audit)
            if next(training_groups, None) is not None or next(episode_groups, None) is not None:
                raise ValueError("full audit join mismatch")
        if audit.readline() or rows != commitment.get("row_count"):
            raise ValueError("full audit row count")
    return 0
