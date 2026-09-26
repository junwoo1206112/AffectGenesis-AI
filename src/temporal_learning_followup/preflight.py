"""Side-effect-free scale estimate for the failure-rich follow-up."""
from __future__ import annotations

from collections.abc import Mapping


def preflight(config: Mapping[str, object]) -> dict[str, object]:
    """Report actual writer work, not runtime, disk, or effect predictions."""
    seeds, horizon = len(config["seeds"]), int(config["horizon"])
    training_rows = seeds * int(config["train_episodes"]) * horizon
    final_evaluation_rows = seeds * len(config["models"]) * int(config["evaluation_episodes"]) * horizon
    public_rows = training_rows + final_evaluation_rows
    return {"schema": f"{config['protocol']}-preflight-1", "training_rows": training_rows,
            "final_evaluation_rows": final_evaluation_rows, "public_episode_rows": public_rows,
            "checkpoint_snapshots_per_seed": len(config["checkpoints"]),
            "public_jsonl_byte_upper_bound": public_rows * 2_048, "streaming_required": True,
            "time_limit_seconds": config["time_limit_seconds"]}
