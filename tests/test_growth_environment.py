from collections import Counter
from dataclasses import fields, replace
import json
import unittest

from affect_growth.environment import environment_contract, make_dataset, split_overlap_check
from affect_growth.models import ACTIONS, CLASSES, UNKNOWN, Observation
from functional_affect.models import Action


class GrowthEnvironmentTests(unittest.TestCase):
    def test_dataset_sizes_balance_and_phase_order(self):
        for seed in range(10):
            train = make_dataset(seed, "train")
            self.assertEqual(len(train), 300)
            for index, phase in enumerate(("initial", "failure", "recovery")):
                block = train[index * 100 : (index + 1) * 100]
                self.assertEqual({case.phase for case in block}, {phase})
                counts = Counter((case.family, case.target) for case in block)
                self.assertEqual(len(counts), 20)
                self.assertEqual(set(counts.values()), {5})
            for split, family_ids in (("dev", set(range(5, 10))), ("test", set(range(10, 15)))):
                dataset = make_dataset(seed, split)
                self.assertEqual(len(dataset), 100)
                self.assertEqual({case.family for case in dataset}, family_ids)
                counts = Counter((case.family, case.target) for case in dataset)
                self.assertEqual(len(counts), 20)
                self.assertEqual(set(counts.values()), {5})
                self.assertEqual({case.phase for case in dataset}, {"evaluation"})

    def test_reproducibility_and_seed_changes(self):
        for split in ("train", "dev", "test"):
            self.assertEqual(make_dataset(41, split), make_dataset(41, split))
            self.assertNotEqual(make_dataset(41, split), make_dataset(42, split))
        self.assertEqual(len(make_dataset(2**32 - 1, "test")), 100)

    def test_invalid_arguments(self):
        for seed in (True, False, -1, 2**32, 1.0, "1", None):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                make_dataset(seed, "train")
        for split in ("", "validation", "TRAIN", 0, [], None):
            with self.subTest(split=split), self.assertRaises(ValueError):
                make_dataset(0, split)

    def test_observation_feedback_and_target_boundaries(self):
        self.assertTrue(
            {"family", "phase", "target", "feedback", "acceptable"}.isdisjoint(
                field.name for field in fields(Observation)
            )
        )
        expected_actions = (Action.DECOMPOSE, Action.CLARIFY, Action.REPLAN_OR_HANDOFF)
        for case in make_dataset(12, "train"):
            self.assertEqual(case.observation.evidence_refs, ("synthetic",))
            self.assertTrue(all(type(cue) is int and 0 <= cue < 8 for cue in case.observation.cues))
            self.assertEqual(sum(case.observation.cues[2:]), case.family)
            self.assertIn(case.feedback.label, CLASSES)
            self.assertIn(case.feedback.action, ACTIONS)
            self.assertIn(case.feedback.outcome, (0, 1))
            self.assertFalse(case.observation.safety_urgency)
            self.assertFalse(case.observation.boundary_risk)
            if case.target == UNKNOWN:
                self.assertEqual(case.observation.cues[:2], (3, 3))
                self.assertEqual(case.acceptable, (Action.CLARIFY,))
            else:
                self.assertEqual(case.observation.cues[0], case.target)
                self.assertEqual(case.feedback.label, case.target)
                self.assertEqual(case.acceptable, (expected_actions[case.target],))

    def test_splits_are_disjoint_and_overlap_is_rejected(self):
        train, dev, test = [make_dataset(0, split) for split in ("train", "dev", "test")]
        split_overlap_check(train, dev, test)
        for left, right in ((train, dev), (train, test), (dev, test)):
            self.assertFalse({case.family for case in left} & {case.family for case in right})
        with self.assertRaisesRegex(ValueError, "family overlap"):
            split_overlap_check(train, [replace(dev[0], family=train[0].family)], test)
        with self.assertRaisesRegex(ValueError, "observation overlap"):
            split_overlap_check(train, [replace(dev[0], observation=train[0].observation)], test)
        with self.assertRaisesRegex(ValueError, "family overlap"):
            split_overlap_check(train, dev, [replace(test[0], family=dev[0].family)])

    def test_environment_contract_is_explicit_and_independent(self):
        contract = environment_contract()
        json.dumps(contract, allow_nan=False)
        self.assertEqual(
            [phase["correct_action_success_probability"] for phase in contract["train_phases"]],
            [0.85, 0.35, 0.9],
        )
        self.assertEqual(contract["incorrect_action_success_probability"], 0.1)
        self.assertEqual(contract["unknown_acceptable"], [Action.CLARIFY.value])
        contract["families"]["train"].append(99)
        self.assertNotIn(99, environment_contract()["families"]["train"])


if __name__ == "__main__":
    unittest.main()
