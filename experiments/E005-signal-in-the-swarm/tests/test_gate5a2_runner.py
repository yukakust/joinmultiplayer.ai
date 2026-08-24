from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/eval_gate5a2.py"


class Gate5A2RunnerTests(unittest.TestCase):
    def test_source_model_is_frozen_and_never_trains(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("optimizer", text.lower())
        self.assertNotIn("backward(", text)
        self.assertIn('"training_performed": False', text)

    def test_missing_capsules_and_question_only_are_real_controls(self):
        text = SOURCE.read_text(encoding="utf-8")
        for condition in ("question_alone", "actual_pair", "cause_only", "safety_only", "oracle_pair"):
            self.assertIn(f'"{condition}"', text)
        self.assertIn("MISSING", text)

    def test_natural_answer_requires_both_meanings_and_no_json(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('"complete": cause_kept and safety_kept', text)
        self.assertIn('"natural_no_json": natural_no_json', text)
        self.assertIn("actual_pair_natural_no_json_at_least_20", text)


if __name__ == "__main__":
    unittest.main()
