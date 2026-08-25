from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class Gate5B3PublicationTest(unittest.TestCase):
    def test_xray_reproduced_every_frozen_answer(self):
        result = json.loads((ROOT / "site/experiments/E005/gate-5b3-xray-results-v0.1.json").read_text())
        self.assertEqual(result["question_count"], 32)
        self.assertTrue(result["all_answers_reproduced"])
        self.assertEqual(len(result["records"]), 32)
        self.assertTrue(all(row["tokens"][-1]["is_stop"] for row in result["records"]))

    def test_xray_page_is_routed_and_links_raw_data(self):
        app = (ROOT / "site/app.js").read_text()
        self.assertIn('path === "experiment/e005/gate-5b/xray"', app)
        self.assertIn("gate-5b3-xray-results-v0.1.json", app)
        self.assertIn("ОТКРЫТЬ НЕЙРОННЫЙ РЕНТГЕН", app)

    def test_conclusion_preserves_the_claim_boundary(self):
        conclusion = json.loads((ROOT / "site/experiments/E005/gate-5b3-conclusion-v0.1.json").read_text())
        self.assertEqual(conclusion["status"], "diagnostic_complete_no_training")
        self.assertIn("не то", conclusion["claim_boundary"]["ru"])


if __name__ == "__main__":
    unittest.main()
