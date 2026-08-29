from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).parents[1] / "src/run_qwen17b_relevance.py"
SPEC = importlib.util.spec_from_file_location("qwen17b_relevance", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Qwen17BRelevanceTest(unittest.TestCase):
    def test_frozen_population_is_60_required_and_420_unrelated(self):
        pairs = MODULE.frozen_pairs(MODULE.read(MODULE.SOURCE_PATH))
        self.assertEqual(len(pairs), 480)
        self.assertEqual(sum(item["gold"] == "USEFUL" for item in pairs), 60)
        self.assertEqual(sum(item["gold"] == "NOT_USEFUL" for item in pairs), 420)

    def test_prompt_contains_no_gold_label_or_expected_answer(self):
        protocol = MODULE.read(MODULE.PROTOCOL_PATH)
        prompt = MODULE.make_prompt(protocol["prompt"]["template"], "Where is Kest-11?", "A record about Kest-11.")
        self.assertIn("Where is Kest-11?", prompt)
        self.assertIn("A record about Kest-11.", prompt)
        self.assertNotIn("gold", prompt.lower())

    def test_parser_is_strict(self):
        self.assertEqual(MODULE.parse_decision("USEFUL"), "USEFUL")
        self.assertEqual(MODULE.parse_decision("NOT_USEFUL."), "NOT_USEFUL")
        self.assertEqual(MODULE.parse_decision("Maybe useful"), "UNPARSEABLE")


if __name__ == "__main__":
    unittest.main()
