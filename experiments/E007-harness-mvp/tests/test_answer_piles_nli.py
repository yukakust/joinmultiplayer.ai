import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
MODULE_PATH = Path(__file__).parents[1] / "src/run_answer_piles_nli.py"
SPEC = importlib.util.spec_from_file_location("run_answer_piles_nli", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AnswerPilesNliTests(unittest.TestCase):
    def test_relation_requires_two_way_entailment(self):
        self.assertEqual(MODULE.relation("entailment", "entailment"), "same_version")
        self.assertEqual(MODULE.relation("entailment", "neutral"), "different_or_related")
        self.assertEqual(MODULE.relation("contradiction", "neutral"), "opposing_versions")

    def test_pile_requires_agreement_with_every_member(self):
        answers = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
        relations = {
            ("A", "B"): "same_version",
            ("A", "C"): "same_version",
            ("B", "C"): "different_or_related",
        }
        self.assertEqual(MODULE.build_piles(answers, relations), [["A", "B"], ["C"]])

    def test_pairwise_metrics(self):
        answers = [
            {"id": "A", "gold_pile": "G1"},
            {"id": "B", "gold_pile": "G1"},
            {"id": "C", "gold_pile": "G2"},
        ]
        metrics = MODULE.pairwise_metrics(answers, [["A", "B"], ["C"]])
        self.assertEqual(metrics, {"tp": 1, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0})

    def test_frozen_world_matches_protocol(self):
        protocol = json.loads((ROOT / "site/experiments/E007/answer-piles-nli-protocol-v0.1.json").read_text())
        world = json.loads((ROOT / "site/experiments/E007/answer-piles-nli-world-v0.1.json").read_text())
        self.assertEqual(len(world["answers"]), protocol["frozen_method"]["answers"])
        self.assertEqual(len(world["answers"]) * (len(world["answers"]) - 1) // 2, protocol["frozen_method"]["unordered_pairs"])
        self.assertEqual(sum(len(pile["answer_ids"]) > 1 for pile in world["gold_piles"]), 6)

    def test_published_result_preserves_locked_failure(self):
        result = json.loads((ROOT / "site/experiments/E007/answer-piles-nli-result-v0.1.json").read_text())
        self.assertFalse(result["summary"]["passed_locked_development_gate"])
        self.assertEqual(result["summary"]["exact_paraphrase_piles"], 4)
        self.assertEqual(result["summary"]["paraphrase_piles_total"], 6)
        self.assertEqual(result["summary"]["forbidden_merges"], 0)
        self.assertEqual(result["summary"]["pairwise"]["f1"], 0.8)
        self.assertEqual(result["summary"]["lost_answers"], 0)


if __name__ == "__main__":
    unittest.main()
