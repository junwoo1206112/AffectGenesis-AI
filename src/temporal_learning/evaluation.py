"""Deterministic training and frozen-count evaluation for temporal-learning-v1.

The runner deliberately receives only public observations and feedback.  Audit
state is copied into result rows by the runner, never passed to a learner.
"""
from __future__ import annotations

import hashlib
import json
from statistics import mean
from typing import Any

from temporal_experience import EpisodeKey, ExperimentAction, TemporalEnvironment

from .learner import ModelKind, TemporalLearner, Token


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def training_action(seed: int, episode: int, step: int) -> ExperimentAction:
    """A public, model-independent uniformly sampled behavior action."""
    encoded = canonical_json(["temporal-learning-v1", "training-action", seed, episode, step]).encode("utf-8")
    return tuple(ExperimentAction)[int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big") % len(ExperimentAction)]


def _run_episode(learner: TemporalLearner, condition: str, seed: int, episode: int,
                 learn_counts: bool, behavior: bool) -> tuple[float, list[dict[str, Any]]]:
    environment = TemporalEnvironment(condition)
    observation = environment.reset(EpisodeKey(condition, seed, episode))
    reward = 0.0
    rows: list[dict[str, Any]] = []
    for step in range(30):
        audit_before = environment.audit_snapshot()
        action = training_action(seed, episode, step) if behavior else learner.predict(observation).action
        scalar_before = learner.scalar
        context_before = tuple(token.value for token in learner.context)
        feedback, next_observation = environment.step(action)
        prior, _, context_after = learner.observe(action, feedback, learn_counts=learn_counts)
        rows.append({
            "seed": seed, "episode": episode, "step": step, "action": action.value,
            "feedback": {"outcome": feedback.outcome, "reward": feedback.reward, "terminal": feedback.terminal},
            "prior_try_success": prior, "scalar_before": scalar_before,
            "scalar_after": learner.scalar, "context_before": context_before,
            "context_after": tuple(token.value for token in context_after), "audit": audit_before,
        })
        reward += feedback.reward
        if feedback.terminal:
            return reward, rows
        if next_observation is None:
            raise AssertionError("nonterminal step must yield public observation")
        observation = next_observation
    raise AssertionError("environment did not terminate at horizon")


def train_seed(seed: int, episodes: int, checkpoints: tuple[int, ...], config_hash: str,
               kinds: tuple[ModelKind, ...] = tuple(ModelKind), deadline=None) -> tuple[dict[int, dict[ModelKind, dict]], list[dict[str, Any]]]:
    if type(seed) is not int or type(episodes) is not int or episodes < 0 or 0 not in checkpoints or episodes not in checkpoints:
        raise ValueError("invalid training plan")
    learners = {kind: TemporalLearner(kind) for kind in kinds}
    snapshots: dict[int, dict[ModelKind, dict]] = {}
    training_rows: list[dict[str, Any]] = []
    for episode in range(episodes + 1):
        if deadline is not None:
            deadline()
        if episode in checkpoints:
            snapshots[episode] = {kind: learner.checkpoint(config_hash) for kind, learner in learners.items()}
        if episode == episodes:
            break
        for learner in learners.values():
            learner.reset_episode()
        primary_reward, primary_rows = _run_episode(learners[kinds[0]], "train", seed, episode, True, True)
        for kind in kinds[1:]:
            learner = learners[kind]
            for row in primary_rows:
                feedback_data = row["feedback"]
                from temporal_experience import Feedback
                learner.observe(ExperimentAction(row["action"]), Feedback(ExperimentAction(row["action"]), feedback_data["outcome"], feedback_data["reward"], feedback_data["terminal"]), True)
        training_rows.extend(primary_rows)
    return snapshots, training_rows


def evaluate_checkpoint(checkpoint: dict, config_hash: str, condition: str, seed: int,
                        episodes: int, checkpoint_index: int, deadline=None) -> tuple[float, list[dict[str, Any]]]:
    learner = TemporalLearner.from_checkpoint(checkpoint, config_hash)
    rewards: list[float] = []
    rows: list[dict[str, Any]] = []
    for episode in range(episodes):
        if deadline is not None:
            deadline()
        learner.reset_episode()
        reward, episode_rows = _run_episode(learner, condition, seed, 10_000 + checkpoint_index * episodes + episode, False, False)
        rewards.append(reward / 30)
        rows.extend(episode_rows)
    return mean(rewards), rows
