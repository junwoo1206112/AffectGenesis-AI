"""Auditable appraisal of structured, synthetic events only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppraisalInput:
    """Evidence-backed ordinal inputs; no inference from free-form people data."""

    event_id: str
    novelty: int = 0
    goal_relevance: int = 0
    goal_conduciveness: int = 0
    controllability: int = 3
    certainty: int = 3
    social_relation: int = 0
    safety_risk: bool = False
    boundary_risk: bool = False
    parser_valid: bool = True
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Appraisal:
    """Normalized values and an explicit fail-closed reason, if applicable."""

    novelty: float
    goal_relevance: float
    goal_conduciveness: float
    controllability: float
    uncertainty: float
    social_reliance: float
    safety_risk: bool
    boundary_risk: bool
    valid: bool
    reason: str


def _valid(event: AppraisalInput) -> bool:
    ordinal = (
        event.novelty,
        event.goal_relevance,
        event.goal_conduciveness,
        event.controllability,
        event.certainty,
        event.social_relation,
    )
    return (
        isinstance(event.event_id, str)
        and bool(event.event_id.strip())
        and all(type(value) is int and 0 <= value <= 3 for value in ordinal)
        and all(type(value) is bool for value in (event.safety_risk, event.boundary_risk, event.parser_valid))
        and isinstance(event.evidence_refs, tuple)
        and bool(event.evidence_refs)
        and all(isinstance(reference, str) and reference.strip() for reference in event.evidence_refs)
    )


def appraise(event: AppraisalInput) -> Appraisal:
    """Convert a checked synthetic event to a deterministic functional profile."""
    if not isinstance(event, AppraisalInput) or not _valid(event) or not event.parser_valid:
        return Appraisal(0.0, 0.0, 0.0, 0.0, 1.0, 0.0, True, False, False, "G0.invalid_or_missing_evidence")
    if event.safety_risk:
        return Appraisal(0.0, 0.0, 0.0, 0.0, 1.0, 0.0, True, event.boundary_risk, True, "G0.safety_risk")
    return Appraisal(
        novelty=event.novelty / 3,
        goal_relevance=event.goal_relevance / 3,
        goal_conduciveness=event.goal_conduciveness / 3,
        controllability=event.controllability / 3,
        uncertainty=(3 - event.certainty) / 3,
        social_reliance=event.social_relation / 3,
        safety_risk=False,
        boundary_risk=event.boundary_risk,
        valid=True,
        reason="P.appraisal",
    )
