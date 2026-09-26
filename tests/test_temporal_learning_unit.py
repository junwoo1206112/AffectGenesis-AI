import unittest

from temporal_experience.contracts import ExperimentAction, Feedback, PublicObservation
from temporal_learning.learner import ModelKind, TemporalLearner, Token


class TemporalLearningTests(unittest.TestCase):
    def test_preupdate_prediction_and_checkpoint(self):
        model=TemporalLearner(ModelKind.AFFECT)
        model.observe(ExperimentAction.TRY, Feedback(ExperimentAction.TRY,"failure",-1,False))
        self.assertEqual(model.counts[((Token.BOS,Token.BOS),ExperimentAction.TRY,Token.TF)],1)
        saved=model.checkpoint("x")
        restored=TemporalLearner.from_checkpoint(saved,"x")
        self.assertEqual(saved,restored.checkpoint("x"))

    def test_scalar_and_reset(self):
        model=TemporalLearner(ModelKind.AFFECT)
        model.observe(ExperimentAction.TRY, Feedback(ExperimentAction.TRY,"failure",-1,False))
        self.assertGreater(model.scalar,0)
        model.reset_scalar(); self.assertEqual(model.scalar,0)
        model.reset_episode(); self.assertEqual(model.context,(Token.BOS,Token.BOS))

    def test_failure_trace_is_nonnegative_and_counts_no_learning(self):
        model=TemporalLearner(ModelKind.FAILURE_TRACE)
        before=deepcopy_counts(model)
        model.observe(ExperimentAction.SAFE,Feedback(ExperimentAction.SAFE,"done",.1,False),learn_counts=False)
        self.assertEqual(before,model.counts)
        self.assertIn(model.predict(PublicObservation()).action,ExperimentAction)

def deepcopy_counts(model): return dict(model.counts)
