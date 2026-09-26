"""Read-only, fixed-protocol diagnostic; does not tune or retrain the learner."""
from __future__ import annotations

import json
from pathlib import Path
import statistics

from affect_growth.environment import make_dataset
from affect_growth.evaluation import canonical, state_probe, verify_report
from affect_growth.learner import Learner
from affect_growth.models import ACTIONS
from functional_affect.models import Action


def inspect(model, cases, seed):
    before = canonical(model.to_dict("diagnostic"))
    states, margins = [], []
    counts = dict(n=0, uncertain=0, non_decompose=0, decompose=0,
                  observed_switches=0, forced_one_switches=0)
    for start in range(0, len(cases), 10):
        worker = model.clone()
        worker.reset_state()
        for case in cases[start:start + 10]:
            obs = case.observation
            states.append(worker.frustration)
            normal = worker.predict(obs).action
            neutral, extreme = worker.clone(), worker.clone()
            neutral.frustration, extreme.frustration = 0.0, 1.0
            baseline = neutral.predict(obs).action
            posterior, utility = worker._estimates(obs)
            counts["n"] += 1
            if max(posterior) < 0.6:
                counts["uncertain"] += 1
            elif baseline is not Action.DECOMPOSE:
                counts["non_decompose"] += 1
            else:
                counts["decompose"] += 1
                margins.append(utility[ACTIONS.index(Action.DECOMPOSE)] - max(
                    value for action, value in zip(ACTIONS, utility)
                    if action is not Action.DECOMPOSE))
            counts["observed_switches"] += int(normal != baseline)
            counts["forced_one_switches"] += int(extreme.predict(obs).action != baseline)
            worker.learn(obs, case.feedback, update=False)
    probe = state_probe(model, cases, seed)
    assert states == [f for trace in probe["frustration_traces"] for f in trace]
    assert counts["observed_switches"] / counts["n"] == probe["action_change_rate"]["neutral"]
    assert before == canonical(model.to_dict("diagnostic")), "Source model mutated"
    return {**counts, "states": states, "decompose_margins": margins}


def aggregate(rows):
    keys = ("n", "uncertain", "non_decompose", "decompose",
            "observed_switches", "forced_one_switches")
    states = [f for row in rows for f in row["states"]]
    margins = [m for row in rows for m in row["decompose_margins"]]
    return {**{key: sum(row[key] for row in rows) for key in keys},
            "state_min": min(states), "state_max": max(states),
            "state_mean": statistics.mean(states),
            "state_positive": sum(f > 0 for f in states),
            "decompose_margin_min": min(margins) if margins else None,
            "decompose_margin_max": max(margins) if margins else None,
            "per_seed": [{key: row[key] for key in keys} for row in rows]}


def main():
    root = Path(__file__).resolve().parents[1]
    run = root / "artifacts/affect_growth/pilot-20260920-02"
    verify_report(run / "report.md", root=root)
    checkpoints = json.loads((run / "checkpoints.json").read_text(encoding="utf-8"))
    selected = sorted((row for row in checkpoints if row["mode"] == "learned"
                       and row["order"] == "chronological" and row["step"] == 300),
                      key=lambda row: row["seed"])
    assert [row["seed"] for row in selected] == list(range(10))
    result = {}
    for label, offset in (("original_dev", 0), ("additional_same_generator", 1000)):
        rows = []
        for checkpoint in selected:
            state = checkpoint["state"]
            model = Learner.from_dict(state, state["config_hash"])
            seed = checkpoint["seed"] + offset
            rows.append(inspect(model, make_dataset(seed, "dev"), seed))
        result[label] = aggregate(rows)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
