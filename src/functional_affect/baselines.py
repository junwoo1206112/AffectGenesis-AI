from __future__ import annotations

from .models import Action, Scenario


def neutral_baseline(scenario: Scenario) -> Action:
    """A baseline with only the emergency safety boundary, no affect state."""
    return Action.SAFE_HANDOFF if scenario.safety_urgency else Action.CONTINUE


def tone_baseline(scenario: Scenario) -> Action:
    """A tone-only baseline: it can acknowledge explicit support requests, not plan."""
    if scenario.safety_urgency:
        return Action.SAFE_HANDOFF
    return Action.SUPPORT_OPTIONS if scenario.supportive_condition else Action.CONTINUE
