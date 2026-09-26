"""Isolated v2 writers; full runs never reuse v1's audit-bearing executor."""
from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Callable
from pathlib import Path

from temporal_experience import ExperimentAction, Feedback
from temporal_learning.learner import ModelKind, TemporalLearner

from .checks import derive_checks, paired_deltas, render_report
from .config import canonical_json
from .diagnostics import learning_diagnostics, persistence_receipt, safety_evidence
from .episode import run_public_episode
from .identity import source_hashes
from .stream import PublicJsonlWriter, RestrictedAuditJsonlWriter


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(_canonical(value))


def _sha256_file(path: Path, deadline_check: Callable[[], None]) -> str:
    """Hash public files without loading a regular-scale artifact into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65_536):
            deadline_check()
            digest.update(chunk)
    return digest.hexdigest()


def _evaluate(checkpoint: dict[str, object], config_hash: str, checkpoint_index: int, condition: str,
              model: str, seed: int, episodes: int, writer: PublicJsonlWriter,
              audit: RestrictedAuditJsonlWriter | None, deadline_check: Callable[[], None]) -> float:
    learner = TemporalLearner.from_checkpoint(checkpoint, config_hash)
    total = 0.0
    for episode in range(episodes):
        learner.reset_episode()
        # Pair checkpoints/models against the same held-out tape episode.
        key_episode = 100_000 + episode
        audit_context = {"phase": "evaluation", "checkpoint": checkpoint_index, "condition": condition, "model": model}
        rewards: list[float] = []
        for row in run_public_episode(learner, condition, seed, key_episode, learn_counts=False, behavior=False,
                                      audit_context=audit_context, audit_sink=None if audit is None else audit.write):
            deadline_check()
            writer.write({"checkpoint": checkpoint_index, "condition": condition, "model": model, **row})
            rewards.append(float(row["feedback"]["reward"]))
        total += math.fsum(rewards)
    return total / (episodes * 30)


def run_full(config: dict[str, object], root: Path, *, with_restricted_audit: bool = False,
             clock: Callable[[], float] = time.monotonic) -> int:
    """Write a complete small-config v2 artifact with paired held-out scores.

    The caller supplies a configuration already accepted by ``load_config``.
    This function intentionally does not run a regular experiment by itself.
    """
    started = clock()
    def deadline_check() -> None:
        if clock() - started > config["time_limit_seconds"]:
            raise TimeoutError("run time limit exceeded")

    root.mkdir(parents=True, exist_ok=False)
    public = root / "public"
    training = episodes = audit = None
    stage = "setup"
    try:
        public.mkdir()
        config_hash = hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest()
        if with_restricted_audit:
            audit_dir = root / "restricted_audit"; audit_dir.mkdir()
            audit = RestrictedAuditJsonlWriter(audit_dir / "audit.jsonl")
        training = PublicJsonlWriter(public / "training.jsonl")
        episodes = PublicJsonlWriter(public / "episodes.jsonl")
        snapshots: dict[str, dict[str, dict[str, object]]] = {}
        scores: dict[str, dict[str, dict[str, list[float]]]] = {str(point): {condition: {kind.value: [] for kind in ModelKind}
                   for condition in ("same_distribution", "test_A", "test_B")} for point in config["checkpoints"]}
        stage = "training"
        for seed in config["seeds"]:
            learners = {kind: TemporalLearner(kind) for kind in ModelKind}
            seed_snapshots: dict[str, dict[str, object]] = {}
            for episode in range(int(config["train_episodes"]) + 1):
                if episode in config["checkpoints"]:
                    seed_snapshots[str(episode)] = {kind.value: learner.checkpoint(config_hash) for kind, learner in learners.items()}
                if episode == config["train_episodes"]:
                    break
                for learner in learners.values():
                    learner.reset_episode()
                for row in run_public_episode(learners[ModelKind.COUNTS], "train", seed, episode, learn_counts=True, behavior=True,
                                              audit_sink=None if audit is None else audit.write):
                    deadline_check()
                    training.write(row)
                    action, raw = ExperimentAction(row["action"]), row["feedback"]
                    feedback = Feedback(action, raw["outcome"], raw["reward"], raw["terminal"])
                    for kind, learner in learners.items():
                        if kind is not ModelKind.COUNTS:
                            learner.observe(action, feedback, learn_counts=True)
            snapshots[str(seed)] = seed_snapshots
            stage = "evaluation"
            for point in config["checkpoints"]:
                for condition in ("same_distribution", "test_A", "test_B"):
                    for kind in ModelKind:
                        score = _evaluate(seed_snapshots[str(point)][kind.value], config_hash, point, condition, kind.value, seed,
                                          int(config["evaluation_episodes"]), episodes, audit, deadline_check)
                        scores[str(point)][condition][kind.value].append(score)
        stage = "finalization"
        training_receipt, episode_receipt = training.close(), episodes.close()
        _write_json(public / "checkpoints.json", {"schema": "temporal-learning-v2-checkpoints", "config_hash": config_hash, "by_seed": snapshots})
        metrics = {"schema": "temporal-learning-v2-metrics", "seed_order": config["seeds"], "scores": scores, "reward_per_step": scores, "paired_deltas": paired_deltas(config, scores),
                   "training": training_receipt, "episodes": episode_receipt}
        _write_json(public / "metrics.json", metrics)
        reloaded = persistence_receipt(config, config_hash, snapshots, deadline_check)
        learning = learning_diagnostics(config, config_hash, snapshots, deadline_check)
        diagnostics = {"schema": "temporal-learning-v2-diagnostics",
                       "persistence": {"reloaded": reloaded, "evaluation": episode_receipt,
                                       "matches": reloaded == episode_receipt},
                       "safety": safety_evidence(), "learning": learning}
        _write_json(public / "diagnostics.json", diagnostics)
        checks = derive_checks(config, scores, persistence=diagnostics["persistence"]["matches"],
                               safety=diagnostics["safety"]["passes"], learning=learning)
        _write_json(public / "checks.json", checks)
        (public / "report.md").write_text(render_report(checks), encoding="utf-8", newline="\n")
        manifest: dict[str, object] = {"artifact_schema": "temporal-learning-v2", "mode": "full-v2", "config": config,
                                        "config_hash": config_hash, "source_hashes": source_hashes()}
        if audit is not None:
            manifest["restricted_audit"] = {"schema": "temporal-learning-v2-restricted-audit-1", "file": "audit.jsonl", **audit.close()}
        _write_json(public / "manifest.json", manifest)
        expected = {path.name: _sha256_file(path, deadline_check) for path in public.iterdir() if path.is_file()}
        _write_json(public / "completion.json", {"status": "completed", "public_hashes": expected})
        return 0
    except Exception as error:
        for writer in (training, episodes, audit):
            if writer is not None:
                try:
                    writer.close()
                except OSError:
                    pass
        _write_json(root / "failure.json", {"status": "failed", "error_type": type(error).__name__, "stage": stage})
        raise


def run_tiny(config: dict[str, object], root: Path, *, with_restricted_audit: bool = False) -> int:
    """Write a one-episode public artifact; intended only for isolated E2E tests."""
    root.mkdir(parents=True, exist_ok=False)
    public = root / "public"
    public.mkdir()
    try:
        writer = PublicJsonlWriter(public / "training.jsonl")
        seed = config["seeds"][0]
        audit = None
        if with_restricted_audit:
            audit_dir = root / "restricted_audit"; audit_dir.mkdir()
            audit = RestrictedAuditJsonlWriter(audit_dir / "audit.jsonl")
        for row in run_public_episode(TemporalLearner(), "train", seed, 0, learn_counts=True, behavior=True,
                                      audit_sink=None if audit is None else audit.write):
            writer.write(row)
        receipt = writer.close()
        (public / "receipt.json").write_bytes(_canonical(receipt))
        manifest = {"artifact_schema": "temporal-learning-v2", "mode": "tiny-e2e", "config": config}
        if audit is not None:
            manifest["restricted_audit"] = {"schema": "temporal-learning-v2-restricted-audit-1", "file": "audit.jsonl", **audit.close()}
        (public / "manifest.json").write_bytes(_canonical(manifest))
        hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in public.iterdir() if path.is_file()}
        (root / "completion.json").write_bytes(_canonical({"status": "completed", "public_hashes": hashes}))
        return 0
    except Exception as error:
        (root / "failure.json").write_bytes(_canonical({"status": "failed", "error_type": type(error).__name__}))
        raise
