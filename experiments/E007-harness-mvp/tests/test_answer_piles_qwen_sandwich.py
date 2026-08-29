import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
MODULE_PATH = Path(__file__).parents[1] / "src/run_answer_piles_qwen_sandwich.py"
SPEC = importlib.util.spec_from_file_location("run_answer_piles_qwen_sandwich", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AnswerPilesQwenSandwichTests(unittest.TestCase):
    def test_prompt_contains_every_statement_once(self):
        prompt = MODULE.make_user_prompt({"answers": ["First.", "Second."]})
        self.assertEqual(prompt, "STATEMENTS IN ONE PILE:\n- First.\n- Second.\n\nONE ATOMIC CLAIM:")

    def test_components_follow_only_predicted_edges(self):
        self.assertEqual(
            MODULE.components(["P01", "P02", "P03"], {("P01", "P03")}),
            [["P01", "P03"], ["P02"]],
        )

    def test_protocol_pins_unchanged_source(self):
        protocol = json.loads((ROOT / "site/experiments/E007/answer-piles-qwen-sandwich-protocol-v0.1.json").read_text())
        source = ROOT / "site/experiments/E007/answer-piles-second-pass-world-v0.1.json"
        self.assertEqual(MODULE.digest(source), protocol["source"]["sha256"])
        self.assertEqual(protocol["source"]["expected_merges"], [["P03", "P04"], ["P06", "P07"]])


if __name__ == "__main__":
    unittest.main()
