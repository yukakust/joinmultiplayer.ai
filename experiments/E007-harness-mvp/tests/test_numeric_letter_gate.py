import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
BUILDER_PATH = ROOT / "experiments/E007-harness-mvp/src/build_numeric_letter_gate.py"
SPEC = importlib.util.spec_from_file_location("build_numeric_letter_gate", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class NumericLetterWorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = json.loads((ROOT / "site/experiments/E007/numeric-letter-world-v0.1.json").read_text())

    def test_two_mirrored_decks(self):
        self.assertEqual(self.world["decks"]["X"], {"1": "approve", "A": "reject"})
        self.assertEqual(self.world["decks"]["Y"], {"1": "reject", "A": "approve"})
        self.assertEqual(len(self.world["items"]), 20)

    def test_each_case_is_identical_across_decks(self):
        for case_id in {item["case_id"] for item in self.world["items"]}:
            pair = [item for item in self.world["items"] if item["case_id"] == case_id]
            self.assertEqual(len(pair), 2)
            for key in ("domain", "question", "source", "answer", "expected_semantic"):
                self.assertEqual(pair[0][key], pair[1][key])
            self.assertNotEqual(pair[0]["expected"], pair[1]["expected"])

    def test_all_prompts_fit_under_ninety_words(self):
        self.assertTrue(all(item["prompt_words"] <= 90 for item in self.world["items"]))

    def test_builder_reproduces_frozen_world(self):
        self.assertEqual(BUILDER.build(), self.world)


if __name__ == "__main__":
    unittest.main()
