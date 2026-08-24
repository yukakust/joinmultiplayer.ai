import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "site/experiments/E005/gate-5b-preflight-v0.1.json"


class Gate5BPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(RESULT.read_text(encoding="utf-8"))

    def test_fresh_tracks_are_an_exact_noop(self):
        self.assertEqual(self.data["fresh_cause_delta_max_abs"], 0)
        self.assertEqual(self.data["fresh_safety_delta_max_abs"], 0)
        self.assertEqual(self.data["fresh_logits_max_abs_difference"], 0)

    def test_real_middle_tracks_are_isolated(self):
        self.assertEqual(self.data["split"], {"stem": [0, 5], "track": [6, 21], "tail": [22, 27]})
        self.assertEqual(self.data["dora_modules_per_track"], 112)
        self.assertTrue(self.data["cause_selection_only_changes_cause_track"])
        self.assertTrue(self.data["safety_selection_only_changes_safety_track"])
        self.assertEqual(self.data["trainable_parameters"]["cause"], self.data["trainable_parameters"]["safety"])

    def test_checkpoint_cannot_claim_training(self):
        self.assertFalse(self.data["training_performed"])
        self.assertEqual(self.data["status"], "passed_before_training")


if __name__ == "__main__":
    unittest.main()
