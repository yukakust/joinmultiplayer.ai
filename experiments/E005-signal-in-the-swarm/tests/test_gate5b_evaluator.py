import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/evaluate_gate5b.py"
sys.path.insert(0, str(SOURCE.parent))
SPEC = importlib.util.spec_from_file_location("evaluate_gate5b", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Gate5BEvaluatorTests(unittest.TestCase):
    def test_score_requires_both_frozen_statements(self):
        row = {"expected_cause": "The cause is thermal rebound.", "expected_safety": "Keep the auxiliary vent closed."}
        self.assertFalse(MODULE.score_answer("The cause is thermal rebound.", row)["complete"])
        self.assertTrue(MODULE.score_answer("THE CAUSE IS THERMAL REBOUND; keep the auxiliary vent closed!", row)["complete"])

    def test_russian_normalization_handles_yo(self):
        self.assertEqual(MODULE.normalize("Всё — хорошо!"), "все хорошо")

    def test_frozen_conditions_are_complete(self):
        self.assertEqual(len(MODULE.CONDITIONS), 6)
        self.assertIn("correct_neural_pair", MODULE.CONDITIONS)
        self.assertIn("semantic_text_capsules", MODULE.CONDITIONS)

    def test_wrong_pair_rule_is_fixed_before_exam(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('number % 2 == 0', source)
        self.assertIn('"wrong_cause" if', source)
        self.assertIn('"wrong_safety"', source)


if __name__ == "__main__":
    unittest.main()
