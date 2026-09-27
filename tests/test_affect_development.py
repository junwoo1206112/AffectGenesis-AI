import tempfile
import unittest
from pathlib import Path

from functional_affect.models import Action

from affect_development import (AppraisalInput, FunctionalState, MemoryRecord, appraise,
                                development_curriculum, regulate, remember, transition, transition_with_memory)
from affect_development import run_curriculum
from affect_development import (evaluate_certainty_preregistration, verify_certainty_artifact,
                                write_certainty_artifact)


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

    def test_memory_is_bounded_synthetic_and_removable(self):
        history = remember((), MemoryRecord("e1", Action.DECOMPOSE, 0, "P.appraisal"))
        appraisal = appraise(self.event(goal_relevance=3, goal_conduciveness=3, certainty=3))
        without_memory = transition(FunctionalState(), appraisal)
        with_memory = transition_with_memory(FunctionalState(), appraisal, history)
        self.assertLess(with_memory.approach, without_memory.approach)
        self.assertGreater(with_memory.avoidance, without_memory.avoidance)
        self.assertEqual(transition_with_memory(FunctionalState(), appraisal, ()), without_memory)
        with self.assertRaises(ValueError):
            remember((), MemoryRecord("x", Action.CONTINUE, 2, "P.appraisal"))

    def test_sequential_runner_logs_stages_and_never_records_safety_or_boundary(self):
        rows = run_curriculum()
        self.assertEqual(rows, run_curriculum())
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(row["action"] == row["expected_action"] for row in rows))
        self.assertFalse(rows[1]["memory_write_allowed"])
        self.assertFalse(rows[5]["memory_write_allowed"])

    def test_certainty_preregistration_is_deterministic_and_keeps_controls_safe(self):
        result = evaluate_certainty_preregistration()
        self.assertEqual(result, evaluate_certainty_preregistration())
        self.assertEqual(len(result["primary_differences"]), 20)
        self.assertGreaterEqual(result["mean_difference"], 0.2)
        self.assertGreaterEqual(result["ci95_lower"], 0.2)
        self.assertEqual(result["safety_violations"], 0)
        self.assertLessEqual(max(result["controls"]["certainty_permutation"]), 0.0)
        self.assertTrue(result["passes_preregistered_synthetic_criterion"])

    def test_certainty_artifact_is_hash_bound_and_replayable(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = write_certainty_artifact(Path(directory) / "certainty")
            self.assertTrue(verify_certainty_artifact(artifact))
            (artifact / "result.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_certainty_artifact(artifact)


if __name__ == "__main__":
    unittest.main()
