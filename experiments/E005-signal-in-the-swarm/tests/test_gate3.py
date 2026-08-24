from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
WORLD_PATH = EXPERIMENT.parents[1] / "site" / "experiments" / "E005" / "world-public-v0.1.json"
sys.path.insert(0, str(EXPERIMENT / "src"))
SPEC = importlib.util.spec_from_file_location("e005_gate3", EXPERIMENT / "src" / "run_gate3.py")
GATE3 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(GATE3)


class Gate3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.world = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        cls.tasks = {task["id"]: task for task in cls.world["tasks"]}

    def test_lexical_ranking_is_deterministic_and_finds_exact_stale_aster_record(self) -> None:
        task = self.tasks["PUBLIC-04"]
        first = GATE3.lexical_rank(task["question"]["en"], self.world["documents"], "en")
        second = GATE3.lexical_rank(task["question"]["en"], self.world["documents"], "en")
        self.assertEqual(first, second)
        self.assertEqual(first[0][0], "DOC-A9-ARCHIVE")

    def test_majority_preserves_copied_kest_lineage_as_the_naive_winner(self) -> None:
        self.assertEqual(
            GATE3.raw_majority_documents(self.tasks["PUBLIC-01"]),
            ["DOC-K7-OLD", "DOC-K7-COPY-A", "DOC-K7-COPY-B"],
        )

    def test_evidence_graph_selects_current_kest_records(self) -> None:
        self.assertEqual(
            GATE3.evidence_graph_documents(self.tasks["PUBLIC-01"], self.world),
            ["DOC-K7-CURRENT", "DOC-K7-REGISTER"],
        )

    def test_composed_task_includes_diagnosis_and_remedy(self) -> None:
        expected = ["DOC-M3-DIAG", "DOC-M3-LOG", "DOC-N11-SAFETY"]
        self.assertEqual(GATE3.evidence_graph_documents(self.tasks["PUBLIC-05"], self.world), expected)
        self.assertEqual(GATE3.oracle_documents(self.tasks["PUBLIC-05"]), expected)

    def test_no_method_can_request_private_or_unknown_records(self) -> None:
        public_ids = {document["id"] for document in self.world["documents"]}
        for task in self.world["tasks"]:
            for ids in (
                GATE3.raw_majority_documents(task),
                GATE3.evidence_graph_documents(task, self.world),
                GATE3.oracle_documents(task),
            ):
                self.assertLessEqual(set(ids), public_ids)

    def test_gate3_contains_no_training_entrypoint(self) -> None:
        source = (EXPERIMENT / "src" / "run_gate3.py").read_text(encoding="utf-8")
        self.assertNotIn("optimizer", source.casefold())
        self.assertNotIn("backward(", source.casefold())
        self.assertNotIn("peft", source.casefold())


if __name__ == "__main__":
    unittest.main()
