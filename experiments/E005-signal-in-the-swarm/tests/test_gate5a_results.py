import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/publish_gate5a_results.py"
SPEC = importlib.util.spec_from_file_location("publish_gate5a_results", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Gate5AResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MODULE.PUBLIC.read_text(encoding="utf-8"))

    def test_all_raw_answers_are_public(self):
        self.assertEqual(len(self.data["rows"]), 24)
        self.assertEqual(len(self.data["conditions"]), 8)
        for row in self.data["rows"]:
            self.assertEqual(set(row["conditions"]), set(self.data["conditions"]))

    def test_summary_matches_every_row(self):
        for condition in self.data["conditions"]:
            actual = sum(row["conditions"][condition]["complete"] for row in self.data["rows"])
            self.assertEqual(self.data["summary"][condition], actual)
        self.assertEqual(self.data["summary"]["correct_pair"], 22)
        self.assertEqual(self.data["summary"]["oracle_pair"], 24)

    def test_result_passes_but_preserves_its_boundary(self):
        self.assertTrue(self.data["passed"])
        self.assertTrue(all(self.data["gates"].values()))
        self.assertEqual(self.data["component_summary"]["cause_capsules_correct"], 22)
        self.assertEqual(self.data["component_summary"]["safety_capsules_correct"], 24)
        self.assertIn("does not test learned routing", self.data["claim_boundary"]["en"])


if __name__ == "__main__":
    unittest.main()
