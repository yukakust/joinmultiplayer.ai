import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src/run_knowledge_chain.py"
SPEC = importlib.util.spec_from_file_location("run_knowledge_chain", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class KnowledgeChainTests(unittest.TestCase):
    def test_frozen_cases_match_locked_protocol(self):
        protocol = json.loads(MODULE.PROTOCOL_PATH.read_text(encoding="utf-8"))
        world = json.loads(MODULE.WORLD_PATH.read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in world["cases"]], protocol["frozen_case_ids"])

    def test_locked_run_passes_all_gates(self):
        result = MODULE.run()
        self.assertTrue(result["passed_locked_gate"])
        self.assertEqual(result["summary"]["case_decisions_correct"], 10)
        self.assertEqual(result["summary"]["transport_roundtrips_exact"], 10)

    def test_run_is_deterministic(self):
        self.assertEqual(MODULE.run(), MODULE.run())

    def test_order_does_not_choose_the_head(self):
        world = json.loads(MODULE.WORLD_PATH.read_text(encoding="utf-8"))
        case = next(item for item in world["cases"] if item["id"] == "KC06")
        self.assertEqual(MODULE.inspect_chain(case["revisions"])["current_revision_ids"], ["K06-3"])

    def test_fork_is_not_independent_consensus(self):
        world = json.loads(MODULE.WORLD_PATH.read_text(encoding="utf-8"))
        case = next(item for item in world["cases"] if item["id"] == "KC09")
        self.assertEqual(MODULE.inspect_chain(case["revisions"])["decision"], "forked")

    def test_two_lineages_remain_two_current_opinions(self):
        world = json.loads(MODULE.WORLD_PATH.read_text(encoding="utf-8"))
        case = next(item for item in world["cases"] if item["id"] == "KC10")
        actual = MODULE.inspect_chain(case["revisions"])
        self.assertEqual(actual["decision"], "ready_multi")
        self.assertEqual(actual["current_revision_ids"], ["K10-A1", "K10-B1"])

    def test_changed_parent_is_rejected(self):
        world = json.loads(MODULE.WORLD_PATH.read_text(encoding="utf-8"))
        case = deepcopy(next(item for item in world["cases"] if item["id"] == "KC03"))
        case["revisions"][1]["previous_revision_id"] = "DOES-NOT-EXIST"
        self.assertEqual(MODULE.inspect_chain(case["revisions"])["decision"], "incomplete")


if __name__ == "__main__":
    unittest.main()
