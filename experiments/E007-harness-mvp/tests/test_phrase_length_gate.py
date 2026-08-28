import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
BUILDER_PATH = ROOT / "experiments/E007-harness-mvp/src/build_phrase_length_gate.py"
SPEC = importlib.util.spec_from_file_location("build_phrase_length_gate", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class PhraseLengthWorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = json.loads((ROOT / "site/experiments/E007/phrase-length-world-v0.1.json").read_text())

    def test_has_five_families_two_orders_and_ten_cases(self):
        self.assertEqual(len(self.world["families"]), 5)
        self.assertEqual(len(self.world["orders"]), 2)
        self.assertEqual(len(self.world["items"]), 100)

    def test_natural_pairs_match_declared_word_length(self):
        for family in self.world["families"]:
            if family["id"].startswith("W"):
                words = int(family["id"][1:])
                self.assertEqual(len(family["positive"].split()), words)
                self.assertEqual(len(family["negative"].split()), words)

    def test_each_order_keeps_case_content_and_truth(self):
        for family in self.world["families"]:
            for case_id in {item["case_id"] for item in self.world["items"]}:
                pair = [item for item in self.world["items"] if item["family_id"] == family["id"] and item["case_id"] == case_id]
                self.assertEqual(len(pair), 2)
                for key in ("question", "source", "answer", "expected_semantic", "expected"):
                    self.assertEqual(pair[0][key], pair[1][key])

    def test_complete_prompts_remain_compact(self):
        self.assertLessEqual(max(item["prompt_words"] for item in self.world["items"]), 100)

    def test_builder_reproduces_frozen_world(self):
        self.assertEqual(BUILDER.build(), self.world)


if __name__ == "__main__":
    unittest.main()
