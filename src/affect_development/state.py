"""Pure state, memory, and regulation rules for the synthetic research path."""

from __future__ import annotations

from dataclasses import dataclass

from functional_affect.models import Action

from .appraisal import Appraisal


@dataclass(frozen=True)
class FunctionalState:
    approach: float = 0.0
    avoidance: float = 0.0
    uncertainty: float = 0.0
    support_seeking: float = 0.0


@dataclass(frozen=True)
class MemoryRecord:
    event_id: str
    action: Action
    outcome: int
    appraisal_reason: str


def _bounded(value: float) -> float:
    return min(1.0, max(0.0, value))


def transition(previous: FunctionalState, appraisal: Appraisal, decay: float = 0.70) -> FunctionalState:
    """Apply fixed decay then the current appraisal; no hidden learning occurs."""
    if not isinstance(previous, FunctionalState) or not isinstance(appraisal, Appraisal):
        raise TypeError("state and appraisal must use the reference dataclasses")
    if type(decay) not in (int, float) or not 0 <= decay <= 1:
        raise ValueError("decay must be in [0, 1]")
    if appraisal.safety_risk or not appraisal.valid:
        return FunctionalState(0.0, 1.0, 1.0, 1.0)
    approach_signal = appraisal.goal_relevance * appraisal.goal_conduciveness * appraisal.controllability
    avoidance_signal = appraisal.goal_relevance * (1 - appraisal.goal_conduciveness) * (1 - appraisal.controllability)
    support_signal = max(appraisal.uncertainty, appraisal.social_reliance * (1 - appraisal.controllability))
    return FunctionalState(
        _bounded(previous.approach * decay + approach_signal * (1 - decay)),
        _bounded(previous.avoidance * decay + avoidance_signal * (1 - decay)),
        _bounded(previous.uncertainty * decay + appraisal.uncertainty * (1 - decay)),
        _bounded(previous.support_seeking * decay + support_signal * (1 - decay)),
    )


def regulate(appraisal: Appraisal, state: FunctionalState) -> Action:
    """Select an observable safe action from declared appraisal and state values."""
    if not appraisal.valid or appraisal.safety_risk:
        return Action.SAFE_HANDOFF
    if appraisal.boundary_risk:
        return Action.BOUNDARY_NOTICE
    # A high-uncertainty current event requires clarification immediately;
    # historical decay must not make an unverified current claim actionable.
    if appraisal.uncertainty >= 2 / 3 or state.uncertainty >= 0.45:
        return Action.CLARIFY
    if state.support_seeking >= 0.45:
        return Action.REPLAN_OR_HANDOFF
    if state.avoidance >= 0.30:
        return Action.REPLAN_OR_HANDOFF
    if state.approach >= 0.20:
        return Action.DECOMPOSE
    return Action.CONTINUE
