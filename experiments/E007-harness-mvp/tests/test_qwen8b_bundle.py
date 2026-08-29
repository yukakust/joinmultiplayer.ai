from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).parents[1] / "src/run_qwen8b_bundle.py"
SPEC = importlib.util.spec_from_file_location("qwen8b_bundle", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Qwen8BBundleTest(unittest.TestCase):
    def test_frozen_population(self):
        cases = MODULE.bundles(MODULE.read(MODULE.SOURCE_PATH))
        self.assertEqual(len(cases), 30)
        self.assertEqual(sum(len(item["offers"]) for item in cases), 480)
        self.assertEqual(sum(len(item["gold"]["core"]) for item in cases), 30)
        self.assertEqual(sum(len(item["gold"]["action"]) for item in cases), 30)
        self.assertEqual(sum(len(item["gold"]["alternatives"]) for item in cases), 24)
        self.assertEqual(sum(len(item["gold"]["irrelevant"]) for item in cases), 396)

    def test_condition_mismatch_lookalike_is_related(self):
        case = next(item for item in MODULE.bundles(MODULE.read(MODULE.SOURCE_PATH)) if item["id"] == "E7-Q07")
        self.assertEqual(case["gold"]["alternatives"], ["E7-X01-LOOKALIKE"])

    def test_dependent_copies_are_related(self):
        case = next(item for item in MODULE.bundles(MODULE.read(MODULE.SOURCE_PATH)) if item["id"] == "E7-Q13")
        self.assertEqual(len(case["gold"]["alternatives"]), 3)

    def test_selector_parser_is_strict(self):
        offered = {"A", "B"}
        self.assertEqual(MODULE.parse_selector('{"keep":["A"]}', offered), (["A"], None))
        self.assertIsNotNone(MODULE.parse_selector('{"keep":["C"]}', offered)[1])
        self.assertIsNotNone(MODULE.parse_selector('answer: A', offered)[1])

    def test_answer_parser_rejects_unselected_citation(self):
        raw = '{"best_supported":"x","best_evidence_ids":["B"],"alternative_view":null,"alternative_evidence_ids":[],"action_or_next_step":null,"action_evidence_ids":[],"uncertainty":null}'
        self.assertIsNotNone(MODULE.parse_answer(raw, {"A"})[1])


if __name__ == "__main__":
    unittest.main()
