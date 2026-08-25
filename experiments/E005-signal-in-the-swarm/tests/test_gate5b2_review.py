import importlib.util
import json
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "publish_gate5b2_review.py"
SPEC = importlib.util.spec_from_file_location("publish_gate5b2_review", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Gate5B2ReviewTests(unittest.TestCase):
    def test_real_results_make_expected_audit_queue(self):
        root = Path(__file__).parents[3]
        site = root / "site" / "experiments" / "E005"
        source = json.loads((site / "gate-5b1-results-v0.1.json").read_text())
        judge_a = json.loads((site / "gate-5b2-qwen25-32b-full-v0.6.json").read_text())
        judge_b = json.loads((site / "gate-5b2-qwen14b-full-v0.4.2.json").read_text())
        summary, audit = MODULE.build(source, judge_a, judge_b)
        self.assertEqual(summary["agreement"]["overall_disagreements"], 21)
        self.assertEqual(summary["agreement"]["component_disagreements"], 42)
        self.assertEqual(audit["always_review_count"], 21)
        self.assertEqual(audit["agreement_sample_count"], 24)
        self.assertEqual(audit["total"], 45)
        cells = {(row["condition_hidden_until_review"], row["language"]) for row in audit["items"] if row["reason"] == "agreement_sample"}
        self.assertEqual(len(cells), 12)


if __name__ == "__main__":
    unittest.main()
