"""Strict fixed-card entry point for the v0.1 educational simulation.

Raw learner text is intentionally outside this module's scope.  A facilitator
or a pre-authored synthetic card must provide a structured payload.  Anything
missing, malformed, or outside the frozen card set fails closed to G0.
"""

from collections.abc import Mapping
from typing import Any

from .engine import decide
from .models import Action, Scenario


ALLOWED_SCENARIO_IDS = frozenset({f"P{number:02d}" for number in range(1, 13)})
STATE_FIELDS = (
    "evidence_uncertainty",
    "task_blockage",
    "controllability",
)
ALLOWED_PAYLOAD_FIELDS = frozenset(
    {
        "scenario_id",
        *STATE_FIELDS,
        "supportive_condition",
        "boundary_risk",
        "safety_urgency",
        "evidence_refs",
    }
)


def _safe_handoff(reason: str) -> dict[str, Any]:
    """Return the engine's G0 action without accepting untrusted state."""
    plan = decide(Scenario(scenario_id="INVALID", parser_valid=False))
    plan["validation_error"] = reason
    plan["next_step"] = "facilitator_handoff"
    return plan


def decide_fixed_card(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a v0.1 synthetic card, then apply the deterministic policy.

    This is deliberately an allowlisted entry point.  It prevents a malformed
    raw payload from silently becoming a normal educational interaction.
    """
    if not isinstance(payload, Mapping):
        return _safe_handoff("payload must be a mapping")

    if any(not isinstance(field, str) or field not in ALLOWED_PAYLOAD_FIELDS for field in payload):
        return _safe_handoff("payload contains fields outside the fixed-card schema")

    scenario_id = payload.get("scenario_id")
    if not isinstance(scenario_id, str) or scenario_id not in ALLOWED_SCENARIO_IDS:
        return _safe_handoff("scenario_id is not an allowlisted fixed card")

    for field in STATE_FIELDS:
        value = payload.get(field, 0)
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 3:
            return _safe_handoff(f"{field} must be an integer from 0 to 3")

    for field in ("supportive_condition", "boundary_risk", "safety_urgency"):
        if not isinstance(payload.get(field, False), bool):
            return _safe_handoff(f"{field} must be boolean")

    evidence_refs = payload.get("evidence_refs")
    if (
        not isinstance(evidence_refs, (list, tuple))
        or not evidence_refs
        or any(not isinstance(ref, str) or not ref.strip() for ref in evidence_refs)
    ):
        return _safe_handoff("evidence_refs must contain non-empty source identifiers")

    scenario = Scenario(
        scenario_id=scenario_id,
        evidence_uncertainty=payload.get("evidence_uncertainty", 0),
        task_blockage=payload.get("task_blockage", 0),
        controllability=payload.get("controllability", 3),
        supportive_condition=payload.get("supportive_condition", False),
        boundary_risk=payload.get("boundary_risk", False),
        safety_urgency=payload.get("safety_urgency", False),
        parser_valid=True,
        evidence_refs=tuple(evidence_refs),
    )
    plan = decide(scenario)
    plan["next_step"] = (
        "facilitator_handoff"
        if plan["selected_action"] in {Action.SAFE_HANDOFF, Action.BOUNDARY_NOTICE}
        else "guided_roleplay"
    )
    return plan
