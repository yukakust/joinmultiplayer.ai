from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT / "src"))
SPEC = importlib.util.spec_from_file_location("e005_gate4_full", EXPERIMENT / "src/eval_gate4_full.py")
FULL = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(FULL)


class Gate4FullEvalTests(unittest.TestCase):
    def test_exact_match_is_conservative(self) -> None:
        target = "Do not open the vent. Ask for pressure."
        self.assertTrue(FULL.exact_target_match(target, target))
        self.assertTrue(FULL.exact_target_match(target, target + " This is safe."))
        self.assertFalse(FULL.exact_target_match(target, "The vent should not be opened."))
        self.assertFalse(FULL.exact_target_match(target, "Question: do not open the vent?"))

    def test_all_four_conditions_are_explicit(self) -> None:
        self.assertEqual(FULL.METHODS, ("base", "personal_dora", "wrong_specialist", "shuffled_lessons"))
        source = (EXPERIMENT / "src/eval_gate4_full.py").read_text(encoding="utf-8")
        self.assertIn("model.disable_adapter()", source)
        self.assertIn('model.set_adapter(method)', source)
        self.assertIn('row["split"] == "held_out"', source)

    def test_duplicate_questions_do_not_count_as_new_evidence(self) -> None:
        rows = [
            {"id": "one", "input": "same"},
            {"id": "two", "input": "different"},
            {"id": "three", "input": "same"},
        ]
        self.assertEqual(
            [row["id"] for row in FULL.keep_unique_inputs(rows)],
            ["one", "two"],
        )


if __name__ == "__main__":
    unittest.main()
