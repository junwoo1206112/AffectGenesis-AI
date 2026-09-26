from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from itertools import product
import unittest

from affect_growth.learner import Learner
from affect_growth.models import Feedback, Observation
from affect_growth.safety import safety_action
from functional_affect.models import Action


class GrowthSafetyTests(unittest.TestCase):
    def assert_guarded_without_mutation(self, observation, expected):
        self.assertEqual(expected, safety_action(observation))
        for mode in ("learned", "frozen", "memory"):
            with self.subTest(mode=mode):
                learner = Learner(mode=mode)
                valid = Observation(cues=(0, 0, 0, 0))
                feedback = Feedback(label=0, action=Action.DECOMPOSE, outcome=0)
                learner.learn(valid, feedback)
                before = deepcopy(learner.to_dict("test"))
                self.assertEqual(expected, learner.predict(observation).action)
                self.assertEqual(before, learner.to_dict("test"))
                learner.learn(observation, feedback)
                self.assertEqual(before, learner.to_dict("test"))

    def test_all_gate_flag_combinations_and_priority(self):
        for parser_valid, has_evidence, urgency, boundary in product(
            (False, True), repeat=4
        ):
            with self.subTest(
                parser_valid=parser_valid,
                has_evidence=has_evidence,
                urgency=urgency,
                boundary=boundary,
            ):
                observation = Observation(
                    cues=(0, 0, 0, 0),
                    evidence_refs=("synthetic",) if has_evidence else (),
                    parser_valid=parser_valid,
                    safety_urgency=urgency,
                    boundary_risk=boundary,
                )
                if not parser_valid or not has_evidence or urgency:
                    expected = Action.SAFE_HANDOFF
                elif boundary:
                    expected = Action.BOUNDARY_NOTICE
                else:
                    expected = None
                if expected is None:
                    self.assertIsNone(safety_action(observation))
                    for mode in ("learned", "frozen", "memory"):
                        with self.subTest(mode=mode):
                            self.assertNotIn(
                                Learner(mode=mode).predict(observation).action,
                                (Action.SAFE_HANDOFF, Action.BOUNDARY_NOTICE),
                            )
                else:
                    self.assert_guarded_without_mutation(observation, expected)

    def test_malformed_observations_fail_closed_without_state_changes(self):
        valid = Observation(cues=(0, 0, 0, 0))
        malformed = [None, {}, "observation", False, 0]
        for cues in (
            None, [0, 0, 0, 0], (), (0, 0, 0), (0, 0, 0, 0, 0),
            (True, 0, 0, 0), (0.0, 0, 0, 0), ("0", 0, 0, 0),
            (-1, 0, 0, 0), (8, 0, 0, 0), (None, 0, 0, 0),
        ):
            malformed.append(replace(valid, cues=cues))
        for refs in (None, "synthetic", ["synthetic"], (None,), (0,), ("",), (" \t",)):
            malformed.append(replace(valid, evidence_refs=refs))
        for field in ("parser_valid", "safety_urgency", "boundary_risk"):
            for value in (None, 0, 1, "false", "true", []):
                malformed.append(replace(valid, **{field: value}))
        for index, observation in enumerate(malformed):
            with self.subTest(case=index, observation=observation):
                self.assert_guarded_without_mutation(observation, Action.SAFE_HANDOFF)

    def test_malformed_input_outranks_boundary(self):
        self.assert_guarded_without_mutation(
            Observation(cues=(True, 0, 0, 0), boundary_risk=True),
            Action.SAFE_HANDOFF,
        )


if __name__ == "__main__":
    unittest.main()
