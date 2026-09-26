"""Side-effect-free scale estimate for a pre-registered v2 configuration."""
from __future__ import annotations

from collections.abc import Mapping


def preflight(config: Mapping[str, object]) -> dict[str, object]:
    """Report deterministic row work; this is not a runtime or effect prediction."""
    seeds = len(config["seeds"])
    checkpoints = len(config["checkpoints"])
    models = len(config["models"])
    horizon = int(config["horizon"])
    training_rows = seeds * int(config["train_episodes"]) * horizon
    evaluation_rows = seeds * checkpoints * 3 * models * int(config["evaluation_episodes"]) * horizon
    affect_evaluation_rows = seeds * checkpoints * 3 * int(config["evaluation_episodes"]) * horizon
    public_rows = training_rows + evaluation_rows
    brier_rows = evaluation_rows
    counterfactual_rows = affect_evaluation_rows * 3
    diagnostic_rows = brier_rows + counterfactual_rows
    total_rows = public_rows + evaluation_rows + diagnostic_rows
    return {"schema": "temporal-learning-v2-preflight-2", "training_rows": training_rows,
            "evaluation_rows": evaluation_rows, "public_episode_rows": public_rows,
            "persistence_replay_rows": evaluation_rows, "diagnostic_brier_rows": brier_rows,
            "diagnostic_counterfactual_rows": counterfactual_rows, "diagnostic_rows": diagnostic_rows,
            "total_episode_rows": total_rows, "public_jsonl_byte_upper_bound": public_rows * 2_048,
            "streaming_required": True,
            "time_limit_seconds": config["time_limit_seconds"]}
