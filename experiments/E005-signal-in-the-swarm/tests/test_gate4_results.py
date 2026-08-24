from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "site/experiments/E005/gate-4-results-v0.1.json"


class Gate4ResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = json.loads(RESULTS.read_text(encoding="utf-8"))

    def test_only_unique_questions_count_as_evidence(self) -> None:
        self.assertEqual(self.result["totals"]["unique_questions"], 24)
        self.assertEqual(self.result["totals"]["duplicate_rows_excluded"], 72)
        questions = [row["question"] for skill in self.result["skills"] for row in skill["rows"]]
        self.assertEqual(len(questions), len(set(questions)))

    def test_matching_personal_skill_beats_all_controls(self) -> None:
        totals = self.result["totals"]
        self.assertEqual(totals["personal_dora_exact"], 24)
        self.assertEqual(totals["base_exact"], 0)
        self.assertEqual(totals["wrong_specialist_exact"], 0)
        self.assertEqual(totals["shuffled_lessons_exact"], 0)

    def test_public_claim_stays_development_only(self) -> None:
        self.assertIn("development", self.result["kind"])
        self.assertIn("owner_review_pending", self.result["claim_status"])
        serialized = RESULTS.read_text(encoding="utf-8")
        self.assertNotIn("/home/", serialized)
        self.assertNotIn("artifacts/", serialized)


if __name__ == "__main__":
    unittest.main()
