import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
RUNNER_PATH = ROOT / "experiments/E007-harness-mvp/src/run_numeric_letter_gate.py"
SPEC = importlib.util.spec_from_file_location("run_numeric_letter_gate", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class NumericLetterRunnerTest(unittest.TestCase):
    def test_actions_are_one_then_A(self):
        self.assertEqual(RUNNER.ACTIONS, ("1", "A"))

    def test_locked_interpretations(self):
        base = {
            "semantic_correct": 10,
            "deck_correct": {"X": 5, "Y": 5},
            "minimum_class_correct_within_a_deck": 2,
            "label_choices": {"1": 10, "A": 10},
            "paired_label_flips": 0,
        }
        self.assertEqual(RUNNER.interpretation({**base, "label_choices": {"1": 20, "A": 0}}), "strong_1_symbol_bias")
        self.assertEqual(RUNNER.interpretation({**base, "label_choices": {"1": 0, "A": 20}}), "strong_A_symbol_bias")
        self.assertEqual(RUNNER.interpretation({**base, "paired_label_flips": 10}), "mapping_followed_but_semantics_failed")
        success = {**base, "semantic_correct": 18, "deck_correct": {"X": 9, "Y": 9}, "minimum_class_correct_within_a_deck": 4}
        self.assertEqual(RUNNER.interpretation(success), "semantic_success")


if __name__ == "__main__":
    unittest.main()
