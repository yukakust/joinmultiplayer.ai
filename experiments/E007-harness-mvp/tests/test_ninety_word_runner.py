import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
RUNNER_PATH = ROOT / "experiments/E007-harness-mvp/src/run_ninety_word_gate.py"
SPEC = importlib.util.spec_from_file_location("run_ninety_word_gate", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class NinetyWordRunnerTest(unittest.TestCase):
    def test_actions_are_exactly_the_two_agreed_choices(self):
        self.assertEqual(RUNNER.ACTIONS, ("approve", "reject"))

    def test_paths_point_to_frozen_inputs(self):
        protocol = json.loads(RUNNER.PROTOCOL_PATH.read_text())
        world = json.loads(RUNNER.WORLD_PATH.read_text())
        self.assertEqual(protocol["status"], "locked_before_inference")
        self.assertEqual(world["status"], "frozen_before_inference")
        self.assertEqual(protocol["locked_success"]["total_correct_min"], 10)


if __name__ == "__main__":
    unittest.main()
