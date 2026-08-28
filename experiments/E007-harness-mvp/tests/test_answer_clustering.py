import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src/run_answer_clustering.py"
SPEC = importlib.util.spec_from_file_location("run_answer_clustering", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AnswerClusteringTests(unittest.TestCase):
    def test_threshold_prefers_higher_value_on_tie(self):
        threshold, metric = MODULE.choose_threshold([0.9, 0.8, 0.3, 0.2], [True, True, False, False])
        self.assertEqual(threshold, 0.8)
        self.assertEqual(metric["f1"], 1.0)

    def test_components_use_transitive_links(self):
        groups = MODULE.components(
            ["A", "B", "C", "D"],
            {("A", "B"): 0.9, ("A", "C"): 0.1, ("A", "D"): 0.1, ("B", "C"): 0.9, ("B", "D"): 0.1, ("C", "D"): 0.1},
            0.8,
        )
        self.assertEqual(groups, [["A", "B", "C"], ["D"]])

    def test_components_keep_low_score_pairs_apart(self):
        groups = MODULE.components(["A", "B"], {("A", "B"): 0.4}, 0.8)
        self.assertEqual(groups, [["A"], ["B"]])


if __name__ == "__main__":
    unittest.main()
