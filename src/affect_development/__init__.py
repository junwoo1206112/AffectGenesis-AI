"""Deterministic functional-affect research reference components.

This package models observable appraisal, state transition, regulation, and
synthetic curriculum behavior.  It deliberately makes no claim about felt
emotion, consciousness, or human development.
"""

from .appraisal import Appraisal, AppraisalInput, appraise
from .certainty_evaluation import (evaluate_certainty_preregistration,
                                   verify_certainty_artifact, write_certainty_artifact)
from .curriculum import CurriculumCase, development_curriculum
from .runner import run_curriculum
from .state import FunctionalState, MemoryRecord, regulate, remember, transition, transition_with_memory

__all__ = [
    "Appraisal",
    "AppraisalInput",
    "CurriculumCase",
    "FunctionalState",
    "MemoryRecord",
    "appraise",
    "development_curriculum",
    "evaluate_certainty_preregistration",
    "regulate",
    "run_curriculum",
    "remember",
    "transition",
    "transition_with_memory",
    "verify_certainty_artifact",
    "write_certainty_artifact",
]
