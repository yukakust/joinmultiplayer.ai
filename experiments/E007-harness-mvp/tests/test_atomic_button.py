import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
BUILDER_PATH = ROOT / "experiments/E007-harness-mvp/src/build_atomic_button_world.py"
SPEC = importlib.util.spec_from_file_location("build_atomic_button_world", BUILDER_PATH)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class AtomicButtonWorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads((ROOT / "site/experiments/E007/atomic-button-protocol-v0.1.json").read_text())
        cls.world = json.loads((ROOT / "site/experiments/E007/atomic-button-world-v0.1.json").read_text())

    def test_inputs_are_frozen(self):
        self.assertEqual(self.protocol["status"], "locked_before_inference")
        self.assertEqual(self.world["status"], "frozen_before_inference")

    def test_exactly_ten_unique_questions(self):
        cases = self.world["cases"]
        self.assertEqual(len(cases), 10)
        self.assertEqual(len({case["question"] for case in cases}), 10)
        self.assertEqual(len({case["domain"] for case in cases}), 10)

    def test_three_useful_and_seven_traps(self):
        counts = {name: sum(case["expected"]["final"] == name for case in self.world["cases"])
                  for name in ("use", "do_not_use")}
        self.assertEqual(counts, {"use": 3, "do_not_use": 7})

    def test_each_single_failure_is_visible(self):
        combinations = {case["combination"] for case in self.world["cases"]}
        self.assertTrue({"011", "101", "110"}.issubset(combinations))

    def test_builder_reproduces_world(self):
        self.assertEqual(BUILDER.build(), self.world)


if __name__ == "__main__":
    unittest.main()
