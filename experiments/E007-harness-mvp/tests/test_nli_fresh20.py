import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "site/experiments/E007/nli-fresh20-short-protocol-v0.1.json"
WORLD = ROOT / "site/experiments/E007/nli-fresh20-short-world-v0.1.json"


class FreshTwentyTest(unittest.TestCase):
    def test_distribution_and_manual_reasons(self):
        world = json.loads(WORLD.read_text())
        labels = [item["expected"] for item in world["items"]]
        self.assertEqual(len(labels), 20)
        self.assertEqual(labels.count("entailment"), 7)
        self.assertEqual(labels.count("contradiction"), 7)
        self.assertEqual(labels.count("neutral"), 6)
        self.assertTrue(all(item["gold_reason"].strip() for item in world["items"]))

    def test_gate_and_model_are_frozen(self):
        protocol = json.loads(PROTOCOL.read_text())
        self.assertEqual(protocol["status"], "frozen_before_inference")
        self.assertEqual(protocol["locked_development_gate"]["total_correct_at_least"], 18)
        self.assertEqual(len(protocol["model"]["revision"]), 40)


if __name__ == "__main__":
    unittest.main()
