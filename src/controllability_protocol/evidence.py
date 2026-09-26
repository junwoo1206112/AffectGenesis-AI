"""Frozen-card evidence writer and independent recomputation for controllability."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .core import Card, mechanism_row


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_cards(path: Path) -> list[Card]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if type(raw) is not list or len(raw) < 6: raise ValueError("invalid card registry")
    cards = [Card(**row) for row in raw]
    if len({card.card_id for card in cards}) != len(cards) or {card.family for card in cards} != {"train", "holdout", "safety"}:
        raise ValueError("invalid card registry identity")
    return cards


def evaluate(cards: list[Card]) -> dict[str, object]:
    holdout = [card for card in cards if card.family == "holdout"]
    normal = [mechanism_row(card) for card in holdout]
    permuted = [mechanism_row(card, permute_label=True) for card in holdout]
    ablated = [mechanism_row(card, ablated=True) for card in holdout]
    safety = [mechanism_row(card) for card in cards if card.family == "safety"]
    high = [row for row in normal if row["controllability"] == "high" and row["recoverable"]]
    low = [row for row in normal if row["controllability"] == "low" and row["recoverable"]]
    if not high or not low: raise ValueError("missing paired holdout cards")
    recover_rate = lambda rows: sum(row["action"] == "recover" for row in rows) / len(rows)
    return {"schema":"controllability-evidence-1", "normal":normal, "permuted":permuted, "ablated":ablated, "safety":safety,
            "criterion":{"high_minus_low_recover_rate":recover_rate(high)-recover_rate(low), "threshold":1.0,
                         "passes":recover_rate(high)-recover_rate(low) >= 1.0,
                         "controls_pass": all(row["action"] == "safe" for row in permuted + ablated + safety) and all(row["action"] == "safe" for row in normal if not row["recoverable"])}}


def run(cards_path: Path, root: Path) -> int:
    cards = load_cards(cards_path); root.mkdir(parents=True, exist_ok=False); evidence = evaluate(cards)
    registry = cards_path.read_bytes(); (root / "cards.json").write_bytes(registry); (root / "evidence.json").write_bytes(_canonical(evidence))
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in ("cards.json", "evidence.json")}
    (root / "completion.json").write_bytes(_canonical({"status":"completed","hashes":hashes}))
    return 0


def verify(root: Path) -> int:
    completion = json.loads((root / "completion.json").read_text(encoding="utf-8"))
    if completion.get("status") != "completed" or set(completion.get("hashes", {})) != {"cards.json", "evidence.json"}: raise ValueError("invalid completion")
    for name, digest in completion["hashes"].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest: raise ValueError("hash mismatch")
    temporary = root / "cards.json"; expected = evaluate(load_cards(temporary))
    if json.loads((root / "evidence.json").read_text(encoding="utf-8")) != expected: raise ValueError("evidence mismatch")
    return 0
