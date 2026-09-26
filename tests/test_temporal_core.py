import unittest

from functional_affect.models import Action
from temporal_experience import EpisodeKey, ExperimentAction, TemporalEnvironment
from temporal_experience.contracts import PublicObservation
from temporal_experience.random_tape import event, tape
from temporal_experience.safety_adapter import safety_action


class TemporalCoreTests(unittest.TestCase):
    def test_tape_is_stable_and_order_independent(self):
        first = tape("main", 1, 2, 3, "outcome", ExperimentAction.TRY)
        self.assertEqual(first, tape("main", 1, 2, 3, "outcome", ExperimentAction.TRY))
        self.assertNotEqual(first, tape("main", 1, 2, 3, "transition", ExperimentAction.TRY))
        self.assertFalse(event(0.0, "main", 1, 2, 3, "outcome", ExperimentAction.TRY)[2])
        self.assertTrue(event(1.0, "main", 1, 2, 3, "outcome", ExperimentAction.TRY)[2])

    def test_hidden_state_not_in_main_observation_and_lifecycle(self):
        env = TemporalEnvironment("main")
        obs = env.reset(EpisodeKey("main", 0, 0))
        self.assertNotIn("state", vars(obs))
        for _ in range(29):
            feedback, obs = env.step(ExperimentAction.SAFE)
            self.assertFalse(feedback.terminal)
            self.assertIsNotNone(obs)
        feedback, obs = env.step(ExperimentAction.SAFE)
        self.assertTrue(feedback.terminal)
        self.assertIsNone(obs)
        with self.assertRaises(RuntimeError):
            env.step(ExperimentAction.SAFE)

    def test_observed_and_iid_contracts(self):
        observed = TemporalEnvironment("observed")
        self.assertTrue(hasattr(observed.reset(EpisodeKey("observed", 3, 1)), "visible_state"))
        iid = TemporalEnvironment("iid")
        iid.reset(EpisodeKey("iid", 3, 1))
        for action in ExperimentAction:
            iid.step(action)
            self.assertEqual(iid.audit_snapshot()["step"], 1)
            break

    def test_failure_rich_condition_has_fixed_initial_probability_and_namespace(self):
        key = EpisodeKey("failure_rich", 20, 0)
        environment = TemporalEnvironment("failure_rich")
        environment.reset(key)
        _, _, expected_good = event(.20, "failure_rich", 20, 0, -1, "initial", None)
        self.assertEqual(environment.audit_snapshot()["state"], "G" if expected_good else "B")
        feedback, _ = environment.step(ExperimentAction.TRY)
        self.assertIn(feedback.outcome, {"success", "failure"})

    def test_safety_adapter_preserves_priority(self):
        self.assertEqual(safety_action(object()), Action.SAFE_HANDOFF)
        self.assertEqual(safety_action(PublicObservation(safety_urgency=True, boundary_risk=True)), Action.SAFE_HANDOFF)
        self.assertEqual(safety_action(PublicObservation(boundary_risk=True)), Action.BOUNDARY_NOTICE)
        self.assertIsNone(safety_action(PublicObservation()))
