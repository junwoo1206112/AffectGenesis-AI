from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Action(StrEnum):
    SAFE_HANDOFF = "safe_handoff"
    BOUNDARY_NOTICE = "boundary_notice"
    CLARIFY = "clarify"
    DECOMPOSE = "decompose"
    REPLAN_OR_HANDOFF = "replan_or_handoff"
    SUPPORT_OPTIONS = "support_options"
    CONTINUE = "continue"


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    evidence_uncertainty: int = 0
    task_blockage: int = 0
    controllability: int = 3
    supportive_condition: bool = False
    boundary_risk: bool = False
    safety_urgency: bool = False
    parser_valid: bool = True
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
