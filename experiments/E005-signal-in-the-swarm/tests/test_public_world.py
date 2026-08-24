from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORLD_PATH = ROOT.parent / "site" / "experiments" / "E005" / "world-public-v0.1.json"


class PublicWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        cls.documents = {document["id"]: document for document in cls.world["documents"]}

    def test_public_fixture_is_not_a_result_or_locked_set(self) -> None:
        self.assertEqual(self.world["claim_status"], "not_a_result")
        self.assertFalse(self.world["locked_boundary"]["contains_locked_tasks"])
        self.assertFalse(self.world["locked_boundary"]["contains_model_outputs"])

    def test_entities_are_fictional_and_all_text_is_bilingual(self) -> None:
        self.assertTrue(self.world["world"]["fictional"])
        for document in self.world["documents"]:
            self.assertTrue(document["content"]["en"])
            self.assertTrue(document["content"]["ru"])
        for task in self.world["tasks"]:
            self.assertTrue(task["question"]["en"])
            self.assertTrue(task["question"]["ru"])

    def test_every_evidence_reference_and_supporter_exists(self) -> None:
        pockets = {pocket["id"] for pocket in self.world["pockets"]}
        for task in self.world["tasks"]:
            self.assertTrue(set(task["candidate_pockets"]).issubset(pockets))
            for claim in task["claims"]:
                self.assertTrue(set(claim["supporters"]).issubset(pockets))
                for evidence_id in claim["evidence"]:
                    self.assertIn(evidence_id, self.documents)
                    self.assertIn(self.documents[evidence_id]["owner"], claim["supporters"])

    def test_lineage_counts_do_not_equal_raw_vote_counts_in_traps(self) -> None:
        for task_id in ("PUBLIC-01", "PUBLIC-04"):
            task = next(task for task in self.world["tasks"] if task["id"] == task_id)
            stale = next(claim for claim in task["claims"] if claim["verdict"] == "defeated_stale_majority")
            self.assertGreater(len(stale["supporters"]), len(set(stale["lineages"])))
            evidence_lineages = {self.documents[item]["lineage"] for item in stale["evidence"]}
            self.assertEqual(evidence_lineages, set(stale["lineages"]))

    def test_every_expected_claim_exists_and_minorities_are_preregistered(self) -> None:
        for task in self.world["tasks"]:
            claim_ids = {claim["id"] for claim in task["claims"]}
            self.assertIn(task["expected"]["main_claim"], claim_ids)
            alternative = task["expected"]["alternative_claim"]
            self.assertEqual(task["expected"]["report_alternative"], alternative is not None)
            if alternative is not None:
                self.assertIn(alternative, claim_ids)

    def test_required_task_families_are_present_once(self) -> None:
        counts = Counter(task["family"] for task in self.world["tasks"])
        expected = {
            "copied_false_majority",
            "independent_true_consensus",
            "unsupported_false_minority",
            "lexical_stale_trap",
            "complementary_composition",
            "insufficient_evidence",
        }
        self.assertEqual(set(counts), expected)
        self.assertTrue(all(count == 1 for count in counts.values()))


if __name__ == "__main__":
    unittest.main()
