import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = ROOT / "site/experiments/E007/nli-deberta-protocol-v0.1.json"
WORLD = ROOT / "site/experiments/E007/nli-minilm-world-v0.1.json"


class NliDebertaProtocolTest(unittest.TestCase):
    def test_reuses_exact_open_world(self):
        protocol = json.loads(PROTOCOL.read_text())
        world = json.loads(WORLD.read_text())
        self.assertTrue(protocol["frozen_design"]["baseline_already_opened"])
        self.assertEqual(protocol["frozen_design"]["cases"], len(world["items"]))

    def test_model_and_gate_are_pinned(self):
        protocol = json.loads(PROTOCOL.read_text())
        self.assertEqual(len(protocol["model"]["revision"]), 40)
        self.assertEqual(protocol["locked_development_gate"]["total_correct_at_least"], 9)
        self.assertTrue(protocol["locked_development_gate"]["beat_minilm_7_of_10"])


if __name__ == "__main__":
    unittest.main()
