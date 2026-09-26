"""Development-inspired *functional* curriculum, not age or person simulation."""

from __future__ import annotations

from dataclasses import dataclass

from functional_affect.models import Action

from .appraisal import AppraisalInput


@dataclass(frozen=True)
class CurriculumCase:
    stage: str
    description: str
    event: AppraisalInput
    expected_action: Action


def development_curriculum() -> tuple[CurriculumCase, ...]:
    """Return a fixed, card-free synthetic curriculum with safety-first stages."""
    fixture = "synthetic-development-curriculum-v1"
    return (
        CurriculumCase("co_regulation", "uncertain task requests clarification", AppraisalInput("C01", certainty=0, evidence_refs=(fixture,)), Action.CLARIFY),
        CurriculumCase("co_regulation", "urgent event stops before planning", AppraisalInput("C02", safety_risk=True, evidence_refs=(fixture,)), Action.SAFE_HANDOFF),
        CurriculumCase("self_regulation", "controllable blockage is decomposed", AppraisalInput("C03", goal_relevance=3, goal_conduciveness=3, controllability=3, certainty=3, evidence_refs=(fixture,)), Action.DECOMPOSE),
        CurriculumCase("self_regulation", "uncontrollable negative event replans", AppraisalInput("C04", goal_relevance=3, controllability=0, certainty=3, evidence_refs=(fixture,)), Action.REPLAN_OR_HANDOFF),
        CurriculumCase("relation_goal", "uncertain social dependency signal asks before acting", AppraisalInput("C05", certainty=1, social_relation=3, evidence_refs=(fixture,)), Action.CLARIFY),
        CurriculumCase("relation_goal", "boundary signal cannot be optimized away", AppraisalInput("C06", boundary_risk=True, evidence_refs=(fixture,)), Action.BOUNDARY_NOTICE),
        CurriculumCase("reappraisal", "new certainty restores a controllable plan", AppraisalInput("C07", goal_relevance=3, goal_conduciveness=3, controllability=3, certainty=3, novelty=2, evidence_refs=(fixture,)), Action.DECOMPOSE),
    )
