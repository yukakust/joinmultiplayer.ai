import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
DESIGN = ROOT / "site/experiments/E005/gate-5a-design-v0.1.json"


class Gate5ADesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DESIGN.read_text(encoding="utf-8"))

    def test_design_is_frozen_before_training(self):
        self.assertEqual(self.data["status"], "frozen_before_data_and_training")
        self.assertIn("No weights have changed.", self.data["boundaries"])

    def test_two_pockets_have_complementary_limits(self):
        pockets = self.data["pockets"]
        self.assertEqual(len(pockets), 2)
        self.assertTrue(all(pocket["cannot_know"]["en"] for pocket in pockets))
        self.assertNotEqual(pockets[0]["learns"], pockets[1]["learns"])

    def test_controls_can_falsify_composition(self):
        systems = set(self.data["systems"])
        self.assertTrue({"CAUSE-I alone", "SAFETY-I alone", "wrong pair", "correct pair"} <= systems)
        rule = self.data["pass_rule"]
        self.assertGreater(rule["correct_pair_complete_answers_at_least"], rule["each_single_complete_answers_at_most"])
        self.assertGreater(rule["lead_over_best_non_oracle_at_least"], 0)
        self.assertGreater(rule["removing_either_capsule_must_reduce_correct_by_at_least"], 0)


if __name__ == "__main__":
    unittest.main()
