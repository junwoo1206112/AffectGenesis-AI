"""Strict, pre-registered configuration boundary for temporal-learning-v2."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from temporal_learning.learner import ModelKind


EXPECTED_KEYS = frozenset({
    "protocol", "seeds", "train_episodes", "evaluation_episodes", "horizon",
    "checkpoints", "models", "context_tokens", "laplace", "scalar_decay",
    "scalar_rate", "try_penalty", "tie_tolerance", "effect_threshold",
    "positive_seed_minimum", "time_limit_seconds",
})


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def load_config(path: str | Path) -> tuple[dict, str]:
    def reject_constant(_: str) -> None:
        raise ValueError("non-finite config number")
    try:
        pairs = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=list, parse_constant=reject_constant)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("invalid config JSON") from error
    if type(pairs) is not list or any(type(item) is not tuple or len(item) != 2 for item in pairs):
        raise ValueError("config must be an object")
    keys = [key for key, _ in pairs]
    if any(type(key) is not str for key in keys) or len(keys) != len(set(keys)) or set(keys) != EXPECTED_KEYS:
        raise ValueError("unexpected config keys")
    config = dict(pairs)
    if (config["protocol"] != "temporal-learning-v2" or config["horizon"] != 30
            or config["context_tokens"] != 2 or config["laplace"] != 1
            or config["scalar_decay"] != .8 or config["scalar_rate"] != .2
            or config["try_penalty"] != .1 or config["tie_tolerance"] != 1e-12
            or tuple(config["models"]) != tuple(kind.value for kind in ModelKind)):
        raise ValueError("config changes a fixed v2 invariant")
    if (type(config["seeds"]) is not list or not config["seeds"]
            or any(type(seed) is not int or seed < 0 for seed in config["seeds"])
            or len(config["seeds"]) != len(set(config["seeds"]))
            or type(config["checkpoints"]) is not list
            or any(type(value) is not int or value < 0 for value in config["checkpoints"])
            or config["checkpoints"] != sorted(set(config["checkpoints"]))
            or type(config["train_episodes"]) is not int or config["train_episodes"] not in config["checkpoints"]
            or 0 not in config["checkpoints"]):
        raise ValueError("invalid seeds or checkpoints")
    for key in ("evaluation_episodes", "positive_seed_minimum", "time_limit_seconds"):
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError("invalid integer config value")
    if config["positive_seed_minimum"] > len(config["seeds"]):
        raise ValueError("positive seed minimum exceeds seed count")
    if (type(config["effect_threshold"]) not in (int, float) or isinstance(config["effect_threshold"], bool)
            or not math.isfinite(config["effect_threshold"]) or config["effect_threshold"] <= 0):
        raise ValueError("invalid effect threshold")
    encoded = canonical_json(config).encode("utf-8")
    return config, hashlib.sha256(encoded).hexdigest()
