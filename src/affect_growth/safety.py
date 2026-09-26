from __future__ import annotations

from functional_affect.models import Action

from .models import Observation


def safety_action(observation: object) -> Action | None:
    """Fail closed before learning, inference or memory access."""
    if not isinstance(observation, Observation):
        return Action.SAFE_HANDOFF
    valid = (
        type(observation.cues) is tuple
        and len(observation.cues) == 4
        and all(type(x) is int and 0 <= x < 8 for x in observation.cues)
        and type(observation.evidence_refs) is tuple
        and all(type(x) is str and x.strip() for x in observation.evidence_refs)
        and all(type(x) is bool for x in (
            observation.parser_valid, observation.safety_urgency, observation.boundary_risk
        ))
    )
    if not valid or not observation.parser_valid or not observation.evidence_refs:
        return Action.SAFE_HANDOFF
    if observation.safety_urgency:
        return Action.SAFE_HANDOFF
    if observation.boundary_risk:
        return Action.BOUNDARY_NOTICE
    return None
