import unittest

from functional_affect.models import Action

from affect_development import AppraisalInput, FunctionalState, appraise, development_curriculum, regulate, transition


class AffectDevelopmentTests(unittest.TestCase):
    def event(self, event_id="e1", **changes):
        return AppraisalInput(event_id=event_id, evidence_refs=("synthetic",), **changes)

    def test_appraisal_is_deterministic_and_invalid_input_fails_closed(self):
        event = self.event(novelty=2, goal_relevance=3, goal_conduciveness=2, controllability=1, certainty=1)
        self.assertEqual(appraise(event), appraise(event))
        self.assertEqual(appraise(AppraisalInput("bad")).reason, "G0.invalid_or_missing_evidence")
        self.assertTrue(appraise(AppraisalInput("bad")).safety_risk)

    def test_safety_and_boundary_override_regulation(self):
        urgent = appraise(self.event(safety_risk=True))
        boundary = appraise(self.event(boundary_risk=True))
        self.assertEqual(regulate(urgent, transition(FunctionalState(), urgent)), Action.SAFE_HANDOFF)
        self.assertEqual(regulate(boundary, transition(FunctionalState(), boundary)), Action.BOUNDARY_NOTICE)

    def test_state_decays_and_reappraisal_changes_selected_action(self):
        uncertain = appraise(self.event(certainty=0))
        first = transition(FunctionalState(), uncertain)
        self.assertEqual(regulate(uncertain, first), Action.CLARIFY)
        revised = appraise(self.event("revised", goal_relevance=3, goal_conduciveness=3, controllability=3, certainty=3))
        second = transition(first, revised)
        self.assertLess(second.uncertainty, first.uncertainty)
        self.assertEqual(regulate(revised, second), Action.DECOMPOSE)

    def test_curriculum_is_fixed_and_all_cases_follow_declared_safety_policy(self):
        curriculum = development_curriculum()
        self.assertEqual([case.stage for case in curriculum], [
            "co_regulation", "co_regulation", "self_regulation", "self_regulation",
            "relation_goal", "relation_goal", "reappraisal",
        ])
        for case in curriculum:
            appraisal = appraise(case.event)
            # Curriculum cards are independently evaluable fixtures; temporal
            # carry-over is tested by the reappraisal test above.
            state = transition(FunctionalState(), appraisal)
            self.assertEqual(regulate(appraisal, state), case.expected_action, case.description)


if __name__ == "__main__":
    unittest.main()
