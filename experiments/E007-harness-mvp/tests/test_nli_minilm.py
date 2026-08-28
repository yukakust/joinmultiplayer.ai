import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORLD = ROOT / "site/experiments/E007/nli-minilm-world-v0.1.json"
PROTOCOL = ROOT / "site/experiments/E007/nli-minilm-protocol-v0.1.json"


class NliMiniLmProtocolTest(unittest.TestCase):
    def test_world_is_balanced_as_frozen(self):
        world = json.loads(WORLD.read_text())
        labels = [item["expected"] for item in world["items"]]
        self.assertEqual(len(labels), 10)
        self.assertEqual(labels.count("entailment"), 4)
        self.assertEqual(labels.count("contradiction"), 3)
        self.assertEqual(labels.count("neutral"), 3)

    def test_inputs_are_atomic_and_unique(self):
        world = json.loads(WORLD.read_text())
        self.assertEqual(len({item["id"] for item in world["items"]}), 10)
        for item in world["items"]:
            self.assertTrue(item["premise"].strip())
            self.assertTrue(item["hypothesis"].strip())

    def test_gate_was_frozen(self):
        protocol = json.loads(PROTOCOL.read_text())
        self.assertEqual(protocol["status"], "frozen_before_inference")
        self.assertEqual(protocol["locked_development_gate"]["total_correct_at_least"], 9)


if __name__ == "__main__":
    unittest.main()
