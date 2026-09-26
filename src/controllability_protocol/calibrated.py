"""Isolated calibrated-recovery kernel; not a model of felt emotion."""
from __future__ import annotations

import hashlib
import math

from .core import Action


_TAPE_NAMESPACE = "sha256-calibrated-recovery-seed-trial-v1"


def decide_calibrated(*, apparent_high: bool, reliability_verified: bool,
                      safety_urgency: bool = False, boundary_risk: bool = False,
                      baseline: bool = False, permute_calibration: bool = False) -> tuple[Action, str]:
    """Keep safety dominant; only the calibrated policy uses verified reliability."""
    if safety_urgency or boundary_risk:
        return Action.SAFE, "safety_override"
    if baseline:
        return (Action.RECOVER, "apparent_control_baseline") if apparent_high else (Action.SAFE, "default_safe")
    calibrated_reliability = not reliability_verified if permute_calibration else reliability_verified
    if apparent_high and calibrated_reliability:
        return Action.RECOVER, "verified_recovery_opportunity"
    return Action.SAFE, "default_safe"


def _uniform(seed: int, trial: int) -> float:
    digest = hashlib.sha256(f"{_TAPE_NAMESPACE}:{seed}:{trial}".encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big") / 2 ** 64


def _outcome(action: Action, reliability_verified: bool, uniform: float) -> int:
    if action is Action.RECOVER:
        probability = 0.75 if reliability_verified else 0.10
    else:
        probability = 0.45
    return int(uniform < probability)


def evaluate_isolated_kernel(seeds: list[int], trials_per_seed: int) -> dict[str, object]:
    """Produce deterministic, card-free evidence for the kernel contract only."""
    if (not seeds or len(set(seeds)) != len(seeds) or any(type(seed) is not int for seed in seeds)
            or type(trials_per_seed) is not int or trials_per_seed < 2):
        raise ValueError("invalid isolated kernel inputs")
    rows: list[dict[str, object]] = []
    for seed in seeds:
        totals = {"calibrated": 0, "baseline": 0, "permuted": 0}
        for trial in range(trials_per_seed):
            verified = trial % 2 == 0
            uniform = _uniform(seed, trial)
            for label, kwargs in (
                ("calibrated", {}), ("baseline", {"baseline": True}), ("permuted", {"permute_calibration": True}),
            ):
                action, _ = decide_calibrated(apparent_high=True, reliability_verified=verified, **kwargs)
                totals[label] += _outcome(action, verified, uniform)
        rows.append({"seed": seed, **{name: total / trials_per_seed for name, total in totals.items()}})
    controls = [
        decide_calibrated(apparent_high=True, reliability_verified=True, safety_urgency=True)[0].value,
        decide_calibrated(apparent_high=True, reliability_verified=True, boundary_risk=True)[0].value,
    ]
    return {"schema": "controllability-calibrated-kernel-evidence-1", "tape_namespace": _TAPE_NAMESPACE,
            "rows": rows, "safety_controls": controls}


def summarize_calibrated_evidence(evidence: dict[str, object], acceptance: dict[str, object]) -> dict[str, object]:
    """Apply a preregistered paired-difference criterion without retuning it."""
    multiplier = acceptance.get("ci95_multiplier")
    if type(multiplier) is not float or multiplier <= 0.0:
        raise ValueError("invalid calibrated CI multiplier")
    rows, controls = evidence.get("rows"), evidence.get("safety_controls")
    if type(rows) is not list or len(rows) < 2 or controls != ["safe", "safe"]:
        raise ValueError("invalid calibrated evidence")
    differences = [float(row["calibrated"]) - float(row["baseline"]) for row in rows if type(row) is dict]
    permutation_differences = [float(row["calibrated"]) - float(row["permuted"]) for row in rows if type(row) is dict]
    if len(differences) != len(rows) or len(permutation_differences) != len(rows):
        raise ValueError("invalid calibrated evidence rows")
    mean = sum(differences) / len(differences)
    variance = sum((value - mean) ** 2 for value in differences) / (len(differences) - 1)
    ci95_lower = mean - multiplier * math.sqrt(variance / len(differences))
    controls_pass = all(value >= 0.0 for value in permutation_differences)
    return {
        "paired_mean_difference": mean,
        "ci95_lower": ci95_lower,
        "minimum_mean_difference": acceptance["minimum_mean_difference"],
        "minimum_ci95_lower": acceptance["minimum_ci95_lower"],
        "ci95_multiplier": multiplier,
        "controls_pass": controls_pass,
        "passes": mean >= acceptance["minimum_mean_difference"] and ci95_lower >= acceptance["minimum_ci95_lower"] and controls_pass,
    }
