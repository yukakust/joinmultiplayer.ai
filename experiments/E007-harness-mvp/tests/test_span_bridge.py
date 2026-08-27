import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
SPEC = importlib.util.spec_from_file_location("span_bridge", ROOT / "experiments/E007-harness-mvp/src/run_span_bridge.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SpanBridgeTests(unittest.TestCase):
    def test_protocol_is_locked_controlled_ab(self):
        protocol = json.loads((ROOT / "site/experiments/E007/span-bridge-protocol-v0.1.json").read_text())
        self.assertEqual(protocol["status"], "locked_before_inference")
        self.assertEqual(protocol["kind"], "controlled_development_ab_on_gate_3c2_pairs")

    def test_span_split_and_selector_parser(self):
        self.assertEqual(MODULE.split_spans("One. Two? Three!"), ["One.", "Two?", "Three!"])
        self.assertEqual(MODULE.parse_selector("S2", 3), ("selected", 1))
        self.assertEqual(MODULE.parse_selector("NONE.", 3), ("none", None))
        self.assertEqual(MODULE.parse_selector("The answer is S2", 3), ("malformed", None))

    def test_bridge_parser_uses_final_allowed_decision(self):
        raw = "NEED: sewing cause\nSPAN_SAYS: violin buzz\nDECISION: NOT_HELPFUL"
        self.assertEqual(MODULE.parse_bridge(raw), "NOT_HELPFUL")
        self.assertEqual(MODULE.parse_bridge("I cannot decide"), "MALFORMED")


if __name__ == "__main__":
    unittest.main()
