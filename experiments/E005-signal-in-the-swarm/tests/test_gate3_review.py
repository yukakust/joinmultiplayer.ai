from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT / "src"))
SPEC = importlib.util.spec_from_file_location("e005_gate3_review", EXPERIMENT / "src" / "review_gate3.py")
REVIEW = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(REVIEW)


class Gate3ReviewTests(unittest.TestCase):
    def test_review_matrix_is_complete(self) -> None:
        self.assertEqual(set(REVIEW.REVIEWS), {f"PUBLIC-{index:02d}" for index in range(1, 7)})
        for methods in REVIEW.REVIEWS.values():
            self.assertEqual(set(methods), {"lexical", "semantic", "raw_majority", "evidence_graph", "oracle"})
            for labels in methods.values():
                self.assertEqual(len(labels), 2)
                self.assertLessEqual(set(labels), REVIEW.LABELS)

    def test_known_generator_reversals_are_not_marked_correct(self) -> None:
        for method in REVIEW.REVIEWS["PUBLIC-04"].values():
            self.assertNotIn("correct", method)
        self.assertEqual(
            REVIEW.REVIEWS["PUBLIC-06"]["oracle"][0],
            "wrong_or_contradictory",
        )

    def test_every_task_and_label_has_a_bilingual_reason(self) -> None:
        self.assertEqual(set(REVIEW.REVIEW_NOTES), set(REVIEW.REVIEWS))
        for notes in REVIEW.REVIEW_NOTES.values():
            self.assertEqual(set(notes), REVIEW.LABELS)
            for localized in notes.values():
                self.assertEqual(set(localized), {"en", "ru"})
                self.assertTrue(all(localized.values()))


if __name__ == "__main__":
    unittest.main()
