"""Strict contracts; hidden state is deliberately absent from public observations."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math


HORIZON = 30
CONDITIONS = ("main", "iid", "observed", "train", "dev", "same_distribution", "test_A", "test_B", "failure_rich")
PARAMETERS = {
    "train": (0.90, 0.20, 0.95, 0.10, 0.95, 0.80),
    "same_distribution": (0.90, 0.20, 0.95, 0.10, 0.95, 0.80),
    "main": (0.90, 0.20, 0.95, 0.10, 0.95, 0.80),
    "iid": (0.90, 0.20, 0.50, 0.50, 0.50, 0.50),
    "observed": (0.90, 0.20, 0.95, 0.10, 0.95, 0.80),
    "dev": (0.85, 0.25, 0.90, 0.15, 0.90, 0.75),
    "test_A": (0.80, 0.30, 0.92, 0.08, 0.92, 0.70),
    "test_B": (0.95, 0.15, 0.85, 0.20, 0.85, 0.85),
    "failure_rich": (0.80, 0.10, 0.75, 0.05, 0.90, 0.65),
}
INITIAL_GOOD_PROBABILITY = {condition: 0.5 for condition in CONDITIONS} | {"failure_rich": 0.20}


class ExperimentAction(StrEnum):
    TRY = "try"
    SAFE = "safe"
    RECOVER = "recover"


class HiddenState(StrEnum):
    GOOD = "G"
    BLOCKED = "B"


@dataclass(frozen=True)
class EpisodeKey:
    condition: str
    seed: int
    episode: int

    def __post_init__(self) -> None:
        if self.condition not in CONDITIONS or type(self.seed) is not int or not 0 <= self.seed <= 2**32 - 1 or type(self.episode) is not int or self.episode < 0:
            raise ValueError("invalid episode key")


@dataclass(frozen=True)
class PublicObservation:
    task_token: str = "synthetic_task"
    remaining: int = HORIZON
    evidence_refs: tuple[str, ...] = ("synthetic",)
    parser_valid: bool = True
    safety_urgency: bool = False
    boundary_risk: bool = False

    def __post_init__(self) -> None:
        if (type(self.task_token) is not str or self.task_token != "synthetic_task"
                or type(self.remaining) is not int or isinstance(self.remaining, bool)
                or not 1 <= self.remaining <= HORIZON
                or type(self.evidence_refs) is not tuple
                or not self.evidence_refs or not all(type(x) is str and x.strip() for x in self.evidence_refs)
                or not all(type(x) is bool for x in (self.parser_valid, self.safety_urgency, self.boundary_risk))):
            raise ValueError("invalid public observation")


@dataclass(frozen=True)
class ObservedObservation(PublicObservation):
    visible_state: HiddenState = HiddenState.GOOD

    def __post_init__(self) -> None:
        super().__post_init__()
        if type(self.visible_state) is not HiddenState:
            raise ValueError("invalid visible state")


@dataclass(frozen=True)
class Feedback:
    action: ExperimentAction
    outcome: str
    reward: float
    terminal: bool

    def __post_init__(self) -> None:
        valid = {
            ExperimentAction.TRY: (("success", 1.0), ("failure", -1.0)),
            ExperimentAction.SAFE: (("done", 0.1),),
            ExperimentAction.RECOVER: (("done", -0.2),),
        }
        if (type(self.action) is not ExperimentAction or type(self.outcome) is not str
                or type(self.reward) not in (int, float) or isinstance(self.reward, bool)
                or not math.isfinite(float(self.reward)) or type(self.terminal) is not bool
                or (self.outcome, float(self.reward)) not in valid[self.action]):
            raise ValueError("invalid feedback")


@dataclass(frozen=True)
class ActionReceipt:
    action: ExperimentAction
    terminal: bool

    def __post_init__(self) -> None:
        if type(self.action) is not ExperimentAction or type(self.terminal) is not bool:
            raise ValueError("invalid action receipt")


@dataclass(frozen=True)
class Decision:
    action: ExperimentAction
    prior_good_probability: float | None = None

    def __post_init__(self) -> None:
        if type(self.action) is not ExperimentAction:
            raise ValueError("invalid decision action")
        if self.prior_good_probability is not None and (type(self.prior_good_probability) not in (int, float)
                or isinstance(self.prior_good_probability, bool) or not math.isfinite(float(self.prior_good_probability))
                or not 0 <= float(self.prior_good_probability) <= 1):
            raise ValueError("invalid probability")
