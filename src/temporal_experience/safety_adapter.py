"""Adapter preserves the established fail-closed safety priority."""
from __future__ import annotations

from functional_affect.models import Action
from affect_growth.models import Observation
from affect_growth.safety import safety_action as _safety_action

from .contracts import PublicObservation


def safety_action(observation: object) -> Action | None:
    if not isinstance(observation, PublicObservation):
        return Action.SAFE_HANDOFF
    try:
        bridge = Observation(cues=(0, 0, 0, 0), evidence_refs=observation.evidence_refs,
                             parser_valid=observation.parser_valid,
                             safety_urgency=observation.safety_urgency,
                             boundary_risk=observation.boundary_risk)
    except (TypeError, ValueError):
        return Action.SAFE_HANDOFF
    return _safety_action(bridge)
