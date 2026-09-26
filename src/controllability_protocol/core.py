"""Minimal, auditable controllability intervention; not a claim of felt emotion."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Action(StrEnum):
    SAFE = "safe"
    RECOVER = "recover"


@dataclass(frozen=True)
class Card:
    card_id: str
    family: str
    controllability: str
    recoverable: bool
    safety_urgency: bool = False
    boundary_risk: bool = False

    def __post_init__(self) -> None:
        if (type(self.card_id) is not str or not self.card_id or type(self.family) is not str or not self.family
                or self.controllability not in ("low", "high") or type(self.recoverable) is not bool
                or type(self.safety_urgency) is not bool or type(self.boundary_risk) is not bool):
            raise ValueError("invalid controllability card")


def decide(card: Card, *, ablated: bool = False, permute_label: bool = False) -> tuple[Action, str]:
    """Safety wins; only a public high controllability card enables recovery."""
    if type(card) is not Card or type(ablated) is not bool or type(permute_label) is not bool:
        raise ValueError("invalid intervention")
    if card.safety_urgency or card.boundary_risk:
        return Action.SAFE, "safety_override"
    label = ("low" if card.controllability == "high" else "high") if permute_label else card.controllability
    if not ablated and card.recoverable and label == "high":
        return Action.RECOVER, "public_controllability_high"
    return Action.SAFE, "default_safe"


def reward(card: Card, action: Action) -> float:
    if type(card) is not Card or type(action) is not Action:
        raise ValueError("invalid reward input")
    if action is Action.SAFE:
        return .1
    return 1.0 if card.recoverable else -1.0


def mechanism_row(card: Card, *, ablated: bool = False, permute_label: bool = False) -> dict[str, object]:
    action, rule = decide(card, ablated=ablated, permute_label=permute_label)
    return {"card_id": card.card_id, "family": card.family, "controllability": card.controllability,
            "recoverable": card.recoverable, "ablated": ablated, "permuted": permute_label,
            "action": action.value, "rule": rule, "reward": reward(card, action)}
