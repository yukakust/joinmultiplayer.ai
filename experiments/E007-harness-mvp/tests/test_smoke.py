import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("e007_smoke", ROOT / "experiments/E007-harness-mvp/src/run_smoke.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)
WORLD = json.loads((ROOT / "site/experiments/E007/world-v0.1.json").read_text())


class SmokePureTests(unittest.TestCase):
    def setUp(self):
        self.tasks = {task["id"]: task for task in WORLD["tasks"]}

    def test_locked_tasks_cover_three_different_failures(self):
        protocol = json.loads((ROOT / "site/experiments/E007/smoke-protocol-v0.1.json").read_text())
        self.assertEqual(["E7-Q01", "E7-Q13", "E7-Q19"], protocol["selected_tasks"])
        self.assertEqual(3, len({self.tasks[task]["family"] for task in protocol["selected_tasks"]}))
        self.assertFalse(protocol["training"])

    def test_router_uses_no_private_text_and_finds_required_holders(self):
        for task_id in ("E7-Q01", "E7-Q13", "E7-Q19"):
            task = self.tasks[task_id]
            routed = MODULE.route(task, WORLD["pockets"], 8)
            routed_ids = {item["pocket"]["id"] for item in routed}
            self.assertTrue(set(task["required_pockets"]) <= routed_ids)
            selected = MODULE.selected_documents(task, routed, WORLD["documents"])
            selected_ids = {document["id"] for document in selected}
            self.assertTrue(set(task["required_sources"]) <= selected_ids)

    def test_local_rag_is_owner_scoped(self):
        task = self.tasks["E7-Q01"]
        for pocket_id in task["required_pockets"]:
            rows = MODULE.local_rag(task, pocket_id, WORLD["documents"], 1)
            self.assertEqual(1, len(rows))
            self.assertEqual(pocket_id, rows[0]["owner"])

    def test_security_removes_canary_before_harness(self):
        task = self.tasks["E7-Q19"]
        canary = task["forbidden_canaries"][0]
        document = next(document for document in WORLD["documents"] if document["id"] == task["required_sources"][0])
        safe, trace = MODULE.safe_document(document)
        self.assertIn(canary, document["text"])
        self.assertNotIn(canary, safe)
        self.assertTrue(trace["redacted"])

    def test_lineage_dedup_counts_copies_once(self):
        capsules = [
            {"source": f"S{index}", "lineage": "ONE", "shelf": "cause", "validation": {"accepted": True}}
            for index in range(3)
        ]
        board = MODULE.build_board(capsules)
        self.assertEqual(1, len(board["unique_capsules"]))
        self.assertEqual(2, len(board["deduplicated"]))

    def test_exact_navigation_is_explicitly_not_semantic(self):
        value = MODULE.exact_navigation("unrelated answer", self.tasks["E7-Q01"])
        self.assertEqual("navigation_only_not_semantic_score", value["warning"])


if __name__ == "__main__":
    unittest.main()
