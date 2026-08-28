import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
RUNNER_PATH = ROOT / "experiments/E007-harness-mvp/src/run_nonce_word_gate.py"
SPEC = importlib.util.spec_from_file_location("run_nonce_word_gate", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class NonceWordRunnerTest(unittest.TestCase):
    def test_labels_are_fixed(self):
        self.assertEqual(RUNNER.LABELS, ("KSEL", "PTHY"))

    def test_locked_interpretations(self):
        base = {
            "semantic_correct": 10,
            "deck_correct": {"MAIN": 5, "MIRROR": 5},
            "minimum_class_correct_within_a_deck": 2,
            "label_choices": {"KSEL": 10, "PTHY": 10},
            "paired_label_flips": 0,
        }
        self.assertEqual(RUNNER.interpretation({**base, "label_choices": {"KSEL": 20, "PTHY": 0}}), "strong_KSEL_bias")
        self.assertEqual(RUNNER.interpretation({**base, "label_choices": {"KSEL": 0, "PTHY": 20}}), "strong_PTHY_bias")
        self.assertEqual(RUNNER.interpretation({**base, "paired_label_flips": 10}), "mapping_followed_but_semantics_failed")
        success = {**base, "semantic_correct": 18, "deck_correct": {"MAIN": 9, "MIRROR": 9}, "minimum_class_correct_within_a_deck": 4}
        self.assertEqual(RUNNER.interpretation(success), "semantic_success")


if __name__ == "__main__":
    unittest.main()
