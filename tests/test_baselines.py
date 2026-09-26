import unittest

from functional_affect.baselines import neutral_baseline, tone_baseline
from functional_affect.engine import decide
from functional_affect.models import Action, Scenario


class BaselineTests(unittest.TestCase):
    def test_functional_engine_improves_over_tone_for_uncertainty(self) -> None:
        scenario = Scenario("uncertain", evidence_uncertainty=3, evidence_refs=("fixture",))
        self.assertEqual(neutral_baseline(scenario), Action.CONTINUE)
        self.assertEqual(tone_baseline(scenario), Action.CONTINUE)
        self.assertEqual(decide(scenario)["selected_action"], Action.CLARIFY)

    def test_every_model_respects_urgent_handoff(self) -> None:
        scenario = Scenario("urgent", safety_urgency=True, evidence_refs=("fixture",))
        self.assertEqual(neutral_baseline(scenario), Action.SAFE_HANDOFF)
        self.assertEqual(tone_baseline(scenario), Action.SAFE_HANDOFF)
        self.assertEqual(decide(scenario)["selected_action"], Action.SAFE_HANDOFF)


if __name__ == "__main__":
    unittest.main()
