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


def remember(history: tuple[MemoryRecord, ...], record: MemoryRecord, capacity: int = 8) -> tuple[MemoryRecord, ...]:
    """Append one synthetic feedback record without storing person data."""
    if (not isinstance(history, tuple) or not all(isinstance(item, MemoryRecord) for item in history)
            or not isinstance(record, MemoryRecord) or type(capacity) is not int or not 1 <= capacity <= 32
            or not isinstance(record.event_id, str) or not record.event_id.strip()
            or type(record.action) is not Action or type(record.outcome) is not int or record.outcome not in (0, 1)
            or not isinstance(record.appraisal_reason, str) or not record.appraisal_reason):
        raise ValueError("invalid synthetic memory record")
    return (*history, record)[-capacity:]


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


def transition_with_memory(previous: FunctionalState, appraisal: Appraisal,
                           history: tuple[MemoryRecord, ...], decay: float = 0.70) -> FunctionalState:
    """Use only matching synthetic outcome records after all safety checks."""
    base = transition(previous, appraisal, decay)
    if appraisal.safety_risk or not appraisal.valid:
        return base
    if not isinstance(history, tuple) or not all(isinstance(item, MemoryRecord) for item in history):
        raise ValueError("invalid synthetic memory history")
    matching = [item.outcome for item in history if item.event_id == appraisal.event_id]
    if not matching:
        return base
    outcome_bias = sum(matching) / len(matching) - 0.5
    return FunctionalState(_bounded(base.approach + 0.2 * outcome_bias),
                           _bounded(base.avoidance - 0.2 * outcome_bias),
                           base.uncertainty, base.support_seeking)


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
