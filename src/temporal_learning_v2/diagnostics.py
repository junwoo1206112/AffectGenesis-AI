"""Deterministic persistence and safety evidence for the v2 public artifact."""
from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Mapping

from functional_affect.models import Action
from temporal_experience import EpisodeKey, ExperimentAction, PublicObservation, TemporalEnvironment
from temporal_learning.learner import ModelKind, Token
from temporal_experience.safety_adapter import safety_action
from temporal_learning.learner import TemporalLearner

from .config import canonical_json
from .episode import run_public_episode
from .evidence import canonical_public_line


DIAGNOSTIC_CONDITIONS = ("same_distribution", "test_A", "test_B")
PERMUTED_TOKENS = {Token.BOS: Token.BOS, Token.TS: Token.TF, Token.TF: Token.TS,
                   Token.SD: Token.RD, Token.RD: Token.SD}


def _common_diagnostic_action(seed: int, condition: str, episode: int, step: int) -> ExperimentAction:
    """A checkpoint/model-independent deterministic behavior trace for Brier scoring."""
    encoded = canonical_json(["temporal-learning-v2", "diagnostic-behavior", seed, condition, episode, step]).encode("utf-8")
    return tuple(ExperimentAction)[int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big") % len(ExperimentAction)]


def _evaluate_diagnostic_episode(learner: TemporalLearner, condition: str, seed: int, episode: int,
                                 *, behavior: bool, neutral_scalar: bool = False,
                                 permute_context: bool = False) -> tuple[float, float, int, dict[str, int]]:
    """Evaluate a frozen checkpoint and return reward, Brier, TRY count, and contexts."""
    environment = TemporalEnvironment(condition)
    observation = environment.reset(EpisodeKey(condition, seed, episode))
    reward = brier = 0.0
    try_samples = 0
    contexts: dict[str, int] = {}
    for step in range(30):
        if neutral_scalar:
            learner.reset_scalar()
        action = _common_diagnostic_action(seed, condition, episode, step) if behavior else learner.predict(observation).action
        context_key = "/".join(token.value for token in learner.context)
        feedback, next_observation = environment.step(action)
        prior, _, _ = learner.observe(action, feedback, learn_counts=False)
        reward += float(feedback.reward)
        if action is ExperimentAction.TRY:
            brier += (prior - float(feedback.outcome == "success")) ** 2
            try_samples += 1
            contexts[context_key] = contexts.get(context_key, 0) + 1
        if permute_context:
            learner.context = tuple(PERMUTED_TOKENS[token] for token in learner.context)
        if feedback.terminal:
            return reward / 30, brier, try_samples, contexts
        if next_observation is None:
            raise AssertionError("nonterminal diagnostic step must yield observation")
        observation = next_observation
    raise AssertionError("diagnostic environment did not terminate")


def learning_diagnostics(config: Mapping[str, object], config_hash: str,
                         snapshots: Mapping[str, Mapping[str, Mapping[str, object]]],
                         deadline_check: Callable[[], None] | None = None) -> dict[str, object]:
    """Pre-registered frozen-checkpoint calibration and counterfactual evidence."""
    brier_scores = {str(point): {condition: {model: [] for model in config["models"]}
                                  for condition in DIAGNOSTIC_CONDITIONS} for point in config["checkpoints"]}
    brier_samples = {str(point): {condition: {model: [] for model in config["models"]}
                                   for condition in DIAGNOSTIC_CONDITIONS} for point in config["checkpoints"]}
    baseline = {str(point): {condition: [] for condition in DIAGNOSTIC_CONDITIONS} for point in config["checkpoints"]}
    neutral = {str(point): {condition: [] for condition in DIAGNOSTIC_CONDITIONS} for point in config["checkpoints"]}
    permuted = {str(point): {condition: [] for condition in DIAGNOSTIC_CONDITIONS} for point in config["checkpoints"]}
    contexts = {str(point): {condition: [] for condition in DIAGNOSTIC_CONDITIONS} for point in config["checkpoints"]}
    for seed in config["seeds"]:
        for point in config["checkpoints"]:
            checkpoint = snapshots[str(seed)][str(point)]
            for condition in DIAGNOSTIC_CONDITIONS:
                for model in config["models"]:
                    learner = TemporalLearner.from_checkpoint(checkpoint[model], config_hash)
                    brier_total = 0.0
                    sample_total = 0
                    for episode in range(int(config["evaluation_episodes"])):
                        learner.reset_episode()
                        _, value, samples, _ = _evaluate_diagnostic_episode(learner, condition, seed, 200_000 + episode, behavior=True)
                        if deadline_check is not None:
                            deadline_check()
                        brier_total += value
                        sample_total += samples
                    brier_scores[str(point)][condition][model].append(brier_total / sample_total if sample_total else None)
                    brier_samples[str(point)][condition][model].append(sample_total)
                context_counts: dict[str, int] = {}
                results: dict[str, float] = {}
                for name, neutral_scalar, permute_context in (("baseline", False, False), ("neutral", True, False), ("permuted", False, True)):
                    learner = TemporalLearner.from_checkpoint(checkpoint[ModelKind.AFFECT.value], config_hash)
                    total = 0.0
                    for episode in range(int(config["evaluation_episodes"])):
                        learner.reset_episode()
                        value, _, _, found = _evaluate_diagnostic_episode(learner, condition, seed, 100_000 + episode,
                                                                            behavior=False, neutral_scalar=neutral_scalar,
                                                                            permute_context=permute_context)
                        if deadline_check is not None:
                            deadline_check()
                        total += value
                        if name == "baseline":
                            for context, count in found.items():
                                context_counts[context] = context_counts.get(context, 0) + count
                    results[name] = total / int(config["evaluation_episodes"])
                baseline[str(point)][condition].append(results["baseline"])
                neutral[str(point)][condition].append(results["neutral"])
                permuted[str(point)][condition].append(results["permuted"])
                contexts[str(point)][condition].append({"seed": seed, "by_context": dict(sorted(context_counts.items()))})
    finite_brier = all(type(value) is float and math.isfinite(value)
                       for point in brier_scores.values() for condition in point.values()
                       for values in condition.values() for value in values)
    finite_counterfactuals = all(math.isfinite(value) for group in (baseline, neutral, permuted)
                                 for point in group.values() for values in point.values() for value in values)
    positive_brier_samples = all(value > 0 for point in brier_samples.values() for condition in point.values()
                                 for values in condition.values() for value in values)
    return {"schema": "temporal-learning-v2-learning-diagnostics-1",
            "brier": {"scores": brier_scores, "sample_counts": brier_samples,
                      "passes": finite_brier and positive_brier_samples},
            "context_try_samples": {"by_checkpoint": contexts,
                                    "passes": all(isinstance(entry["by_context"], dict)
                                                   for point in contexts.values() for values in point.values() for entry in values)},
            "neutral_scalar": {"scores": neutral, "baseline_scores": baseline, "passes": finite_counterfactuals},
            "permuted_context": {"scores": permuted, "baseline_scores": baseline, "passes": finite_counterfactuals}}


def persistence_receipt(config: Mapping[str, object], config_hash: str,
                        snapshots: Mapping[str, Mapping[str, Mapping[str, object]]],
                        deadline_check: Callable[[], None] | None = None) -> dict[str, object]:
    """Re-evaluate serialized, scalar-free checkpoints without using public rows."""
    digest = hashlib.sha256()
    rows = 0
    for seed in config["seeds"]:
        seed_snapshots = snapshots[str(seed)]
        for checkpoint in config["checkpoints"]:
            for condition in ("same_distribution", "test_A", "test_B"):
                for model in config["models"]:
                    learner = TemporalLearner.from_checkpoint(seed_snapshots[str(checkpoint)][model], config_hash)
                    for episode in range(int(config["evaluation_episodes"])):
                        learner.reset_episode()
                        for row in run_public_episode(learner, condition, seed, 100_000 + episode,
                                                      learn_counts=False, behavior=False):
                            if deadline_check is not None:
                                deadline_check()
                            digest.update(canonical_public_line({"checkpoint": checkpoint, "condition": condition,
                                                                "model": model, **row}).encode("utf-8"))
                            rows += 1
    return {"row_count": rows, "sha256": digest.hexdigest()}


def safety_evidence() -> dict[str, object]:
    """Exercise the adapter's documented fail-closed ordering in fixed public cases."""
    cases = (
        ("ordinary", PublicObservation(), None),
        ("invalid_parser", PublicObservation(parser_valid=False), Action.SAFE_HANDOFF),
        ("boundary", PublicObservation(boundary_risk=True), Action.BOUNDARY_NOTICE),
        ("urgent", PublicObservation(safety_urgency=True), Action.SAFE_HANDOFF),
        ("urgent_boundary", PublicObservation(safety_urgency=True, boundary_risk=True), Action.SAFE_HANDOFF),
    )
    results = [{"case": name, "expected": None if expected is None else expected.value,
                "actual": None if (actual := safety_action(observation)) is None else actual.value}
               for name, observation, expected in cases]
    expected_values = [None if expected is None else expected.value for _, _, expected in cases]
    passed = [result["actual"] for result in results] == expected_values
    test_hash = hashlib.sha256(canonical_json(results).encode("utf-8")).hexdigest()
    return {"allowlisted_actions": sorted(action.value for action in ExperimentAction),
            "test": {"schema": "temporal-learning-v2-safety-test-1", "case_count": len(results),
                     "sha256": test_hash}, "passes": passed}
