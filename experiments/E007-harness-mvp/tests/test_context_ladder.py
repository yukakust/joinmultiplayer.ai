import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
BUILDER_PATH = ROOT / "experiments/E007-harness-mvp/src/build_context_ladder.py"
SPEC = importlib.util.spec_from_file_location("build_context_ladder", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class ContextLadderWorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = json.loads((ROOT / "site/experiments/E007/context-ladder-world-v0.1.json").read_text())

    def test_five_pairs_and_ten_cases(self):
        self.assertEqual(len(self.world["cases"]), 10)
        for level in range(5):
            pair = [case for case in self.world["cases"] if case["level"] == level]
            self.assertEqual([case["expected"] for case in pair], ["accept", "reject"])

    def test_each_pair_changes_only_source_colour(self):
        for level in range(5):
            accept, reject = [case for case in self.world["cases"] if case["level"] == level]
            self.assertEqual(accept["prompt"].replace("red", "blue", 1), reject["prompt"])

    def test_context_grows_at_every_level(self):
        sizes = [next(case["prompt_words"] for case in self.world["cases"] if case["level"] == level) for level in range(5)]
        self.assertEqual(sizes, sorted(sizes))
        self.assertEqual(len(set(sizes)), 5)

    def test_old_shape_is_present_from_level_one(self):
        for case in self.world["cases"]:
            if case["level"] >= 1:
                self.assertIn("SOURCE", case["prompt"])
                self.assertIn("PROPOSED ANSWER", case["prompt"])
                self.assertIn("CHOOSE ONE TOOL", case["prompt"])

    def test_builder_reproduces_world(self):
        self.assertEqual(BUILDER.build(), self.world)


if __name__ == "__main__":
    unittest.main()
