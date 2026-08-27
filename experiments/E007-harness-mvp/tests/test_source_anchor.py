import importlib.util
import json
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src/verify_source_anchor.py"
SPEC = importlib.util.spec_from_file_location("verify_source_anchor", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SourceAnchorTests(unittest.TestCase):
    def test_frozen_cases_match_locked_protocol(self):
        protocol = json.loads(MODULE.PROTOCOL_PATH.read_text(encoding="utf-8"))
        _, cases = MODULE.frozen_world()
        self.assertEqual(
            [(item["id"], item["scenario"], item["expected"]) for item in cases],
            [(item["id"], item["scenario"], item["expected"]) for item in protocol["frozen_cases"]],
        )

    def test_second_run_is_identical(self):
        self.assertEqual(MODULE.run(), MODULE.run())

    def test_published_result_preserves_locked_gate(self):
        result_path = Path(__file__).parents[3] / "site/experiments/E007/source-anchor-result-v0.1.json"
        if not result_path.exists():
            self.skipTest("Gate 3C.6A has not run yet")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertEqual(result["summary"]["total"], 20)
        self.assertEqual(len(result["records"]), 20)


if __name__ == "__main__":
    unittest.main()
