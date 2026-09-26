"""Deterministic, auditable functional-affect reference engine."""

from .engine import decide
from .models import Action, Scenario

__all__ = ["Action", "Scenario", "decide"]
