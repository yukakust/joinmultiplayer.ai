import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RESULT = ROOT / "site/experiments/E005/gate-5a2-results-v0.1.json"


class Gate5A2ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(RESULT.read_text(encoding="utf-8"))

    def test_failed_result_preserves_all_outputs(self):
        self.assertEqual(self.data["status"], "failed")
        self.assertEqual(len(self.data["rows"]), 24)
        self.assertEqual(self.data["conditions"], [
            "question_alone", "actual_pair", "cause_only", "safety_only", "oracle_pair"
        ])
        for row in self.data["rows"]:
            self.assertEqual(set(row["conditions"]), set(self.data["conditions"]))
            for condition in self.data["conditions"]:
                self.assertTrue(row["conditions"][condition]["output"].strip())

    def test_human_review_matches_public_summary(self):
        actual = sum(row["conditions"]["actual_pair"]["human_complete"] for row in self.data["rows"])
        oracle = sum(row["conditions"]["oracle_pair"]["human_complete"] for row in self.data["rows"])
        self.assertEqual(actual, 4)
        self.assertEqual(oracle, 4)
        self.assertEqual(self.data["human_complete"], actual)
        self.assertEqual(self.data["automatic_complete"], 1)
        self.assertLess(actual, self.data["required_complete"])

    def test_language_gap_is_explicit(self):
        by_language = {language: 0 for language in ("en", "ru")}
        for row in self.data["rows"]:
            by_language[row["language"]] += int(row["conditions"]["actual_pair"]["human_complete"])
        self.assertEqual(by_language, {"en": 4, "ru": 0})
        self.assertEqual(self.data["language_result"]["en"]["human_complete"], 4)
        self.assertEqual(self.data["language_result"]["ru"]["human_complete"], 0)

    def test_claim_does_not_overreach(self):
        boundary = " ".join(self.data["claim_boundary"].values()).lower()
        for term in ("latent", "routing", "devices", "swarm"):
            self.assertIn(term, boundary)


if __name__ == "__main__":
    unittest.main()
