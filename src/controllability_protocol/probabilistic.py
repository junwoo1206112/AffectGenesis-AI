"""Strict synthetic paired re-evaluation; not evidence of felt emotion."""
from __future__ import annotations

import hashlib
import json
import math
import tempfile
from pathlib import Path

from .core import Action, Card, decide
from .evidence import load_cards


_BASELINE_SCHEMA = "controllability-probabilistic-protocol-1"
_INDEPENDENT_SCHEMA = "controllability-independent-reproduction-protocol-1"
_BASELINE_TAPE = "sha256-seed-trial-v1"
_INDEPENDENT_TAPE = "sha256-recovery-friction-seed-trial-v1"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_protocol(path: Path) -> dict[str, object]:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    schema = protocol.get("schema") if type(protocol) is dict else None
    if schema not in (_BASELINE_SCHEMA, _INDEPENDENT_SCHEMA) or protocol.get("evaluation_family") != "holdout":
        raise ValueError("invalid probabilistic protocol")
    seeds, trials, tape = protocol.get("seeds"), protocol.get("trials_per_seed"), protocol.get("tape_scheme")
    outcomes, acceptance = protocol.get("outcomes"), protocol.get("acceptance")
    if (type(seeds) is not list or len(seeds) < 20 or len(set(seeds)) != len(seeds)
            or any(type(seed) is not int for seed in seeds) or type(trials) is not int or trials < 2
            or tape != (_BASELINE_TAPE if schema == _BASELINE_SCHEMA else _INDEPENDENT_TAPE)
            or type(outcomes) is not dict or type(acceptance) is not dict):
        raise ValueError("invalid probabilistic protocol")
    if schema == _INDEPENDENT_SCHEMA and protocol.get("kernel_id") != "recovery-friction-v1":
        raise ValueError("invalid independent kernel")
    for name in ("recover_success_probability", "safe_success_probability"):
        if type(outcomes.get(name)) is not float or not 0.0 < outcomes[name] < 1.0:
            raise ValueError("invalid outcome probability")
    for name in ("minimum_mean_difference", "minimum_ci95_low", "ci95_multiplier"):
        if type(acceptance.get(name)) is not float or acceptance[name] <= 0.0:
            raise ValueError("invalid acceptance criterion")
    return protocol


def _uniform(seed: int, trial: int, tape_scheme: str) -> float:
    material = f"{seed}:{trial}" if tape_scheme == _BASELINE_TAPE else f"{tape_scheme}:{seed}:{trial}"
    digest = hashlib.sha256(material.encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big") / 2 ** 64


def _outcome(action: Action, uniform: float, outcomes: dict[str, object]) -> int:
    probability = outcomes["recover_success_probability"] if action is Action.RECOVER else outcomes["safe_success_probability"]
    return int(uniform < probability)


def _summary(values: list[float], multiplier: float) -> dict[str, float]:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    margin = multiplier * math.sqrt(variance / len(values))
    return {"mean": mean, "ci95_low": mean - margin, "ci95_high": mean + margin}


def evaluate(protocol: dict[str, object], cards: list[Card]) -> dict[str, object]:
    holdout = [card for card in cards if card.family == protocol["evaluation_family"]]
    high = [card for card in holdout if card.controllability == "high" and card.recoverable]
    low = [card for card in holdout if card.controllability == "low" and card.recoverable]
    if len(high) != 1 or len(low) != 1:
        raise ValueError("expected exactly one paired high/low holdout card")
    safety = [card for card in cards if card.family == "safety"]
    if not safety:
        raise ValueError("missing safety cards")
    outcomes = protocol["outcomes"]
    assert type(outcomes) is dict
    acceptance = protocol["acceptance"]
    assert type(acceptance) is dict
    trials = protocol["trials_per_seed"]
    assert type(trials) is int
    seeds = protocol["seeds"]
    assert type(seeds) is list
    tape_scheme = protocol["tape_scheme"]
    assert type(tape_scheme) is str
    seed_rows: list[dict[str, object]] = []
    paired_differences: list[float] = []
    for seed in seeds:
        assert type(seed) is int
        high_values, low_values = [], []
        for trial in range(trials):
            tape = _uniform(seed, trial, tape_scheme)
            high_values.append(_outcome(decide(high[0])[0], tape, outcomes))
            low_values.append(_outcome(decide(low[0])[0], tape, outcomes))
        high_mean, low_mean = sum(high_values) / trials, sum(low_values) / trials
        paired_differences.append(high_mean - low_mean)
        seed_rows.append({"seed": seed, "high_mean": high_mean, "low_mean": low_mean, "difference": high_mean - low_mean})
    statistics = _summary(paired_differences, acceptance["ci95_multiplier"])
    controls = {
        "permuted_high_actions": [decide(high[0], permute_label=True)[0].value],
        "ablated_high_actions": [decide(high[0], ablated=True)[0].value],
        "safety_actions": [decide(card)[0].value for card in safety],
    }
    controls_pass = all(action == Action.SAFE.value for actions in controls.values() for action in actions)
    criterion = {
        **statistics,
        "minimum_mean_difference": acceptance["minimum_mean_difference"],
        "minimum_ci95_low": acceptance["minimum_ci95_low"],
        "passes": statistics["mean"] >= acceptance["minimum_mean_difference"] and statistics["ci95_low"] >= acceptance["minimum_ci95_low"] and controls_pass,
        "controls_pass": controls_pass,
    }
    evidence = {"schema": "controllability-probabilistic-evidence-1", "tape_scheme": tape_scheme, "seed_rows": seed_rows,
                "controls": controls, "criterion": criterion}
    if protocol["schema"] == _INDEPENDENT_SCHEMA:
        evidence["schema"] = "controllability-independent-reproduction-evidence-1"
        evidence["kernel_id"] = protocol["kernel_id"]
    return evidence


def run(protocol_path: Path, cards_path: Path, root: Path) -> int:
    protocol, cards = load_protocol(protocol_path), load_cards(cards_path)
    root.mkdir(parents=True, exist_ok=False)
    (root / "protocol.json").write_bytes(protocol_path.read_bytes())
    (root / "cards.json").write_bytes(cards_path.read_bytes())
    (root / "evidence.json").write_bytes(_canonical(evaluate(protocol, cards)))
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in ("protocol.json", "cards.json", "evidence.json")}
    (root / "completion.json").write_bytes(_canonical({"status": "completed", "hashes": hashes}))
    return 0


def verify(root: Path) -> int:
    completion = json.loads((root / "completion.json").read_text(encoding="utf-8"))
    expected_names = {"protocol.json", "cards.json", "evidence.json"}
    if completion.get("status") != "completed" or set(completion.get("hashes", {})) != expected_names:
        raise ValueError("invalid completion")
    for name, digest in completion["hashes"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError("hash mismatch")
    expected = evaluate(load_protocol(root / "protocol.json"), load_cards(root / "cards.json"))
    if json.loads((root / "evidence.json").read_text(encoding="utf-8")) != expected:
        raise ValueError("evidence mismatch")
    return 0


def replay(root: Path) -> int:
    verify(root)
    with tempfile.TemporaryDirectory(dir=root.parent) as directory:
        replay_root = Path(directory) / "replay"
        run(root / "protocol.json", root / "cards.json", replay_root)
        if (root / "evidence.json").read_bytes() != (replay_root / "evidence.json").read_bytes():
            raise ValueError("replay mismatch")
    return 0
