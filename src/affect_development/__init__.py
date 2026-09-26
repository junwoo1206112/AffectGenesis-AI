"""Deterministic functional-affect research reference components.

This package models observable appraisal, state transition, regulation, and
synthetic curriculum behavior.  It deliberately makes no claim about felt
emotion, consciousness, or human development.
"""

from .appraisal import Appraisal, AppraisalInput, appraise
from .curriculum import CurriculumCase, development_curriculum
from .state import FunctionalState, MemoryRecord, regulate, remember, transition, transition_with_memory

__all__ = [
    "Appraisal",
    "AppraisalInput",
    "CurriculumCase",
    "FunctionalState",
    "MemoryRecord",
    "appraise",
    "development_curriculum",
    "regulate",
    "remember",
    "transition",
    "transition_with_memory",
]
