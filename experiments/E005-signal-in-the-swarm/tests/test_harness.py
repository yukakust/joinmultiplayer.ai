from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
WORLD_PATH = EXPERIMENT.parents[1] / "site" / "experiments" / "E005" / "world-public-v0.1.json"
SPEC = importlib.util.spec_from_file_location("e005_harness", EXPERIMENT / "src" / "harness.py")
HARNESS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HARNESS)


class HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        cls.result = HARNESS.run(cls.world)
        cls.rows = {row["task_id"]: row for row in cls.result["rows"]}

    def test_evidence_graph_and_minority_policy_match_all_public_expectations(self) -> None:
        self.assertEqual(self.result["status"], "passed")
        self.assertEqual(self.result["evidence_graph_accuracy"], 1.0)
        self.assertEqual(self.result["minority_policy_accuracy"], 1.0)

    def test_raw_majority_fails_at_least_one_copied_or_stale_trap(self) -> None:
        self.assertLess(self.result["raw_majority_accuracy"], 1.0)
        self.assertFalse(self.rows["PUBLIC-01"]["raw_majority_correct"])

    def test_three_copies_of_k7_count_as_one_lineage(self) -> None:
        stale = next(
            claim for claim in self.rows["PUBLIC-01"]["claims"]
            if claim["claim_id"] == "restart_kest_7"
        )
        self.assertEqual(stale["raw_supporters"], 3)
        self.assertEqual(stale["independent_lineages"], 1)

    def test_credible_defeated_alternatives_are_reported(self) -> None:
        self.assertEqual(self.rows["PUBLIC-01"]["reported_alternatives"], ["restart_kest_7"])
        self.assertEqual(self.rows["PUBLIC-04"]["reported_alternatives"], ["open_aster_9_aux_vent"])

    def test_unsupported_rumours_are_not_reported_for_false_balance(self) -> None:
        self.assertEqual(self.rows["PUBLIC-03"]["reported_alternatives"], [])
        self.assertEqual(self.rows["PUBLIC-06"]["reported_alternatives"], [])

    def test_composed_answer_requires_diagnostic_context(self) -> None:
        row = self.rows["PUBLIC-05"]
        self.assertTrue(row["dependencies_met"])
        selected = next(claim for claim in row["claims"] if claim["claim_id"] == row["selected_main_claim"])
        self.assertEqual(selected["depends_on"], ["mira_3_phase_inversion"])


if __name__ == "__main__":
    unittest.main()
