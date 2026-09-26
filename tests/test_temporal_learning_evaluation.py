import unittest

from temporal_learning.evaluation import evaluate_checkpoint, train_seed, training_action
from temporal_learning.learner import ModelKind


class TemporalLearningEvaluationTests(unittest.TestCase):
    def test_common_behavior_and_frozen_evaluation(self):
        self.assertEqual(training_action(2, 3, 4), training_action(2, 3, 4))
        snapshots, rows = train_seed(1, 2, (0, 2), "config", (ModelKind.COUNTS, ModelKind.AFFECT))
        self.assertEqual(len(rows), 60)
        self.assertEqual(set(snapshots), {0, 2})
        self.assertEqual(snapshots[2][ModelKind.COUNTS]["counts"], snapshots[2][ModelKind.AFFECT]["counts"])
        checkpoint = snapshots[2][ModelKind.AFFECT]
        before = checkpoint["counts"].copy()
        score, evaluation_rows = evaluate_checkpoint(checkpoint, "config", "test_A", 1, 2, 2)
        self.assertIsInstance(score, float)
        self.assertEqual(len(evaluation_rows), 60)
        self.assertEqual(before, checkpoint["counts"])
