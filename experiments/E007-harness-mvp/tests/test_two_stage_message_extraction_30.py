import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
MODULE_PATH = ROOT / "experiments/E007-harness-mvp/src/run_two_stage_message_extraction_30.py"
SPEC = importlib.util.spec_from_file_location("two_stage_message_extraction_30", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TwoStageThirtyCaseTest(unittest.TestCase):
    def test_frozen_mix_and_missing_sources(self):
        world = json.loads((ROOT / "site/experiments/E007/world-v0.1.json").read_text())
        cases = MODULE.build_cases(world)
        self.assertEqual(len(cases), 30)
        self.assertEqual(sum(row["kind"] == "answerable" for row in cases), 20)
        self.assertEqual(sum(row["kind"] == "no_answer_in_packet" for row in cases), 10)
        for row in cases[20:]:
            candidate_ids = {item["real_id"] for item in row["messages"]}
            self.assertTrue(candidate_ids.isdisjoint(row["removed_sources"]))


if __name__ == "__main__":
    unittest.main()
