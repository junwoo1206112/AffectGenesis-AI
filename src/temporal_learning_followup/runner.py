"""Artifact writer for a separate, small-config follow-up experiment."""
from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Callable, Iterator
from pathlib import Path

from temporal_experience import EpisodeKey, ExperimentAction, TemporalEnvironment
from temporal_learning.learner import ModelKind, TemporalLearner
from temporal_learning_v2.episode import training_action
from temporal_learning_v2.stream import PublicJsonlWriter, RestrictedAuditJsonlWriter

from .checks import derive_checks
from .config import canonical_json
from .identity import source_hashes


def _write_json(path: Path, value: object) -> None:
    path.write_text(canonical_json(value), encoding="utf-8", newline="\n")


def _episode(learner: TemporalLearner, condition: str, seed: int, episode: int, *, learn: bool,
             behavior: bool, neutral_scalar: bool = False, audit_context: dict[str, object] | None = None,
             audit_sink: Callable[[dict[str, object]], None] | None = None) -> Iterator[dict[str, object]]:
    environment = TemporalEnvironment(condition)
    observation = environment.reset(EpisodeKey(condition, seed, episode))
    for step in range(30):
        if audit_sink is not None:
            snapshot = environment.audit_snapshot()
            audit_sink({"phase": "training", "checkpoint": None, "condition": condition, "model": None,
                        "seed": seed, "episode": episode, "step": step, "state_before": snapshot["state"],
                        **(audit_context or {})})
        if neutral_scalar:
            learner.reset_scalar()
        action = training_action(seed, episode, step) if behavior else learner.predict(observation).action
        feedback, next_observation = environment.step(action)
        prior, scalar_before, context_after = learner.observe(action, feedback, learn_counts=learn)
        yield {"seed": seed, "episode": episode, "step": step, "remaining": observation.remaining,
               "action": action.value, "feedback": {"outcome": feedback.outcome, "reward": feedback.reward, "terminal": feedback.terminal},
               "prior_try_success": prior, "scalar_before": scalar_before, "scalar_after": learner.scalar,
               "context_after": tuple(token.value for token in context_after), "scalar_neutral": neutral_scalar}
        if feedback.terminal:
            return
        if next_observation is None:
            raise AssertionError("nonterminal step must yield public observation")
        observation = next_observation


def _score(checkpoint: dict[str, object], config_hash: str, config: dict[str, object], kind: str, seed: int,
           writer: PublicJsonlWriter, deadline: Callable[[], None], audit: RestrictedAuditJsonlWriter | None) -> float:
    learner = TemporalLearner.from_checkpoint(checkpoint, config_hash)
    total = 0.0
    neutral = kind == "affect_neutral"
    for episode in range(int(config["evaluation_episodes"])):
        learner.reset_episode()
        rewards: list[float] = []
        for row in _episode(learner, str(config["held_out_condition"]), seed, 100_000 + episode,
                            learn=False, behavior=False, neutral_scalar=neutral,
                            audit_context={"phase": "evaluation", "checkpoint": config["train_episodes"], "model": kind},
                            audit_sink=None if audit is None else audit.write):
            deadline(); writer.write({"checkpoint": config["train_episodes"], "condition": config["held_out_condition"], "model": kind, **row})
            rewards.append(float(row["feedback"]["reward"]))
        total += math.fsum(rewards)
    return total / (int(config["evaluation_episodes"]) * 30)


def run_full(config: dict[str, object], root: Path, *, clock: Callable[[], float] = time.monotonic) -> int:
    """Write a complete follow-up artifact; caller decides whether a regular run is authorized."""
    started = clock()
    def deadline() -> None:
        if clock() - started > int(config["time_limit_seconds"]):
            raise TimeoutError("run time limit exceeded")
    root.mkdir(parents=True, exist_ok=False)
    public = root / "public"; public.mkdir()
    training = episodes = audit = None
    stage = "setup"
    try:
        config_hash = hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest()
        training, episodes = PublicJsonlWriter(public / "training.jsonl"), PublicJsonlWriter(public / "episodes.jsonl")
        if config["protocol"] == "temporal-learning-followup-2":
            audit_dir = root / "restricted_audit"; audit_dir.mkdir()
            audit = RestrictedAuditJsonlWriter(audit_dir / "audit.jsonl")
        checkpoints: dict[str, object] = {}
        scores = {str(point): {str(config["held_out_condition"]): {model: [] for model in config["models"]}} for point in config["checkpoints"]}
        stage = "training"
        for seed in config["seeds"]:
            learners = {kind: TemporalLearner(kind) for kind in ModelKind}
            snapshots: dict[str, object] = {}
            for episode in range(int(config["train_episodes"]) + 1):
                if episode in config["checkpoints"]:
                    snapshots[str(episode)] = {kind.value: learner.checkpoint(config_hash) for kind, learner in learners.items()}
                if episode == config["train_episodes"]:
                    break
                for learner in learners.values(): learner.reset_episode()
                for row in _episode(learners[ModelKind.COUNTS], str(config["training_condition"]), seed, episode, learn=True, behavior=True,
                                    audit_sink=None if audit is None else audit.write):
                    deadline(); training.write(row)
                    action = ExperimentAction(row["action"])
                    from temporal_experience import Feedback
                    raw = row["feedback"]; feedback = Feedback(action, raw["outcome"], raw["reward"], raw["terminal"])
                    for kind, learner in learners.items():
                        if kind is not ModelKind.COUNTS: learner.observe(action, feedback, learn_counts=True)
            checkpoints[str(seed)] = snapshots
            stage = "evaluation"
            final = snapshots[str(config["train_episodes"])]
            for model in config["models"]:
                source = "affect" if model == "affect_neutral" else model
                scores[str(config["train_episodes"])][str(config["held_out_condition"])][model].append(
                    _score(final[source], config_hash, config, model, seed, episodes, deadline, audit))
        stage = "finalization"
        training_receipt, episode_receipt = training.close(), episodes.close()
        _write_json(public / "checkpoints.json", {"schema": f"{config['protocol']}-checkpoints", "config_hash": config_hash, "by_seed": checkpoints})
        metrics = {"schema": f"{config['protocol']}-metrics", "seed_order": config["seeds"], "scores": scores,
                   "training": training_receipt, "episodes": episode_receipt}
        _write_json(public / "metrics.json", metrics)
        checks = derive_checks(config, scores); _write_json(public / "checks.json", checks)
        manifest = {"artifact_schema": config["protocol"], "mode": "full-followup", "config": config, "config_hash": config_hash}
        if audit is not None:
            manifest["restricted_audit"] = {"schema": "temporal-learning-followup-2-restricted-audit-1", "file": "audit.jsonl", **audit.close()}
            manifest["source_hashes"] = source_hashes()
        _write_json(public / "manifest.json", manifest)
        hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in public.iterdir() if path.is_file()}
        _write_json(public / "completion.json", {"status": "completed", "public_hashes": hashes})
        return 0
    except Exception as error:
        for writer in (training, episodes, audit):
            if writer is not None:
                writer.close()
        _write_json(root / "failure.json", {"status": "failed", "error_type": type(error).__name__, "stage": stage})
        raise
