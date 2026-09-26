"""Pure score derivation for the pre-registered follow-up comparisons."""
from __future__ import annotations

import math
from statistics import mean
from typing import Mapping, Sequence


COMPARATORS = ("counts", "failure_trace", "affect_neutral")


def _scores(values: object, count: int) -> list[float]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)) or len(values) != count:
        raise ValueError("seed count mismatch")
    if any(type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(float(value)) for value in values):
        raise ValueError("invalid score")
    return [float(value) for value in values]


def _verdict(deltas: Sequence[float], threshold: float, minimum: int) -> dict[str, object]:
    qualifying = sum(delta >= threshold for delta in deltas)
    return {"status": "pass" if mean(deltas) >= threshold and qualifying >= minimum else "fail",
            "mean_delta": mean(deltas), "qualifying_seeds": qualifying, "seed_count": len(deltas),
            "threshold": threshold, "minimum": minimum}


def derive_checks(config: Mapping[str, object], scores: Mapping[str, Mapping[str, Mapping[str, Sequence[float]]]]) -> dict[str, object]:
    """Require all three final held-out comparisons; no finding implies real emotion."""
    final, condition, count = str(config["train_episodes"]), str(config["held_out_condition"]), len(config["seeds"])
    result: dict[str, object] = {"schema": f"{config['protocol']}-checks", "comparisons": {}}
    try:
        affect = _scores(scores[final][condition]["affect"], count)
        for comparator in COMPARATORS:
            baseline = _scores(scores[final][condition][comparator], count)
            result["comparisons"][f"affect_minus_{comparator}"] = _verdict(
                [value - control for value, control in zip(affect, baseline)], float(config["effect_threshold"]), int(config["positive_seed_minimum"]))
    except (KeyError, TypeError, ValueError):
        for comparator in COMPARATORS:
            result["comparisons"][f"affect_minus_{comparator}"] = {"status": "not_assessed", "reason": "missing or misaligned scores"}
    result["all_required_pass"] = all(item["status"] == "pass" for item in result["comparisons"].values())
    return result
