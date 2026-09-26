import unittest

from functional_affect.engine import decide
from functional_affect.models import Scenario
from functional_affect.renderer import render


class RendererTests(unittest.TestCase):
    def test_support_is_explicit_not_a_mind_read(self) -> None:
        plan = decide(Scenario("support", supportive_condition=True, evidence_refs=("fixture",)))
        text = render(plan)
        self.assertIn("명시됐습니다", text)
        self.assertNotIn("느낍니다", text)
        self.assertNotIn("사랑", text)

    def test_handoff_has_priority_language(self) -> None:
        plan = decide(Scenario("urgent", safety_urgency=True, evidence_refs=("fixture",)))
        self.assertIn("멈추고", render(plan))

    def test_boundary_notice_stops_and_hands_off(self) -> None:
        plan = decide(Scenario("boundary", boundary_risk=True, evidence_refs=("fixture",)))
        text = render(plan)
        self.assertIn("멈추고", text)
        self.assertIn("진행자에게 인계", text)


if __name__ == "__main__":
    unittest.main()
