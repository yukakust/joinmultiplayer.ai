from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/eval_gate5a.py"


class Gate5AEvalRunnerTests(unittest.TestCase):
    def test_runner_never_trains_or_changes_exam(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("optimizer", text.lower())
        self.assertNotIn("backward(", text)
        self.assertIn('"training_performed": False', text)

    def test_all_falsifying_controls_are_present(self):
        text = SOURCE.read_text(encoding="utf-8")
        for condition in ("frozen_base_direct", "cause_i_direct", "safety_i_direct", "frozen_base_pair", "wrong_cause_pair", "wrong_safety_pair", "correct_pair", "oracle_pair"):
            self.assertIn(f'"{condition}"', text)

    def test_pair_success_needs_both_exact_capsules(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('cause["cause"] == expected_cause', text)
        self.assertIn('safety["restriction"] == expected_safety', text)
        self.assertIn("remove_cause_costs_at_least_10", text)
        self.assertIn("remove_safety_costs_at_least_10", text)


if __name__ == "__main__":
    unittest.main()
