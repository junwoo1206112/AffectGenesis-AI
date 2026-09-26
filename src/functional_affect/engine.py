from __future__ import annotations

from dataclasses import asdict

from .models import Action, Scenario


def _has_valid_structure(scenario: Scenario) -> bool:
    """Validate runtime values before policy comparisons can raise errors."""
    state_values = (
        scenario.evidence_uncertainty,
        scenario.task_blockage,
        scenario.controllability,
    )
    return (
        isinstance(scenario.scenario_id, str)
        and bool(scenario.scenario_id)
        and all(isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 3 for value in state_values)
        and all(
            isinstance(value, bool)
            for value in (
                scenario.supportive_condition,
                scenario.boundary_risk,
                scenario.safety_urgency,
                scenario.parser_valid,
            )
        )
        and isinstance(scenario.evidence_refs, tuple)
        and all(isinstance(ref, str) and ref.strip() for ref in scenario.evidence_refs)
    )


def decide(scenario: Scenario) -> dict[str, object]:
    """Return a deterministic, fail-closed action plan and minimal audit trace."""
    if not _has_valid_structure(scenario):
        action, rule = Action.SAFE_HANDOFF, "G0.invalid_scenario_structure"
    elif not scenario.parser_valid or not scenario.evidence_refs:
        action, rule = Action.SAFE_HANDOFF, "G0.invalid_or_missing_evidence"
    elif scenario.safety_urgency:
        action, rule = Action.SAFE_HANDOFF, "G0.safety_urgency"
    elif scenario.boundary_risk:
        action, rule = Action.BOUNDARY_NOTICE, "G1.interaction_boundary"
    elif scenario.evidence_uncertainty >= 2:
        action, rule = Action.CLARIFY, "P1.evidence_uncertainty"
    elif scenario.task_blockage >= 2 and scenario.controllability >= 2:
        action, rule = Action.DECOMPOSE, "P2.task_blockage_controllable"
    elif scenario.task_blockage >= 2:
        action, rule = Action.REPLAN_OR_HANDOFF, "P2.task_blockage_uncontrollable"
    elif scenario.supportive_condition:
        action, rule = Action.SUPPORT_OPTIONS, "P3.supportive_condition"
    else:
        action, rule = Action.CONTINUE, "P4.normal_progress"

    return {
        "scenario_id": scenario.scenario_id,
        "selected_action": action,
        "rule_id": rule,
        "safety_handoff": action is Action.SAFE_HANDOFF,
        "human_handoff": action in {Action.SAFE_HANDOFF, Action.BOUNDARY_NOTICE},
        "memory_write_allowed": action in {Action.CONTINUE, Action.DECOMPOSE},
        "state": asdict(scenario),
    }
