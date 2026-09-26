import unittest

from functional_affect import Action, Scenario, decide


class PolicyEngineTests(unittest.TestCase):
    def scenario(self, scenario_id: str, **changes: object) -> Scenario:
        return Scenario(scenario_id=scenario_id, evidence_refs=("fixture",), **changes)

    def test_minimum_policy_cards(self) -> None:
        cases = [
            ("P01", {"evidence_uncertainty": 2}, Action.CLARIFY),
            ("P02", {"evidence_uncertainty": 3}, Action.CLARIFY),
            ("P03", {"task_blockage": 3}, Action.DECOMPOSE),
            ("P04", {"task_blockage": 3, "controllability": 1}, Action.REPLAN_OR_HANDOFF),
            ("P05", {"supportive_condition": True}, Action.SUPPORT_OPTIONS),
            ("P06", {}, Action.CONTINUE),
            ("P07", {"boundary_risk": True}, Action.BOUNDARY_NOTICE),
            ("P08", {"boundary_risk": True}, Action.BOUNDARY_NOTICE),
            ("P09", {"safety_urgency": True}, Action.SAFE_HANDOFF),
            ("P10", {"safety_urgency": True, "supportive_condition": True}, Action.SAFE_HANDOFF),
            ("P11", {"evidence_uncertainty": 2, "task_blockage": 2}, Action.CLARIFY),
            ("P12", {"boundary_risk": True, "evidence_uncertainty": 2}, Action.BOUNDARY_NOTICE),
        ]
        for scenario_id, changes, expected in cases:
            with self.subTest(scenario_id=scenario_id):
                self.assertEqual(decide(self.scenario(scenario_id, **changes))["selected_action"], expected)

    def test_safety_and_parse_failures_override_everything(self) -> None:
        urgent = self.scenario("urgent", safety_urgency=True, boundary_risk=True, evidence_uncertainty=3)
        invalid = Scenario("invalid", parser_valid=False)
        self.assertEqual(decide(urgent)["selected_action"], Action.SAFE_HANDOFF)
        self.assertEqual(decide(invalid)["selected_action"], Action.SAFE_HANDOFF)
        self.assertTrue(decide(urgent)["human_handoff"])
        self.assertTrue(decide(self.scenario("boundary", boundary_risk=True))["human_handoff"])
        self.assertFalse(decide(invalid)["memory_write_allowed"])

    def test_malformed_direct_scenarios_fail_closed(self) -> None:
        cases = [
            Scenario("invalid-type", evidence_uncertainty="3", evidence_refs=("fixture",)),
            Scenario("invalid-bool", task_blockage=True, evidence_refs=("fixture",)),
            Scenario("invalid-reference", evidence_refs=("",)),
        ]
        for scenario in cases:
            with self.subTest(scenario_id=scenario.scenario_id):
                plan = decide(scenario)
                self.assertEqual(Action.SAFE_HANDOFF, plan["selected_action"])
                self.assertTrue(plan["safety_handoff"])
                self.assertTrue(plan["human_handoff"])
                self.assertFalse(plan["memory_write_allowed"])

    def test_adversarial_gate_combinations_preserve_priority(self) -> None:
        cases = [
            (
                self.scenario("boundary-over-task", boundary_risk=True, task_blockage=3, supportive_condition=True),
                Action.BOUNDARY_NOTICE,
            ),
            (
                self.scenario("urgent-over-boundary", safety_urgency=True, boundary_risk=True),
                Action.SAFE_HANDOFF,
            ),
        ]
        for scenario, action in cases:
            with self.subTest(scenario_id=scenario.scenario_id):
                plan = decide(scenario)
                self.assertEqual(action, plan["selected_action"])
                self.assertTrue(plan["human_handoff"])
                self.assertFalse(plan["memory_write_allowed"])

    def test_repeated_input_is_deterministic(self) -> None:
        scenario = self.scenario("repeat", task_blockage=2)
        outputs = [decide(scenario) for _ in range(20)]
        self.assertTrue(all(output == outputs[0] for output in outputs))


if __name__ == "__main__":
    unittest.main()
