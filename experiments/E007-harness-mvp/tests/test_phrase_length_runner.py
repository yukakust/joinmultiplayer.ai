import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
RUNNER_PATH = ROOT / "experiments/E007-harness-mvp/src/run_phrase_length_gate.py"
SPEC = importlib.util.spec_from_file_location("run_phrase_length_gate", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class PhraseLengthRunnerTest(unittest.TestCase):
    def test_locked_gate_requires_every_condition(self):
        passing = {
            "semantic_correct": 18,
            "order_correct": {"POSITIVE_FIRST": 9, "NEGATIVE_FIRST": 9},
            "minimum_class_correct_within_an_order": 4,
            "order_stable_pairs": 9,
        }
        self.assertTrue(RUNNER.family_passes(passing))
        for field in ("semantic_correct", "minimum_class_correct_within_an_order", "order_stable_pairs"):
            failing = dict(passing)
            failing[field] -= 1
            self.assertFalse(RUNNER.family_passes(failing))
        failing = dict(passing)
        failing["order_correct"] = {"POSITIVE_FIRST": 9, "NEGATIVE_FIRST": 8}
        self.assertFalse(RUNNER.family_passes(failing))


if __name__ == "__main__":
    unittest.main()
