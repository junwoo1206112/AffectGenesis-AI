"""Pure, pre-registered v2 result derivation; it performs no learning or I/O."""
from __future__ import annotations

import math
from statistics import mean
from typing import Mapping, Sequence


HELD_OUT = ("test_A", "test_B")
BASELINES = ("counts", "failure_trace")


def paired_deltas(config: Mapping[str, object], scores: Mapping[str, Mapping[str, Mapping[str, Sequence[float]]]]) -> dict[str, dict[str, list[float]]]:
    """Canonical seed-ordered deltas retained alongside aggregate checks."""
    initial, final = "0", str(config["train_episodes"])
    result: dict[str, dict[str, list[float]]] = {"L": {}, "S": {}}
    for condition in HELD_OUT:
        affect0, affect = scores[initial][condition]["affect"], scores[final][condition]["affect"]
        result["L"][condition] = [after - before for before, after in zip(affect0, affect)]
        for baseline in BASELINES:
            result["S"][f"{condition}:affect_minus_{baseline}"] = [after - control for after, control in zip(affect, scores[final][condition][baseline])]
    return result


def _verdict(deltas: Sequence[float], threshold: float, minimum: int) -> dict[str, object]:
    if not deltas:
        return {"status": "not_assessed", "reason": "no seed deltas"}
    positive = sum(delta >= threshold for delta in deltas)
    passed = mean(deltas) >= threshold and positive >= minimum
    return {"status": "pass" if passed else "fail", "mean_delta": mean(deltas),
            "qualifying_seeds": positive, "seed_count": len(deltas),
            "threshold": threshold, "minimum": minimum}


def _aligned_scores(values: object, seed_count: int) -> list[float]:
    """Accept only finite, seed-aligned numeric values (never booleans)."""
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)) or len(values) != seed_count:
        raise ValueError("seed count mismatch")
    result: list[float] = []
    for value in values:
        if type(value) not in (int, float) or not math.isfinite(float(value)):
            raise ValueError("invalid score")
        result.append(float(value))
    return result


def derive_checks(config: Mapping[str, object], scores: Mapping[str, Mapping[str, Mapping[str, Sequence[float]]]],
                  *, persistence: bool | None, safety: bool | None,
                  learning: Mapping[str, object] | None = None) -> dict[str, object]:
    """Derive v2 checks from seed-aligned normalized score sequences.

    ``scores[checkpoint][condition][model]`` must contain one finite score per
    configured seed in exactly the configured order.  This strict shape prevents
    an aggregate-only report from hiding paired failures.
    """
    final, initial = str(config["train_episodes"]), "0"
    seed_count = len(config["seeds"])
    threshold, minimum = float(config["effect_threshold"]), int(config["positive_seed_minimum"])
    unavailable = {"status": "not_assessed", "reason": "not emitted by this protocol version"}
    result: dict[str, object] = {"schema": "temporal-learning-v2-checks", "L": {}, "S": {},
                                 "persistence": {"status": "not_assessed"}, "safety": {"status": "not_assessed"},
                                 "brier": unavailable.copy(), "context_try_samples": unavailable.copy(),
                                 "neutral_diagnostic": unavailable.copy(), "permuted_diagnostic": unavailable.copy()}
    for condition in HELD_OUT:
        try:
            before = _aligned_scores(scores[initial][condition]["affect"], seed_count)
            affect = _aligned_scores(scores[final][condition]["affect"], seed_count)
            result["L"][condition] = _verdict([after - prior for prior, after in zip(before, affect)], threshold, minimum)
            for baseline in BASELINES:
                reference = _aligned_scores(scores[final][condition][baseline], seed_count)
                result["S"][f"{condition}:affect_minus_{baseline}"] = _verdict(
                    [after - control for after, control in zip(affect, reference)], threshold, minimum)
        except (KeyError, TypeError, ValueError):
            result["L"][condition] = {"status": "not_assessed", "reason": "missing or misaligned scores"}
            for baseline in BASELINES:
                result["S"][f"{condition}:affect_minus_{baseline}"] = {"status": "not_assessed", "reason": "missing or misaligned scores"}
    result["persistence"] = {"status": "pass" if persistence else "fail" if persistence is False else "not_assessed"}
    result["safety"] = {"status": "pass" if safety else "fail" if safety is False else "not_assessed"}
    if learning is not None:
        try:
            if learning.get("schema") != "temporal-learning-v2-learning-diagnostics-1":
                raise ValueError("invalid learning diagnostics")
            result["brier"] = {"status": "pass" if learning["brier"]["passes"] else "fail",
                               "reason": "common frozen-checkpoint behavior trace"}
            result["context_try_samples"] = {"status": "pass" if learning["context_try_samples"]["passes"] else "fail",
                                              "reason": "affect policy context TRY counts emitted"}
            result["neutral_diagnostic"] = {"status": "pass" if learning["neutral_scalar"]["passes"] else "fail",
                                            "reason": "same-tape scalar-neutral counterfactual emitted"}
            result["permuted_diagnostic"] = {"status": "pass" if learning["permuted_context"]["passes"] else "fail",
                                             "reason": "same-tape context-permutation counterfactual emitted"}
        except (AttributeError, KeyError, TypeError, ValueError):
            for name in ("brier", "context_try_samples", "neutral_diagnostic", "permuted_diagnostic"):
                result[name] = {"status": "not_assessed", "reason": "invalid learning diagnostics"}
    return result


def render_report(checks: Mapping[str, object]) -> str:
    """Canonical human-readable view; all findings originate in checks."""
    lines = ["# temporal-learning-v2 report", "", "Synthetic functional-learning evidence only; no claim of real emotion or consciousness.", ""]
    for heading in ("L", "S", "persistence", "safety", "brier", "context_try_samples", "neutral_diagnostic", "permuted_diagnostic"):
        lines.append(f"## {heading}")
        value = checks[heading]
        if isinstance(value, Mapping):
            for name, finding in value.items():
                if isinstance(finding, Mapping):
                    lines.append(f"- {name}: {finding['status']}")
                else:
                    lines.append(f"- {name}: {finding}")
        lines.append("")
    return "\n".join(lines)
