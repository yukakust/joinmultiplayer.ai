import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
RUNNER_PATH = ROOT / "experiments/E007-harness-mvp/src/run_button_sanity.py"
SPEC = importlib.util.spec_from_file_location("run_button_sanity", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


class ButtonSanityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = json.loads((ROOT / "site/experiments/E007/button-sanity-world-v0.1.json").read_text())

    def test_exactly_one_accept_and_one_reject(self):
        self.assertEqual([case["expected"] for case in self.world["cases"]], ["accept", "reject"])

    def test_only_colour_word_changes(self):
        first, second = self.world["cases"]
        self.assertEqual(first["second_text"], second["second_text"])
        self.assertEqual(first["first_text"].replace("red", "blue"), second["first_text"])

    def test_prompt_is_the_same_shape(self):
        prompts = [RUNNER.prompt_for(case) for case in self.world["cases"]]
        self.assertIn("FIRST TEXT", prompts[0])
        self.assertIn("SECOND TEXT", prompts[0])
        self.assertEqual(prompts[0].replace("red", "blue", 1), prompts[1])

    def test_result_if_published(self):
        path = ROOT / "site/experiments/E007/button-sanity-result-v0.1.json"
        if not path.exists():
            self.skipTest("result not published yet")
        result = json.loads(path.read_text())
        self.assertEqual(len(result["records"]), 2)


if __name__ == "__main__":
    unittest.main()
