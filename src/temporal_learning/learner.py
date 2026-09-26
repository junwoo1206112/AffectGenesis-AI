from __future__ import annotations

from copy import deepcopy
from enum import StrEnum
import hashlib
import json
import math

from temporal_experience.contracts import Decision, ExperimentAction, Feedback, PublicObservation


class Token(StrEnum):
    BOS = "bos"; TS = "ts"; TF = "tf"; SD = "sd"; RD = "rd"


class ModelKind(StrEnum):
    COUNTS = "counts"; AFFECT = "affect"; FAILURE_TRACE = "failure_trace"


OUTCOMES = {ExperimentAction.TRY: (Token.TS, Token.TF), ExperimentAction.SAFE: (Token.SD,), ExperimentAction.RECOVER: (Token.RD,)}
REWARDS = {Token.TS: 1.0, Token.TF: -1.0, Token.SD: 0.1, Token.RD: -0.2}
# BOS remains possible in the first coordinate after the first public feedback.
CONTEXTS = tuple((a, b) for a in Token for b in Token)


class TemporalLearner:
    def __init__(self, kind: ModelKind | str = ModelKind.COUNTS) -> None:
        self.kind = ModelKind(kind)
        self.counts = {(c, a, o): 0 for c in CONTEXTS for a in ExperimentAction for o in OUTCOMES[a]}
        self.context = (Token.BOS, Token.BOS)
        self.scalar = 0.0
        self._prediction_cache: dict[tuple[tuple[Token, Token], int], dict[ExperimentAction, float]] = {}

    def reset_episode(self) -> None:
        self.context, self.scalar = (Token.BOS, Token.BOS), 0.0

    def reset_scalar(self) -> None: self.scalar = 0.0

    def probability(self, action: ExperimentAction, outcome: Token, context=None) -> float:
        c = self.context if context is None else context
        if outcome not in OUTCOMES[action]: raise ValueError("invalid outcome")
        return (self.counts[(c, action, outcome)] + 1) / (sum(self.counts[(c, action, o)] for o in OUTCOMES[action]) + len(OUTCOMES[action]))

    def _q(self, context, h: int, memo: dict) -> dict:
        if h == 0: return {a: 0.0 for a in ExperimentAction}
        result = {}
        for a in ExperimentAction:
            value = 0.0
            for o in OUTCOMES[a]:
                nxt = (context[1], o)
                key = (nxt, h - 1)
                if key not in memo: memo[key] = max(self._q(nxt, h - 1, memo).values())
                value += self.probability(a, o, context) * (REWARDS[o] + memo[key])
            result[a] = value
        return result

    def predict(self, observation: PublicObservation) -> Decision:
        cache_key = (self.context, observation.remaining)
        if cache_key not in self._prediction_cache:
            self._prediction_cache[cache_key] = self._q(self.context, observation.remaining, {})
        q = self._prediction_cache[cache_key].copy()
        if self.kind is not ModelKind.COUNTS: q[ExperimentAction.TRY] -= 0.1 * self.scalar
        best = max(ExperimentAction, key=lambda a: (q[a], - (0 if a is ExperimentAction.SAFE else 1 if a is ExperimentAction.TRY else 2)))
        return Decision(best, self.probability(ExperimentAction.TRY, Token.TS))

    def observe(self, action: ExperimentAction, feedback: Feedback, learn_counts: bool = True) -> tuple[float, float, tuple[Token, Token]]:
        if type(action) is not ExperimentAction or feedback.action is not action: raise ValueError("action/feedback mismatch")
        prior, before = self.probability(ExperimentAction.TRY, Token.TS), self.scalar
        token = Token.TS if feedback.outcome == "success" else Token.TF if feedback.outcome == "failure" else Token.SD if action is ExperimentAction.SAFE else Token.RD
        if self.kind is ModelKind.AFFECT:
            self.scalar = max(0.0, min(1.0, .8 * self.scalar + (.2 * (prior - int(token is Token.TS)) if action is ExperimentAction.TRY else 0.0)))
        elif self.kind is ModelKind.FAILURE_TRACE:
            self.scalar = max(0.0, min(1.0, .8 * self.scalar + (.2 * int(token is Token.TF) if action is ExperimentAction.TRY else 0.0)))
        if learn_counts:
            self.counts[(self.context, action, token)] += 1
            self._prediction_cache.clear()
        self.context = (self.context[1], token)
        return prior, before, self.context

    def checkpoint(self, config_hash: str) -> dict:
        if type(config_hash) is not str or not config_hash: raise ValueError("config hash")
        return {"schema": 1, "config_hash": config_hash, "kind": self.kind.value,
                "counts": {f"{c[0].value}/{c[1].value}/{a.value}/{o.value}": n for (c, a, o), n in self.counts.items()}}

    @classmethod
    def from_checkpoint(cls, data: dict, config_hash: str):
        if type(data) is not dict or set(data) != {"schema", "config_hash", "kind", "counts"} or data.get("schema") != 1 or data.get("config_hash") != config_hash:
            raise ValueError("checkpoint schema")
        result = cls(data["kind"])
        expected = result.checkpoint(config_hash)["counts"]
        if set(data["counts"]) != set(expected) or any(type(n) is not int or n < 0 for n in data["counts"].values()): raise ValueError("checkpoint counts")
        for key, value in data["counts"].items():
            c0,c1,a,o=key.split("/"); result.counts[((Token(c0),Token(c1)),ExperimentAction(a),Token(o))]=value
        return result
