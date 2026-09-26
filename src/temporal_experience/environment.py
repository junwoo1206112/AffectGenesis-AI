"""Hidden-state synthetic environment; public and audit data are separate objects."""
from __future__ import annotations

from dataclasses import asdict

from .contracts import (
    HORIZON, INITIAL_GOOD_PROBABILITY, PARAMETERS, EpisodeKey, ExperimentAction, Feedback, HiddenState,
    ObservedObservation, PublicObservation,
)
from .random_tape import event, tape


class TemporalEnvironment:
    def __init__(self, condition: str = "main") -> None:
        if condition not in PARAMETERS:
            raise ValueError("unknown environment condition")
        self.condition = condition
        self._key: EpisodeKey | None = None
        self._state: HiddenState | None = None
        self._step = 0
        self._done = False

    def reset(self, key: EpisodeKey) -> PublicObservation:
        if key.condition != self.condition:
            raise ValueError("environment condition/key mismatch")
        _, _, good = event(INITIAL_GOOD_PROBABILITY[self.condition], self.condition, key.seed, key.episode, -1, "initial", None)
        self._key, self._state, self._step, self._done = key, (HiddenState.GOOD if good else HiddenState.BLOCKED), 0, False
        return self._observation()

    def _observation(self) -> PublicObservation:
        if self._state is None or self._done:
            raise RuntimeError("no next observation")
        common = dict(remaining=HORIZON - self._step)
        if self.condition == "observed":
            return ObservedObservation(visible_state=self._state, **common)
        return PublicObservation(**common)

    def step(self, action: ExperimentAction) -> tuple[Feedback, PublicObservation | None]:
        if type(action) is not ExperimentAction:
            raise ValueError("invalid experiment action")
        if self._key is None or self._state is None or self._done:
            raise RuntimeError("environment is not ready")
        good_success, blocked_success, good_natural, blocked_natural, good_recover, blocked_recover = PARAMETERS[self.condition]
        if self.condition == "iid":
            good_natural = blocked_natural = good_recover = blocked_recover = 0.5
        if action is ExperimentAction.TRY:
            probability = good_success if self._state is HiddenState.GOOD else blocked_success
            _, _, success = event(probability, self.condition, self._key.seed, self._key.episode, self._step, "outcome", action)
            feedback = Feedback(action, "success" if success else "failure", 1.0 if success else -1.0, self._step == HORIZON - 1)
        elif action is ExperimentAction.SAFE:
            tape(self.condition, self._key.seed, self._key.episode, self._step, "outcome", action)
            feedback = Feedback(action, "done", 0.1, self._step == HORIZON - 1)
        else:
            tape(self.condition, self._key.seed, self._key.episode, self._step, "outcome", action)
            feedback = Feedback(action, "done", -0.2, self._step == HORIZON - 1)
        transition = (good_recover if self._state is HiddenState.GOOD else blocked_recover) if action is ExperimentAction.RECOVER else (good_natural if self._state is HiddenState.GOOD else blocked_natural)
        _, _, next_good = event(transition, self.condition, self._key.seed, self._key.episode, self._step, "transition", action)
        self._state = HiddenState.GOOD if next_good else HiddenState.BLOCKED
        self._step += 1
        self._done = feedback.terminal
        return feedback, None if self._done else self._observation()

    def audit_snapshot(self) -> dict[str, object]:
        if self._key is None or self._state is None:
            raise RuntimeError("environment is not ready")
        return {"condition": self.condition, "seed": self._key.seed, "episode": self._key.episode,
                "step": self._step, "state": self._state.value, "done": self._done}
