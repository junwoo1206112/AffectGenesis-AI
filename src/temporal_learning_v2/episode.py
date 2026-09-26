"""Deterministic v2 public episode generation without audit leakage."""
from __future__ import annotations

from collections.abc import Callable, Iterator

from temporal_experience import EpisodeKey, ExperimentAction, TemporalEnvironment
from temporal_learning.learner import TemporalLearner
import hashlib
import json


def training_action(seed: int, episode: int, step: int) -> ExperimentAction:
    encoded = json.dumps(["temporal-learning-v2", "training-action", seed, episode, step], separators=(",", ":")).encode("utf-8")
    return tuple(ExperimentAction)[int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big") % len(ExperimentAction)]


def run_public_episode(learner: TemporalLearner, condition: str, seed: int, episode: int,
                       *, learn_counts: bool, behavior: bool,
                       audit_context: dict[str, object] | None = None,
                       audit_sink: Callable[[dict[str, object]], None] | None = None) -> Iterator[dict[str, object]]:
    environment = TemporalEnvironment(condition)
    observation = environment.reset(EpisodeKey(condition, seed, episode))
    for step in range(30):
        if audit_sink is not None:
            snapshot = environment.audit_snapshot()
            audit_sink({"phase": "training", "checkpoint": None, "condition": condition, "model": None,
                        "seed": seed, "episode": episode, "step": step, "state_before": snapshot["state"], **(audit_context or {})})
        action = training_action(seed, episode, step) if behavior else learner.predict(observation).action
        scalar_before = learner.scalar
        context_before = tuple(token.value for token in learner.context)
        feedback, next_observation = environment.step(action)
        prior, _, context_after = learner.observe(action, feedback, learn_counts=learn_counts)
        yield {"seed": seed, "episode": episode, "step": step, "remaining": observation.remaining,
               "action": action.value, "feedback": {"outcome": feedback.outcome, "reward": feedback.reward, "terminal": feedback.terminal},
               "prior_try_success": prior, "scalar_before": scalar_before, "scalar_after": learner.scalar,
               "context_before": context_before, "context_after": tuple(token.value for token in context_after)}
        if feedback.terminal:
            return
        if next_observation is None:
            raise AssertionError("nonterminal step must yield public observation")
        observation = next_observation
    raise AssertionError("environment did not terminate at horizon")
