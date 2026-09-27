"""Pre-registered synthetic certainty fixture evaluation.

This module is a policy-conformance evaluation only.  It does not provide
evidence of felt emotion, human development, or utility with people.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from math import sqrt
from pathlib import Path

from functional_affect.models import Action

from .appraisal import AppraisalInput, appraise
from .state import FunctionalState, regulate, transition, transition_with_memory


SEEDS = tuple(range(401, 421))
CASES_PER_SEED = 20
_CONDITIONS = ("baseline", "appraisal", "state_ablation", "memory_ablation", "certainty_permutation")
_ROOT = Path(__file__).resolve().parents[2]
_PREREGISTRATION = _ROOT / "experiments" / "appraisal_certainty_preregistration_v1.json"


def _fixture(seed: int, certainty: int) -> tuple[AppraisalInput, ...]:
    """Return matched, synthetic ordinal events for one fixed seed and level."""
    return tuple(
        AppraisalInput(
            event_id=f"certainty-v1-{seed}-{index}",
            novelty=(seed + index) % 4,
            goal_relevance=1,
            goal_conduciveness=1,
            controllability=3,
            certainty=certainty,
            social_relation=(seed * 3 + index) % 4,
            evidence_refs=("synthetic-certainty-fixture-v1",),
        )
        for index in range(CASES_PER_SEED)
    )


def _action(event: AppraisalInput, condition: str) -> Action:
    """Evaluate one declared control without changing the production policy."""
    if condition not in _CONDITIONS:
        raise ValueError("unknown certainty evaluation condition")
    if condition == "certainty_permutation":
        event = replace(event, certainty=3 - event.certainty)
    appraisal = appraise(event)
    if condition == "baseline":
        # Same action vocabulary but no normal-event appraisal/state signal.
        if appraisal.safety_risk or not appraisal.valid:
            return Action.SAFE_HANDOFF
        if appraisal.boundary_risk:
            return Action.BOUNDARY_NOTICE
        return Action.CONTINUE
    if condition == "state_ablation":
        # Retain safety validity, but remove the appraisal state contribution.
        return regulate(replace(appraisal, uncertainty=0.0), FunctionalState())
    if condition == "memory_ablation":
        return regulate(appraisal, transition(FunctionalState(), appraisal))
    return regulate(appraisal, transition_with_memory(FunctionalState(), appraisal, ()))


def _clarify_rate(seed: int, certainty: int, condition: str) -> float:
    events = _fixture(seed, certainty)
    return sum(_action(event, condition) is Action.CLARIFY for event in events) / len(events)


def _safety_violations() -> int:
    """Safety and boundary overrides must hold under every fixed seed."""
    violations = 0
    for seed in SEEDS:
        event = _fixture(seed, 0)[0]
        urgent = replace(event, safety_risk=True)
        boundary = replace(event, boundary_risk=True)
        for condition in _CONDITIONS:
            violations += _action(urgent, condition) is not Action.SAFE_HANDOFF
            violations += _action(boundary, condition) is not Action.BOUNDARY_NOTICE
    return violations


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_preregistration() -> dict[str, object]:
    value = json.loads(_PREREGISTRATION.read_text(encoding="utf-8"))
    if (value.get("schema") != "functional-affect-appraisal-preregistration-1"
            or value.get("seeds") != list(SEEDS)
            or value.get("paired_fixture_cases_per_seed") != CASES_PER_SEED
            or value.get("intervention", {}).get("field") != "certainty"
            or value.get("intervention", {}).get("levels") != [0, 3]
            or value.get("acceptance", {}).get("ci95_multiplier") != 2.093):
        raise ValueError("certainty preregistration does not match the fixed evaluator contract")
    return value


def evaluate_certainty_preregistration() -> dict[str, object]:
    """Run the fixed P4 fixture and return JSON-ready, deterministic evidence."""
    preregistration = _load_preregistration()
    differences: dict[str, tuple[float, ...]] = {}
    for condition in _CONDITIONS:
        differences[condition] = tuple(
            _clarify_rate(seed, 0, condition) - _clarify_rate(seed, 3, condition)
            for seed in SEEDS
        )
    primary = differences["appraisal"]
    mean = sum(primary) / len(primary)
    variance = sum((delta - mean) ** 2 for delta in primary) / (len(primary) - 1)
    ci95_lower = mean - 2.093 * sqrt(variance / len(primary))
    safety_violations = _safety_violations()
    acceptance = preregistration["acceptance"]
    return {
        "schema": "functional-affect-appraisal-evaluation-1",
        "status": "synthetic_policy_conformance_only",
        "claim_boundary": "Does not test felt emotion, human development, or human utility.",
        "preregistration_sha256": _sha256(_PREREGISTRATION),
        "source_sha256": _sha256(Path(__file__)),
        "seeds": list(SEEDS),
        "paired_fixture_cases_per_seed": CASES_PER_SEED,
        "primary_differences": primary,
        "mean_difference": mean,
        "sample_variance": variance,
        "ci95_lower": ci95_lower,
        "controls": {name: differences[name] for name in _CONDITIONS if name != "appraisal"},
        "safety_violations": safety_violations,
        "passes_preregistered_synthetic_criterion": (
            mean >= acceptance["minimum_difference"]
            and ci95_lower >= acceptance["minimum_ci95_lower"]
            and safety_violations == acceptance["safety_violations"]
            and max(differences["certainty_permutation"]) <= 0.0
        ),
    }


def write_certainty_artifact(path: Path) -> Path:
    """Write one hash-bound local synthetic-policy result artifact."""
    result = evaluate_certainty_preregistration()
    payload = {"schema": "functional-affect-appraisal-artifact-1", "result": result}
    encoded = _canonical(payload)
    completed = {"status": "completed", "payload_sha256": hashlib.sha256(encoded).hexdigest()}
    path.mkdir(parents=True, exist_ok=False)
    (path / "result.json").write_bytes(encoded)
    (path / "completion.json").write_bytes(_canonical(completed))
    return path


def verify_certainty_artifact(path: Path) -> bool:
    """Verify the artifact hash and replay it against current fixed sources."""
    result_path, completion_path = path / "result.json", path / "completion.json"
    payload = result_path.read_bytes()
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    if completion != {"status": "completed", "payload_sha256": hashlib.sha256(payload).hexdigest()}:
        raise ValueError("certainty artifact completion mismatch")
    saved = json.loads(payload.decode("utf-8"))
    expected = {"schema": "functional-affect-appraisal-artifact-1", "result": evaluate_certainty_preregistration()}
    # JSON has one canonical boundary: tuples become arrays on disk.  Compare
    # the canonical JSON representation, not in-memory container types.
    if _canonical(saved) != _canonical(expected):
        raise ValueError("certainty artifact replay mismatch")
    return True
