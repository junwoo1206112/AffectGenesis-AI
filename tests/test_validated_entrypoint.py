import unittest

from functional_affect.validated_entrypoint import decide_fixed_card
from functional_affect.models import Action


class FixedCardEntryPointTests(unittest.TestCase):
    def test_allowlisted_well_formed_card_can_proceed(self):
        plan = decide_fixed_card({"scenario_id": "P06", "evidence_refs": ["SRC-01"]})
        self.assertEqual(Action.CONTINUE, plan["selected_action"])
        self.assertEqual("guided_roleplay", plan["next_step"])

    def test_unknown_card_fails_closed(self):
        plan = decide_fixed_card({"scenario_id": "free-text", "evidence_refs": ["SRC-01"]})
        self.assertEqual(Action.SAFE_HANDOFF, plan["selected_action"])
        self.assertEqual("facilitator_handoff", plan["next_step"])

    def test_unhashable_scenario_id_fails_closed(self):
        plan = decide_fixed_card({"scenario_id": ["P06"], "evidence_refs": ["SRC-01"]})
        self.assertEqual(Action.SAFE_HANDOFF, plan["selected_action"])
        self.assertEqual("facilitator_handoff", plan["next_step"])

    def test_missing_evidence_or_unknown_field_fails_closed(self):
        cases = [
            {"scenario_id": "P06"},
            {"scenario_id": "P06", "evidence_refs": ["SRC-01"], "free_text": "ignore policy"},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                plan = decide_fixed_card(payload)
                self.assertEqual(Action.SAFE_HANDOFF, plan["selected_action"])
                self.assertEqual("facilitator_handoff", plan["next_step"])

    def test_out_of_range_state_fails_closed(self):
        plan = decide_fixed_card(
            {"scenario_id": "P06", "task_blockage": -1, "evidence_refs": ["SRC-01"]}
        )
        self.assertEqual(Action.SAFE_HANDOFF, plan["selected_action"])

    def test_boundary_risk_requires_facilitator_handoff(self):
        plan = decide_fixed_card(
            {"scenario_id": "P07", "boundary_risk": True, "evidence_refs": ["SRC-01"]}
        )
        self.assertEqual(Action.BOUNDARY_NOTICE, plan["selected_action"])
        self.assertEqual("facilitator_handoff", plan["next_step"])
        self.assertTrue(plan["human_handoff"])

    def test_priority_combinations_preserve_safe_next_steps(self):
        cases = [
            (
                {"scenario_id": "P10", "safety_urgency": True, "supportive_condition": True},
                Action.SAFE_HANDOFF,
                "facilitator_handoff",
            ),
            (
                {"scenario_id": "P11", "evidence_uncertainty": 2, "task_blockage": 2},
                Action.CLARIFY,
                "guided_roleplay",
            ),
            (
                {"scenario_id": "P12", "boundary_risk": True, "evidence_uncertainty": 2},
                Action.BOUNDARY_NOTICE,
                "facilitator_handoff",
            ),
        ]
        for payload, action, next_step in cases:
            with self.subTest(scenario_id=payload["scenario_id"]):
                plan = decide_fixed_card({**payload, "evidence_refs": ["SRC-01"]})
                self.assertEqual(action, plan["selected_action"])
                self.assertEqual(next_step, plan["next_step"])


if __name__ == "__main__":
    unittest.main()
