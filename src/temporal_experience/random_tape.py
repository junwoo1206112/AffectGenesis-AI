"""Pure, order-independent SHA-256 based random tape."""
from __future__ import annotations

import hashlib
import json

from .contracts import ExperimentAction


PROTOCOL = "temporal-environment-v1"


def _validate(condition: str, seed: int, episode: int, step: int, component: str, action: ExperimentAction | None) -> None:
    if (type(condition) is not str or type(seed) is not int or type(episode) is not int
            or type(step) is not int or type(component) is not str
            or (action is not None and type(action) is not ExperimentAction)):
        raise ValueError("invalid tape key")
    if component == "initial":
        if step != -1 or action is not None:
            raise ValueError("invalid initial tape key")
    elif component in ("outcome", "transition"):
        if not 0 <= step < 30 or action is None:
            raise ValueError("invalid event tape key")
    else:
        raise ValueError("invalid tape component")


def key_bytes(condition: str, seed: int, episode: int, step: int, component: str, action: ExperimentAction | None) -> bytes:
    _validate(condition, seed, episode, step, component, action)
    return json.dumps([PROTOCOL, condition, seed, episode, step, component,
                       None if action is None else action.value], ensure_ascii=True,
                      separators=(",", ":")).encode("utf-8")


def tape(condition: str, seed: int, episode: int, step: int, component: str, action: ExperimentAction | None) -> tuple[str, float]:
    digest = hashlib.sha256(key_bytes(condition, seed, episode, step, component, action)).digest()
    value = int.from_bytes(digest[:8], "big") >> 11
    return digest.hex(), value / 2**53


def event(probability: float, *key: object) -> tuple[str, float, bool]:
    if type(probability) not in (int, float) or isinstance(probability, bool) or not 0 <= float(probability) <= 1:
        raise ValueError("invalid event probability")
    digest, uniform = tape(*key)
    return digest, uniform, uniform < float(probability)
