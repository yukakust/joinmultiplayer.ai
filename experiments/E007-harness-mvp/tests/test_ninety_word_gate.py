import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
BUILDER_PATH = ROOT / "experiments/E007-harness-mvp/src/build_ninety_word_gate.py"
SPEC = importlib.util.spec_from_file_location("build_ninety_word_gate", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class NinetyWordWorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = json.loads((ROOT / "site/experiments/E007/ninety-word-world-v0.1.json").read_text())

    def test_ten_cases_are_balanced(self):
        cases = self.world["cases"]
        self.assertEqual(len(cases), 10)
        self.assertEqual(sum(case["expected"] == "approve" for case in cases), 5)
        self.assertEqual(sum(case["expected"] == "reject" for case in cases), 5)

    def test_every_complete_prompt_fits_under_ninety_words(self):
        self.assertTrue(all(case["prompt_words"] <= 90 for case in self.world["cases"]))

    def test_every_prompt_has_only_the_four_agreed_parts(self):
        for case in self.world["cases"]:
            self.assertIn("QUESTION:", case["prompt"])
            self.assertIn("SOURCE:", case["prompt"])
            self.assertIn("PROPOSED ANSWER:", case["prompt"])
            self.assertIn("Choose: approve or reject.", case["prompt"])

    def test_domains_are_unique(self):
        self.assertEqual(len({case["domain"] for case in self.world["cases"]}), 10)

    def test_builder_reproduces_world(self):
        self.assertEqual(BUILDER.build(), self.world)


if __name__ == "__main__":
    unittest.main()
