from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "run_e006.py"
SPEC = importlib.util.spec_from_file_location("run_e006", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class CapsuleTests(unittest.TestCase):
    def setUp(self):
        self.document = {"id": "D1", "text": "A violet ring identifies an outer seal breach."}

    def test_accepts_exact_grounded_capsule(self):
        raw = json.dumps({"status": "found", "claim": "The seal is breached.", "source": "D1", "quote": "A violet ring identifies an outer seal breach.", "missing": "safe action"})
        result = MODULE.validate_capsule(raw, self.document)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["capsule"]["source"], "D1")

    def test_rejects_invented_quote(self):
        raw = json.dumps({"status": "found", "claim": "The seal is breached.", "source": "D1", "quote": "Invented evidence", "missing": None})
        result = MODULE.validate_capsule(raw, self.document)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "quote_not_exact")

    def test_rejects_wrong_source(self):
        raw = json.dumps({"status": "found", "claim": "The seal is breached.", "source": "D2", "quote": "A violet ring identifies an outer seal breach.", "missing": None})
        self.assertEqual(MODULE.validate_capsule(raw, self.document)["reason"], "wrong_source_id")

    def test_accepts_honest_not_found(self):
        raw = json.dumps({"status": "not_found", "claim": None, "source": None, "quote": None, "missing": "safe action"})
        result = MODULE.validate_capsule(raw, self.document)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["capsule"]["status"], "not_found")

    def test_rejects_non_json(self):
        self.assertEqual(MODULE.validate_capsule("I think it is broken", self.document)["reason"], "no_valid_json")


if __name__ == "__main__":
    unittest.main()
