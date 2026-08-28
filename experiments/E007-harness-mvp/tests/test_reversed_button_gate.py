import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
BUILDER_PATH = ROOT / "experiments/E007-harness-mvp/src/build_reversed_button_gate.py"
SPEC = importlib.util.spec_from_file_location("build_reversed_button_gate", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class ReversedButtonWorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = json.loads((ROOT / "site/experiments/E007/ninety-word-world-v0.1.json").read_text())
        cls.new = json.loads((ROOT / "site/experiments/E007/ninety-word-reversed-world-v0.1.json").read_text())

    def test_same_ten_cases_and_truth(self):
        for old, new in zip(self.old["cases"], self.new["cases"]):
            for key in ("id", "domain", "expected", "question", "source", "answer"):
                self.assertEqual(old[key], new[key])

    def test_only_instruction_order_changed(self):
        for case in self.new["cases"]:
            self.assertIn("Choose: reject or approve.", case["prompt"])
            self.assertLess(case["prompt"].index("reject ="), case["prompt"].index("approve ="))
            self.assertLessEqual(case["prompt_words"], 90)

    def test_builder_reproduces_frozen_world(self):
        self.assertEqual(BUILDER.build(), self.new)


if __name__ == "__main__":
    unittest.main()
