import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
SPEC = importlib.util.spec_from_file_location("blind_reader", ROOT / "experiments/E007-harness-mvp/src/run_blind_reader.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BlindReaderTests(unittest.TestCase):
    def setUp(self):
        self.protocol = json.loads((ROOT / "site/experiments/E007/blind-reader-protocol-v0.1.json").read_text())

    def test_protocol_is_balanced_and_locked(self):
        self.assertEqual(self.protocol["status"], "locked_before_inference")
        self.assertEqual(len(self.protocol["candidates"]), 16)
        self.assertEqual(sum(item["expected"] == "useful" for item in self.protocol["candidates"]), 8)
        self.assertEqual(sum(item["expected"] == "extra" for item in self.protocol["candidates"]), 8)

    def test_exact_quote_parser(self):
        source = "First sentence. This exact useful sentence appears in the source. Last sentence."
        decision, quote = MODULE.classify("FOUND\nThis exact useful sentence appears in the source.", source)
        self.assertEqual(decision, "found_exact")
        self.assertEqual(quote, "This exact useful sentence appears in the source.")

    def test_none_and_invention_are_distinct(self):
        self.assertEqual(MODULE.classify("NONE", "A source sentence.")[0], "none")
        self.assertEqual(MODULE.classify("FOUND\nAn invented sentence that is not present.", "A source sentence.")[0], "malformed_or_invented")

    def test_published_result_preserves_failed_gate(self):
        result_path = ROOT / "site/experiments/E007/blind-reader-result-v0.1.json"
        if not result_path.exists():
            self.skipTest("locked run has not completed")
        result = json.loads(result_path.read_text())
        self.assertFalse(result["passed_locked_gate"])
        self.assertEqual(result["summary"]["useful_quotes_found"], 7)
        self.assertEqual(result["summary"]["extra_sources_not_accepted_by_exact_quote_gate"], 7)
        self.assertEqual(result["summary"]["invented_or_malformed"], 3)


if __name__ == "__main__":
    unittest.main()
