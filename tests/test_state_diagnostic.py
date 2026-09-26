import importlib.util
from dataclasses import replace
from pathlib import Path
import unittest

from affect_growth.environment import make_dataset
from affect_growth.learner import Learner
from affect_growth.models import Feedback
from functional_affect.models import Action


spec = importlib.util.spec_from_file_location(
    "state_diagnostic", Path(__file__).resolve().parents[1] / "scripts/diagnose_state_influence.py")
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class StateDiagnosticTests(unittest.TestCase):
    def test_positive_control_detects_state_switch(self):
        class NearTieLearner(Learner):
            def _estimates(self, observation):
                return (0.9, 0.05, 0.05), [0.45, 0.1, 0.5]

        case = replace(make_dataset(0, "dev")[0],
                       feedback=Feedback(0, Action.DECOMPOSE, 0))
        row = diagnostic.inspect(NearTieLearner(), [case] * 100, 0)
        self.assertEqual(row["forced_one_switches"], 100)
        self.assertGreater(row["observed_switches"], 0)
        self.assertEqual(row["decompose"], 100)

    def test_frozen_gate_and_source_preservation(self):
        model = Learner("frozen")
        model.frustration = 0.4
        before = model.to_dict("test")
        row = diagnostic.inspect(model, make_dataset(0, "dev"), 0)
        result = diagnostic.aggregate([row])
        self.assertEqual(result["n"], 100)
        self.assertEqual(result["uncertain"], 100)
        self.assertEqual(result["observed_switches"], 0)
        self.assertEqual(result["forced_one_switches"], 0)
        self.assertIsNone(result["decompose_margin_min"])
        self.assertGreater(result["state_positive"], 0)
        self.assertEqual(before, model.to_dict("test"))

    def test_learned_partition(self):
        model = Learner()
        for case in make_dataset(0, "train"):
            model.learn(case.observation, case.feedback)
        row = diagnostic.inspect(model, make_dataset(0, "dev"), 0)
        self.assertEqual(row["n"], row["uncertain"] + row["non_decompose"] + row["decompose"])
        self.assertEqual(len(row["decompose_margins"]), row["decompose"])
        self.assertEqual(len(row["states"]), 100)
