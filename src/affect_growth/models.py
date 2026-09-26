from __future__ import annotations

from dataclasses import dataclass

from functional_affect.models import Action


ACTIONS = (Action.CLARIFY, Action.REPLAN_OR_HANDOFF, Action.DECOMPOSE)
CLASSES = (0, 1, 2)
UNKNOWN = 3
VOCAB_SIZE = 8


@dataclass(frozen=True)
class Observation:
    cues: tuple[int, int, int, int]
    evidence_refs: tuple[str, ...] = ("synthetic",)
    parser_valid: bool = True
    safety_urgency: bool = False
    boundary_risk: bool = False


@dataclass(frozen=True)
class Feedback:
    label: int
    action: Action
    outcome: int


@dataclass(frozen=True)
class Case:
    observation: Observation
    feedback: Feedback
    target: int
    acceptable: tuple[Action, ...]
    family: int
    phase: str


@dataclass(frozen=True)
class Prediction:
    label: int
    posterior: tuple[float, float, float]
    action: Action
    expected_success: float
    frustration: float
