"""Small supervised learners; no network, human data, or hidden-label inference."""
from __future__ import annotations

from copy import deepcopy
import math

from functional_affect.models import Action

from .models import ACTIONS, CLASSES, UNKNOWN, VOCAB_SIZE, Feedback, Observation, Prediction
from .safety import safety_action


def _feedback_valid(feedback: object) -> bool:
    return (
        isinstance(feedback, Feedback)
        and type(feedback.label) is int and feedback.label in CLASSES
        and type(feedback.action) is Action and feedback.action in ACTIONS
        and type(feedback.outcome) is int and feedback.outcome in (0, 1)
    )


class Learner:
    """NB + conditional Beta estimates, frozen prior, or raw-experience 5NN."""

    def __init__(self, mode: str = "learned") -> None:
        if type(mode) is not str or mode not in ("learned", "frozen", "memory"):
            raise ValueError("invalid learner mode")
        self.mode = mode
        self.frustration = 0.0
        self.class_counts = [0 for _ in CLASSES]
        self.feature_counts = [[[0] * VOCAB_SIZE for _ in range(4)] for _ in CLASSES]
        self.action_counts = [[[0, 0] for _ in ACTIONS] for _ in CLASSES]
        self.memory: list[dict[str, object]] = []

    def _check_state(self) -> None:
        if (type(self.frustration) not in (float, int)
                or not math.isfinite(self.frustration) or not 0 <= self.frustration <= 1):
            raise ValueError("frustration must be finite and in [0, 1]")

    def _estimates(self, observation: Observation) -> tuple[tuple[float, ...], list[float]]:
        if self.mode == "memory":
            neighbors = sorted(
                enumerate(self.memory),
                key=lambda pair: (
                    sum(a != b for a, b in zip(observation.cues, pair[1]["cues"])),
                    pair[0],
                ),
            )[:5]
            if not neighbors:
                return (1 / 3, 1 / 3, 1 / 3), [0.5] * len(ACTIONS)
            posterior = tuple(
                sum(record["label"] == label for _, record in neighbors) / len(neighbors)
                for label in CLASSES
            )
            utility = []
            for action in ACTIONS:
                outcomes = [record["outcome"] for _, record in neighbors if record["action"] == action.value]
                utility.append((1 + sum(outcomes)) / (2 + len(outcomes)))
            return posterior, utility

        total = sum(self.class_counts)
        logs = []
        for label in CLASSES:
            count = self.class_counts[label]
            logp = math.log(count + 1) - math.log(total + len(CLASSES))
            for index, cue in enumerate(observation.cues):
                logp += math.log(self.feature_counts[label][index][cue] + 1) - math.log(count + VOCAB_SIZE)
            logs.append(logp)
        weights = [math.exp(value - max(logs)) for value in logs]
        posterior = tuple(value / sum(weights) for value in weights)
        utility = [
            sum(posterior[label] * (1 + self.action_counts[label][index][1])
                / (2 + sum(self.action_counts[label][index])) for label in CLASSES)
            for index in range(len(ACTIONS))
        ]
        return posterior, utility

    def predict(self, observation: Observation) -> Prediction:
        blocked = safety_action(observation)
        if blocked is not None:
            return Prediction(UNKNOWN, (1 / 3, 1 / 3, 1 / 3), blocked, 0.0, self.frustration)
        self._check_state()
        posterior, utility = self._estimates(observation)
        label = max(CLASSES, key=lambda value: posterior[value])
        if posterior[label] < 0.6:
            label, action = UNKNOWN, Action.CLARIFY
        else:
            scores = [value + (-0.1 if action is Action.DECOMPOSE else 0.05) * self.frustration
                      for action, value in zip(ACTIONS, utility)]
            action = ACTIONS[max(range(len(ACTIONS)), key=lambda index: scores[index])]
        action = safety_action(observation) or action
        expected = utility[ACTIONS.index(action)] if action in ACTIONS else 0.0
        return Prediction(label, posterior, action, expected, self.frustration)

    def expected_success(self, observation: Observation, action: Action) -> float:
        """Read the pre-update prediction for an externally logged action."""
        if safety_action(observation) is not None:
            return 0.0
        if type(action) is not Action or action not in ACTIONS:
            raise ValueError("invalid logged action")
        self._check_state()
        _, utility = self._estimates(observation)
        return utility[ACTIONS.index(action)]

    def learn(self, observation: Observation, feedback: Feedback, update: bool = True) -> None:
        if safety_action(observation) is not None:
            return
        if not _feedback_valid(feedback) or type(update) is not bool:
            raise ValueError("invalid feedback or update flag")
        self._check_state()
        _, utility = self._estimates(observation)
        action_index = ACTIONS.index(feedback.action)
        expected = utility[action_index]
        self.frustration = min(1.0, max(0.0, 0.8 * self.frustration + 0.2 * (expected - feedback.outcome)))
        if not update or self.mode == "frozen":
            return
        if self.mode == "memory":
            self.memory.append({"cues": list(observation.cues), "label": feedback.label,
                                "action": feedback.action.value, "outcome": feedback.outcome})
            return
        self.class_counts[feedback.label] += 1
        for index, cue in enumerate(observation.cues):
            self.feature_counts[feedback.label][index][cue] += 1
        self.action_counts[feedback.label][action_index][feedback.outcome] += 1

    def reset_state(self) -> None:
        self.frustration = 0.0

    def clone(self) -> Learner:
        return deepcopy(self)

    def to_dict(self, config_hash: str) -> dict[str, object]:
        data = deepcopy({"schema": 1, "config_hash": config_hash, "mode": self.mode,
                         "frustration": self.frustration, "class_counts": self.class_counts,
                         "feature_counts": self.feature_counts, "action_counts": self.action_counts,
                         "memory": self.memory})
        self.from_dict(data, config_hash)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, object], config_hash: str) -> Learner:
        keys = {"schema", "config_hash", "mode", "frustration", "class_counts",
                "feature_counts", "action_counts", "memory"}
        if (type(data) is not dict or set(data) != keys
                or type(config_hash) is not str or not config_hash
                or type(data["config_hash"]) is not str or data["config_hash"] != config_hash
                or type(data["schema"]) is not int or data["schema"] != 1):
            raise ValueError("checkpoint schema or configuration mismatch")
        result = cls(data["mode"])
        result.frustration = data["frustration"]
        result._check_state()

        def counts(value: object, shape: tuple[int, ...]) -> bool:
            if not shape:
                return type(value) is int and value >= 0
            return type(value) is list and len(value) == shape[0] and all(
                counts(item, shape[1:]) for item in value
            )

        if not (counts(data["class_counts"], (3,))
                and counts(data["feature_counts"], (3, 4, VOCAB_SIZE))
                and counts(data["action_counts"], (3, len(ACTIONS), 2))
                and type(data["memory"]) is list):
            raise ValueError("invalid checkpoint count structure")
        for label in CLASSES:
            count = data["class_counts"][label]
            if (any(sum(row) != count for row in data["feature_counts"][label])
                    or sum(sum(row) for row in data["action_counts"][label]) != count):
                raise ValueError("inconsistent checkpoint counts")
        for record in data["memory"]:
            if (type(record) is not dict or set(record) != {"cues", "label", "action", "outcome"}
                    or type(record["cues"]) is not list or len(record["cues"]) != 4
                    or any(type(cue) is not int or not 0 <= cue < VOCAB_SIZE for cue in record["cues"])
                    or type(record["label"]) is not int or record["label"] not in CLASSES
                    or type(record["action"]) is not str or record["action"] not in [a.value for a in ACTIONS]
                    or type(record["outcome"]) is not int or record["outcome"] not in (0, 1)):
                raise ValueError("invalid checkpoint memory record")
        if ((result.mode != "learned" and any(data["class_counts"]))
                or (result.mode != "memory" and data["memory"])):
            raise ValueError("checkpoint statistics do not match mode")
        for name in ("class_counts", "feature_counts", "action_counts", "memory"):
            setattr(result, name, deepcopy(data[name]))
        return result
