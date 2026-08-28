import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
RUNNER_PATH = ROOT / "experiments/E007-harness-mvp/src/run_reversed_button_gate.py"
SPEC = importlib.util.spec_from_file_location("run_reversed_button_gate", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class ReversedButtonRunnerTest(unittest.TestCase):
    def test_reject_is_first_everywhere(self):
        self.assertEqual(RUNNER.ACTIONS, ("reject", "approve"))
        self.assertLess(RUNNER.SYSTEM.index("Choose reject"), RUNNER.SYSTEM.index("Choose approve"))

    def test_locked_interpretations(self):
        common = {"total_correct": 5, "approve_correct": 0, "reject_correct": 5}
        self.assertEqual(RUNNER.interpretation({**common, "switched_approve_to_reject": 10, "approve_choices": 0}), "strong_order_effect")
        self.assertEqual(RUNNER.interpretation({**common, "switched_approve_to_reject": 0, "approve_choices": 10}), "strong_approve_label_bias")
        self.assertEqual(RUNNER.interpretation({"total_correct": 9, "approve_correct": 4, "reject_correct": 5, "switched_approve_to_reject": 5, "approve_choices": 4}), "semantic_success")


if __name__ == "__main__":
    unittest.main()
