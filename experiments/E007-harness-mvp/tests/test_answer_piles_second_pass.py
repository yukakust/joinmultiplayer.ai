import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
MODULE_PATH = Path(__file__).parents[1] / "src/run_answer_piles_second_pass.py"
SPEC = importlib.util.spec_from_file_location("run_answer_piles_second_pass", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AnswerPilesSecondPassTests(unittest.TestCase):
    def test_premise_contains_both_complete_piles(self):
        premise = MODULE.make_premise(
            {"answers": ["First.", "Second."]},
            {"answers": ["Third."]},
        )
        self.assertEqual(premise, "PILE A:\n- First.\n- Second.\n\nPILE B:\n- Third.")

    def test_components_follow_merge_edges(self):
        groups = MODULE.components(["P01", "P02", "P03"], {("P01", "P02")})
        self.assertEqual(groups, [["P01", "P02"], ["P03"]])

    def test_frozen_world_matches_protocol(self):
        protocol = json.loads((ROOT / "site/experiments/E007/answer-piles-second-pass-protocol-v0.1.json").read_text())
        world = json.loads((ROOT / "site/experiments/E007/answer-piles-second-pass-world-v0.1.json").read_text())
        self.assertEqual(len(world["piles"]), protocol["frozen_input"]["piles"])
        self.assertEqual(len(world["piles"]) * (len(world["piles"]) - 1) // 2, protocol["frozen_input"]["unordered_pile_pairs"])
        self.assertEqual(len(world["expected_merges"]), 2)


if __name__ == "__main__":
    unittest.main()
