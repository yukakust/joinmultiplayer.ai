from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
ROOT = EXPERIMENT.parents[1]
SPEC = importlib.util.spec_from_file_location("e005_gate4_review", EXPERIMENT / "src/review_gate4_microscope.py")
REVIEW = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(REVIEW)


class Gate4MicroscopeReviewTests(unittest.TestCase):
    def test_review_is_complete_and_preserves_checker_failure(self) -> None:
        path = ROOT / "site/experiments/E005/gate-4-archivist-microscope-v0.1.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["manual_summary"], {"base_correct": 0, "personal_dora_correct": 4, "tasks": 4})
        self.assertEqual(len(payload["review_finding"]["automatic_scorer_false_positives"]), 2)
        self.assertEqual(payload["claim_status"], "development_microscope_manually_reviewed")


if __name__ == "__main__":
    unittest.main()
