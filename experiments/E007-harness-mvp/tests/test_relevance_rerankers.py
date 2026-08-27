import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src/run_relevance_rerankers.py"
SPEC = importlib.util.spec_from_file_location("run_relevance_rerankers", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RelevanceRerankerTests(unittest.TestCase):
    def test_cosine_rows_ignores_vector_magnitude(self):
        import numpy as np

        left = np.asarray([[1.0, 0.0], [1.0, 1.0]])
        right = np.asarray([[12.0, 0.0], [-2.0, 2.0]])
        result = MODULE.cosine_rows(left, right)
        self.assertAlmostEqual(float(result[0]), 1.0)
        self.assertAlmostEqual(float(result[1]), 0.0)

    def test_percentile_interpolates(self):
        self.assertEqual(MODULE.percentile([0, 10, 20, 30], 0.25), 7.5)

    def test_clean_calibration_creates_unclear_band(self):
        scores = [0.8, 0.9, 0.7, 0.85, 0.1, 0.2, 0.3, 0.15]
        labels = [True] * 4 + [False] * 4
        result = MODULE.calibrate(scores, labels)
        self.assertEqual(result["mode"], "quantile_band")
        self.assertLess(result["reject_at_or_below"], result["accept_at_or_above"])
        self.assertEqual(MODULE.decide(0.5, result), "unclear")

    def test_overlap_uses_one_locked_midpoint(self):
        scores = [0.4, 0.6, 0.3, 0.8, 0.5, 0.7, 0.2, 0.9]
        labels = [True] * 4 + [False] * 4
        result = MODULE.calibrate(scores, labels)
        self.assertEqual(result["mode"], "collapsed_best_calibration_midpoint")
        self.assertEqual(result["reject_at_or_below"], result["accept_at_or_above"])

    def test_evaluation_keeps_groups_separate(self):
        calibration = [
            {"query":"q","passage":"p","relevant":True},
            {"query":"q","passage":"n","relevant":False},
        ] * 4
        heldout = [
            {"id":"u","family":"x","kind":"useful","question":"q","passage":"p"},
            {"id":"h","family":"x","kind":"hard_extra","question":"q","passage":"n"},
            {"id":"o","family":"x","kind":"obvious_extra","question":"q","passage":"n"},
        ]
        def scorer(pairs):
            return [1.0 if passage == "p" else 0.0 for _, passage in pairs]
        result = MODULE.evaluate_method("fake", scorer, calibration, heldout)
        self.assertEqual(result["summary"]["correct"], 3)
        self.assertEqual(result["summary"]["by_kind"]["useful"]["accept"], 1)
        self.assertEqual(result["summary"]["by_kind"]["hard_extra"]["reject"], 1)


if __name__ == "__main__":
    unittest.main()
