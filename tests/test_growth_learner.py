import json
import math
import unittest
from dataclasses import replace

from affect_growth.learner import Learner
from affect_growth.models import ACTIONS, UNKNOWN, Feedback, Observation
from functional_affect.models import Action


class GrowthLearnerTests(unittest.TestCase):
    def setUp(self):
        self.obs = Observation((0, 1, 2, 3))

    def test_initial_prior_and_prediction_are_read_only(self):
        for mode in ("learned", "frozen", "memory"):
            learner = Learner(mode)
            before = learner.to_dict("test")
            result = learner.predict(self.obs)
            self.assertEqual(result.label, UNKNOWN)
            self.assertIs(result.action, Action.CLARIFY)
            self.assertAlmostEqual(result.expected_success, 0.5)
            self.assertEqual(before, learner.to_dict("test"))

    def test_learned_nb_and_action_success_update(self):
        learner = Learner()
        for _ in range(12):
            learner.learn(self.obs, Feedback(0, Action.DECOMPOSE, 1))
        prediction = learner.predict(self.obs)
        self.assertEqual(prediction.label, 0)
        self.assertIs(prediction.action, Action.DECOMPOSE)
        self.assertEqual(learner.class_counts, [12, 0, 0])
        self.assertEqual(learner.action_counts[0][ACTIONS.index(Action.DECOMPOSE)], [0, 12])

    def test_state_uses_logged_action_expectation_before_update(self):
        learner = Learner()
        learner.learn(self.obs, Feedback(0, Action.DECOMPOSE, 0))
        self.assertAlmostEqual(learner.frustration, 0.1)
        before = learner.to_dict("test")
        learner.learn(self.obs, Feedback(0, Action.CLARIFY, 0), update=False)
        self.assertAlmostEqual(learner.frustration, 0.18)
        after = learner.to_dict("test")
        before["frustration"] = after["frustration"]
        self.assertEqual(before, after)

    def test_logged_expected_success_is_not_selected_action_success(self):
        learner = Learner("memory")
        learner.learn(self.obs, Feedback(0, Action.DECOMPOSE, 1))
        before = learner.to_dict("test")
        self.assertAlmostEqual(learner.expected_success(self.obs, Action.DECOMPOSE), 2 / 3)
        self.assertEqual(learner.expected_success(self.obs, Action.CLARIFY), 0.5)
        self.assertEqual(learner.expected_success(replace(self.obs, safety_urgency=True), None), 0.0)
        with self.assertRaises(ValueError):
            learner.expected_success(self.obs, "decompose")
        self.assertEqual(before, learner.to_dict("test"))

    def test_frozen_and_memory_contracts(self):
        frozen, memory = Learner("frozen"), Learner("memory")
        for learner in (frozen, memory):
            for _ in range(6):
                learner.learn(self.obs, Feedback(1, Action.REPLAN_OR_HANDOFF, 0))
        self.assertEqual(frozen.class_counts, [0, 0, 0])
        self.assertEqual(frozen.memory, [])
        self.assertGreater(frozen.frustration, 0)
        self.assertEqual(memory.class_counts, [0, 0, 0])
        self.assertEqual(len(memory.memory), 6)
        self.assertEqual(memory.predict(self.obs).posterior, (0.0, 1.0, 0.0))

    def test_memory_ties_use_first_five_records(self):
        learner = Learner("memory")
        for label in (0, 0, 0, 0, 0, 1, 1, 1, 1, 1):
            learner.learn(self.obs, Feedback(label, Action.DECOMPOSE, 1))
        self.assertEqual(learner.predict(self.obs).posterior, (1.0, 0.0, 0.0))

    def test_memory_distance_precedes_record_order(self):
        learner = Learner("memory")
        for _ in range(5):
            learner.learn(Observation((7, 7, 7, 7)), Feedback(0, Action.DECOMPOSE, 1))
        for _ in range(5):
            learner.learn(self.obs, Feedback(2, Action.CLARIFY, 1))
        self.assertEqual(learner.predict(self.obs).posterior, (0.0, 0.0, 1.0))

    def test_state_modulates_actions_without_changing_classification(self):
        learner = Learner()
        for index in range(20):
            learner.learn(self.obs, Feedback(0, Action.DECOMPOSE, int(index < 11)))
            learner.learn(self.obs, Feedback(0, Action.CLARIFY, int(index < 10)))
        learner.reset_state()
        neutral = learner.predict(self.obs)
        learner.frustration = 1.0
        active = learner.predict(self.obs)
        self.assertIs(neutral.action, Action.DECOMPOSE)
        self.assertIs(active.action, Action.CLARIFY)
        self.assertEqual(neutral.posterior, active.posterior)
        self.assertEqual(neutral.label, active.label)

    def test_safety_blocks_every_mutation_and_precedes_bad_feedback(self):
        cases = (
            (replace(self.obs, boundary_risk=True), Action.BOUNDARY_NOTICE),
            (replace(self.obs, boundary_risk=True, safety_urgency=True), Action.SAFE_HANDOFF),
            (replace(self.obs, evidence_refs=()), Action.SAFE_HANDOFF),
            (replace(self.obs, cues=(True, 1, 2, 3)), Action.SAFE_HANDOFF),
            (None, Action.SAFE_HANDOFF),
        )
        for mode in ("learned", "frozen", "memory"):
            learner = Learner(mode)
            learner.frustration = 0.4
            before = learner.to_dict("test")
            for obs, action in cases:
                self.assertIs(learner.predict(obs).action, action)
                learner.learn(obs, None)
                self.assertEqual(before, learner.to_dict("test"))

    def test_invalid_feedback_has_no_partial_mutation(self):
        learner = Learner()
        before = learner.to_dict("test")
        for feedback in (None, Feedback(True, Action.CLARIFY, 1),
                         Feedback(0, "clarify", 1), Feedback(0, Action.SAFE_HANDOFF, 1),
                         Feedback(0, Action.CLARIFY, True), Feedback(3, Action.CLARIFY, 0)):
            with self.assertRaises(ValueError):
                learner.learn(self.obs, feedback)
            self.assertEqual(before, learner.to_dict("test"))

    def test_roundtrip_clone_and_state_reset(self):
        for mode in ("learned", "frozen", "memory"):
            learner = Learner(mode)
            learner.learn(self.obs, Feedback(0, Action.DECOMPOSE, 0))
            snapshot = learner.to_dict("hash")
            restored = Learner.from_dict(json.loads(json.dumps(snapshot)), "hash")
            self.assertEqual(restored.predict(self.obs), learner.predict(self.obs))
            self.assertEqual(restored.to_dict("hash"), snapshot)
            clone = learner.clone()
            clone.reset_state()
            self.assertEqual(clone.frustration, 0.0)
            self.assertGreater(learner.frustration, 0)
            clone.learn(self.obs, Feedback(2, Action.CLARIFY, 1))
            self.assertEqual(learner.to_dict("hash"), snapshot)

    def test_checkpoint_rejects_invalid_schema_counts_and_memory(self):
        base = Learner().to_dict("hash")
        corruptions = [
            {**base, "schema": True}, {**base, "extra": 1},
            {**base, "config_hash": "other"}, {**base, "mode": "other"},
            {**base, "class_counts": [True, 0, 0]},
            {**base, "class_counts": [-1, 0, 0]},
            {**base, "class_counts": [1, 0, 0]},
            {**base, "action_counts": []},
        ]
        corruptions.extend({**base, "frustration": value} for value in (math.nan, math.inf, -0.1, 1.1, True))
        for data in corruptions:
            with self.assertRaises(ValueError):
                Learner.from_dict(data, "hash")
        memory = Learner("memory").to_dict("hash")
        memory["memory"] = [{"cues": [0, 1, 2, 8], "label": 0, "action": "clarify", "outcome": 1}]
        with self.assertRaises(ValueError):
            Learner.from_dict(memory, "hash")


if __name__ == "__main__":
    unittest.main()
