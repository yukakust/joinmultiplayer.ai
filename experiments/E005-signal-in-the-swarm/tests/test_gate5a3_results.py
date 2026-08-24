import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "site/experiments/E005/gate-5a3-results-v0.1.json"


class Gate5A3ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(RESULT.read_text(encoding="utf-8"))

    def test_failure_and_improvement_are_both_preserved(self):
        summary = self.data["human_summary"]
        self.assertEqual(summary["previous_coded_base"], 4)
        self.assertEqual(summary["base_semantic_actual_pair"], 11)
        self.assertEqual(summary["instruct_semantic_actual_pair"], 17)
        self.assertLess(summary["instruct_semantic_actual_pair"], summary["required"])
        self.assertEqual(self.data["status"], "failed_but_improved")

    def test_all_168_outputs_remain_public(self):
        self.assertEqual(len(self.data["rows"]), 24)
        self.assertEqual(len(self.data["conditions"]), 7)
        for row in self.data["rows"]:
            self.assertEqual(set(row["conditions"]), set(self.data["conditions"]))
            for result in row["conditions"].values():
                self.assertTrue(result["output"].strip())

    def test_instruct_answers_are_not_cut_off(self):
        for row in self.data["rows"]:
            self.assertFalse(row["conditions"]["instruct_semantic_actual_pair"]["hit_token_limit"])

    def test_language_gap_matches_human_review(self):
        counts = {"en": 0, "ru": 0}
        for row in self.data["rows"]:
            counts[row["language"]] += int(row["conditions"]["instruct_semantic_actual_pair"]["human_complete"])
        self.assertEqual(counts, {"en": 11, "ru": 6})


if __name__ == "__main__":
    unittest.main()
