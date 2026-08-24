from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "experiments/E005-signal-in-the-swarm/src/review_gate4c.py"
PUBLIC = ROOT / "site/experiments/E005/gate-4c-results-v0.1.json"
SPEC = importlib.util.spec_from_file_location("review_gate4c", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name] = MODULE; SPEC.loader.exec_module(MODULE)


class Gate4CResultTests(unittest.TestCase):
    def test_all_raw_answers_are_preserved_and_reviewed(self):
        payload = MODULE.build()
        self.assertEqual(json.loads(PUBLIC.read_text(encoding="utf-8")), payload)
        self.assertEqual(len(payload["rows"]), 48)
        for row in payload["rows"]:
            self.assertEqual(len(row["conditions"]), 4)
            self.assertTrue(all(answer["output"] and answer["review"] in {"correct", "wrong"} for answer in row["conditions"].values()))

    def test_mixed_result_is_not_called_a_pass(self):
        payload = MODULE.build()
        self.assertFalse(payload["passed"])
        self.assertEqual(payload["summary"]["source_work"]["matching_dora"]["correct"], 6)
        self.assertEqual(payload["summary"]["safe_action"]["matching_dora"]["correct"], 23)
        self.assertIn("owner_pending", payload["status"])


if __name__ == "__main__":
    unittest.main()
