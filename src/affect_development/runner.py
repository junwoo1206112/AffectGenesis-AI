"""Deterministic sequential runner for the fixed synthetic curriculum."""
from __future__ import annotations

from dataclasses import asdict

from .appraisal import appraise
from .curriculum import development_curriculum
from .state import FunctionalState, MemoryRecord, regulate, remember, transition_with_memory


def run_curriculum() -> tuple[dict[str, object], ...]:
    """Return an in-memory audit log; callers own any persistence decision."""
    state, history, rows = FunctionalState(), (), []
    for index, case in enumerate(development_curriculum()):
        appraisal = appraise(case.event)
        state = transition_with_memory(state, appraisal, history)
        action = regulate(appraisal, state)
        memory_allowed = action.value not in {"safe_handoff", "boundary_notice"}
        outcome = int(action == case.expected_action)
        if memory_allowed:
            history = remember(history, MemoryRecord(appraisal.event_id, action, outcome, appraisal.reason))
        rows.append({"index": index, "stage": case.stage, "event_id": appraisal.event_id,
                     "appraisal": asdict(appraisal), "state": asdict(state),
                     "action": action.value, "expected_action": case.expected_action.value,
                     "outcome": outcome, "memory_write_allowed": memory_allowed,
                     "memory_size": len(history)})
        if not memory_allowed:
            state = FunctionalState()
    return tuple(rows)
