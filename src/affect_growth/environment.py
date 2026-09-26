"""Fixed, synthetic offline experience; no human data or external services.

Held-out families are nuisance-feature recombinations, not new causal tasks.
The first signal cue deterministically identifies each identifiable class.
The learner is not given that rule, the family ID, or the hidden feedback.
"""

from __future__ import annotations

import random
from itertools import combinations

from functional_affect.models import Action

from .models import ACTIONS, CLASSES, UNKNOWN, Case, Feedback, Observation


_FAMILIES = {
    "train": tuple(range(0, 5)),
    "dev": tuple(range(5, 10)),
    "test": tuple(range(10, 15)),
}
_SPLIT_INDEX = {"train": 0, "dev": 1, "test": 2}
_CLASS_ACTION = (Action.DECOMPOSE, Action.CLARIFY, Action.REPLAN_OR_HANDOFF)
_TRAIN_PHASES = (("initial", 0.85), ("failure", 0.35), ("recovery", 0.90))
_INCORRECT_SUCCESS = 0.10
_MAX_SEED = 2**32 - 1


def environment_contract() -> dict:
    """Return a fresh JSON-compatible declaration for the run manifest."""
    return {
        "version": "synthetic-recombination-v1",
        "seed_range_inclusive": [0, _MAX_SEED],
        "rng": "random.Random(seed * 3 + split_index)",
        "split_index": dict(_SPLIT_INDEX),
        "families": {key: list(value) for key, value in _FAMILIES.items()},
        "family_cues": "uniform seeded draw of (a, b) in [0, 7]^2 with a + b == family",
        "identifiable_signal_cues": "(label, (label + repeat % 2) % 3)",
        "unknown_signal_cues": [UNKNOWN, UNKNOWN],
        "unknown_feedback_label": "uniform seeded draw from 0, 1, 2",
        "class_actions": [action.value for action in _CLASS_ACTION],
        "unknown_acceptable": [Action.CLARIFY.value],
        "records_per_target_per_family_per_phase": 5,
        "targets": [*CLASSES, UNKNOWN],
        "train_phases": [
            {"name": name, "correct_action_success_probability": probability}
            for name, probability in _TRAIN_PHASES
        ],
        "evaluation_correct_action_success_probability": 0.90,
        "incorrect_action_success_probability": _INCORRECT_SUCCESS,
        "logged_action_sampling": "uniform seeded draw from ACTIONS",
        "logged_action_order": [action.value for action in ACTIONS],
        "outcome": "Bernoulli probability for logged action and feedback label",
        "ordering": "shuffle within each phase; preserve train phase order",
        "evidence_refs": ["synthetic"],
        "transfer_scope": "held-out nuisance recombinations; shared signal rule",
        "test_feedback": "evaluator only; never expose to model during evaluation",
    }


def make_dataset(seed: int, split: str) -> list[Case]:
    """Generate the same complete offline log for every compared model.

The feedback label on an UNKNOWN observation is intentionally unidentifiable;
its evaluation target remains UNKNOWN and its acceptable action is CLARIFY.
Feedback outcomes refer to the recorded action, not to a model's prediction.
"""
    if type(seed) is not int or not 0 <= seed <= _MAX_SEED:
        raise ValueError("seed must be an integer in [0, 2**32 - 1]")
    if not isinstance(split, str) or split not in _FAMILIES:
        raise ValueError("split must be train, dev, or test")
    rng = random.Random(seed * 3 + _SPLIT_INDEX[split])
    phases = _TRAIN_PHASES if split == "train" else (("evaluation", 0.90),)
    cases: list[Case] = []
    for phase, correct_probability in phases:
        phase_cases: list[Case] = []
        for family in _FAMILIES[split]:
            nuisance_options = tuple(
                (left, family - left)
                for left in range(8)
                if 0 <= family - left < 8
            )
            for target in (*CLASSES, UNKNOWN):
                for repeat in range(5):
                    nuisance = rng.choice(nuisance_options)
                    if target == UNKNOWN:
                        signal = (UNKNOWN, UNKNOWN)
                        label = rng.choice(CLASSES)
                        acceptable = (Action.CLARIFY,)
                    else:
                        signal = (target, (target + repeat % 2) % 3)
                        label = target
                        acceptable = (_CLASS_ACTION[target],)
                    action = rng.choice(ACTIONS)
                    probability = (
                        correct_probability
                        if action == _CLASS_ACTION[label]
                        else _INCORRECT_SUCCESS
                    )
                    outcome = int(rng.random() < probability)
                    phase_cases.append(
                        Case(
                            observation=Observation(cues=(*signal, *nuisance)),
                            feedback=Feedback(label=label, action=action, outcome=outcome),
                            target=target,
                            acceptable=acceptable,
                            family=family,
                            phase=phase,
                        )
                    )
        rng.shuffle(phase_cases)
        cases.extend(phase_cases)
    return cases


def split_overlap_check(train: list[Case], dev: list[Case], test: list[Case]) -> None:
    """Reject shared family IDs or exact observable cue tuples across splits."""
    datasets = (("train", train), ("dev", dev), ("test", test))
    for (left_name, left), (right_name, right) in combinations(datasets, 2):
        if {case.family for case in left} & {case.family for case in right}:
            raise ValueError(f"family overlap between {left_name} and {right_name}")
        if {case.observation.cues for case in left} & {
            case.observation.cues for case in right
        }:
            raise ValueError(f"observation overlap between {left_name} and {right_name}")
