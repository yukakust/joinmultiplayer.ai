import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "build_evidence_ledger.py"
SPEC = importlib.util.spec_from_file_location("build_evidence_ledger", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EvidenceLedgerTests(unittest.TestCase):
    def test_frozen_gate_builds_without_model_calls(self):
        result = MODULE.build()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["summary"]["new_model_calls"], 0)
        self.assertEqual(result["summary"]["ledger_records_preserved"], 480)
        self.assertTrue(all(item["preserved"] for item in result["ledger"]))

    def test_views_keep_required_alternatives_and_lineage(self):
        result = MODULE.build()
        self.assertEqual(result["summary"]["required_pieces_in_used"], 60)
        self.assertEqual(result["summary"]["same_case_alternatives_preserved"], 24)
        self.assertEqual(result["summary"]["other_records_preserved_hidden"], 396)
        self.assertEqual(result["summary"]["dependent_copy_records"], 18)
        self.assertEqual(result["summary"]["dependent_copy_visible_lineages"], 6)

    def test_every_record_has_exactly_one_primary_shelf(self):
        result = MODULE.build()
        self.assertEqual({item["shelf"] for item in result["ledger"]}, {"USED", "SAME_CASE", "OTHER"})
        ids = [item["ledger_id"] for item in result["ledger"]]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
