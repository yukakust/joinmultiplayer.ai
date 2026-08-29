from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).parents[1] / "src/run_used_shelf_writer.py"
SPEC = importlib.util.spec_from_file_location("used_shelf_writer", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class UsedShelfWriterTest(unittest.TestCase):
    def test_frozen_population_contains_only_used(self):
        source = MODULE.read(MODULE.SOURCE_PATH)
        cases = MODULE.cases(source)
        self.assertEqual(len(cases), 30)
        self.assertEqual(sum(len(item["used"]) for item in cases), 60)
        self.assertTrue(all(len(item["used"]) == 2 for item in cases))

    def test_prompt_never_contains_other_shelves(self):
        protocol = MODULE.read(MODULE.PROTOCOL_PATH)
        case = MODULE.cases(MODULE.read(MODULE.SOURCE_PATH))[0]
        text = MODULE.prompt(protocol["writer"], case)
        self.assertIn("USED SHELF", text)
        self.assertNotIn("SAME_CASE", text)
        self.assertNotIn("OTHER", text)

    def test_parser_rejects_unknown_citation(self):
        valid = '{"answer":"Cause X. Do Y.","evidence_ids":["A","B"]}'
        self.assertEqual(MODULE.parse_answer(valid, {"A", "B"})[1], None)
        invalid = '{"answer":"Cause X.","evidence_ids":["C"]}'
        self.assertIsNotNone(MODULE.parse_answer(invalid, {"A", "B"})[1])


if __name__ == "__main__":
    unittest.main()
