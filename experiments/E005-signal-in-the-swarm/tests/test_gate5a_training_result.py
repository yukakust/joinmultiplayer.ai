import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / "site/experiments/E005/gate-5a-training-v0.1.json"
ARTIFACTS = ROOT / "experiments/E005-signal-in-the-swarm/artifacts"


class Gate5ATrainingResultTests(unittest.TestCase):
    def test_public_checkpoint_matches_private_summaries(self):
        public = json.loads(PUBLIC.read_text(encoding="utf-8"))
        private = {
            skill: json.loads((ARTIFACTS / f"gate5a-{skill}-v0.1/summary.json").read_text(encoding="utf-8"))
            for skill in ("cause", "safety")
        }
        for run in public["runs"]:
            source = private[run["skill"]]
            for key in ("examples", "trainable_parameters", "loss_mean_first_24", "loss_mean_last_24", "adapter_sha256"):
                self.assertEqual(run[key], source[key])

    def test_training_does_not_claim_exam_success(self):
        public = json.loads(PUBLIC.read_text(encoding="utf-8"))
        self.assertTrue(public["base_unchanged"])
        self.assertFalse(public["exam_run"])
        self.assertIn("does not show transfer or composition", public["claim_boundary"]["en"])


if __name__ == "__main__":
    unittest.main()
